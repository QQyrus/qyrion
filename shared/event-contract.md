# Qyrion event contract v1 (plugin copy)

The machine-readable contract for consuming Qyrion session streams. This is
the plugin-embedded copy; the upstream source of truth is
`apps/qyrion/docs/event-contract.md` in the Qyrus df-ai-session repository —
if the two ever disagree, the upstream file wins and this copy must be
refreshed.

Features marked with a capabilities flag below exist only when
`qyrion capabilities --json` reports that flag `true` (see the CLI contract).

## Frame envelope

With `--jsonl`, each frame is one JSON object per line on stdout; all
human-readable output goes to stderr.

```json
{"event": "snapshot", "run": {"run_id": "run_...", "status": "running"}}
```

```json
{
  "event": "update",
  "event_id": "evt_...",
  "sequence_no": 42,
  "type": "tool_result",
  "run_id": "run_...",
  "status": "running",
  "message": "Tapped 'Log in'",
  "payload": {},
  "created_at": "2026-07-11T09:34:12Z"
}
```

- `event` is `snapshot` (full run state; always the first frame, re-emitted
  after status-changing updates) or `update` (one runtime event).
- `sequence_no` is monotonically increasing per run. Use it for dedupe,
  citations in evidence reports, and reconnect. Duplicate delivery is
  possible; consumers must be idempotent.
- Unknown `type` values must be ignored, not treated as errors.

## Run statuses

```text
created → running ⇄ waiting_user_input → completed | failed | cancelled | blocked | timed_out
```

Terminal set: `completed`, `failed`, `cancelled`, `blocked`, `timed_out`.
The stream closes after a terminal snapshot.

`waiting_user_input` is the **park state**: the device session stays live
(and keeps consuming device time) while the run waits for an appended
message. Two park reasons, distinguishable by the preceding events:

1. **Question park** — preceded by `clarification_requested`: the device
   agent is asking the caller something.
2. **Objective-complete park** (`--mode live` only) — the objective segment
   finished; no clarification event precedes it. The next appended message
   becomes a new objective.

Both are continued with the same `qyrion sessions send <run_id> ...` append.
`--mode ci` terminates instead of parking on objective completion.

## Event types (`update` frames)

| `type` | Meaning / key payload fields |
|---|---|
| `run_started` | Runtime began executing. |
| `message_recorded` | A conversation message was stored: `role` (`user`/`assistant`/`system`/`tool`), `content`, `metadata.kind` (notably `assistant_tool_call`, `clarification_request`). |
| `text_delta` | Streaming token chunk of the assistant's current message. Display-only; never parse for control flow. |
| `tool_call_start` | A device action is starting: `tool_name`, `step_label`, `tool_call_id`. |
| `tool_result` | A device action finished: `output`, `is_error`, `latency_ms`, `step_label`, `artifact_refs` (see below). |
| `clarification_requested` | The device agent needs input. `payload.question` is the question text; status moves to `waiting_user_input`. Answer with `qyrion sessions send <run_id> ...`. |
| `clarification_resolved` | An appended user message answered the pending question; status returns to `running`. `payload.message_id` links the answer. |
| `user_message_appended` | A caller message was accepted into the run. |
| `run_completed` / `run_failed` / `run_cancelled` / `run_timed_out` / `run_blocked` | Terminal transitions; a terminal `snapshot` follows. |
| `usage` / `device_geometry_changed` / others | May appear; safe to ignore for control flow. |

## Artifacts (screenshots and evidence)

`tool_result.payload.artifact_refs` is a list of artifact handles:

```json
{
  "artifact_id": "art_...",
  "name": "observe-000123.png",
  "content_type": "image/png",
  "metadata": {"role": "observe_raw"}
}
```

Roles seen today: `observe_raw` (device screenshot),
`derived_observation_overlay` (annotated screenshot). Treat `artifact_id` as
the only durable handle; any path/S3 fields are not part of the contract and
are removed by sanitization. Fetch content (gated by `artifact_presign`):

```bash
qyrion sessions artifacts <run_id> --role observe_raw --json
qyrion sessions download <run_id> <artifact_id> --output ./shot.png
qyrion sessions presign  <run_id> <artifact_id> --json   # {url, expires_in_seconds}
```

Prefer `download` — coding agents read local files far more reliably than
remote URLs. Presigned URLs expire (default 3600s) and are short-lived
secrets: never log, paste, or commit them.

## Reconnect (gated by `stream_cursor`)

`qyrion sessions stream <run_id> --after-sequence <n> --jsonl` replays
persisted events with `sequence_no > n`, then continues live with no gap.
Keep the highest `sequence_no` you have processed and pass it on reconnect.
On SIGINT the CLI prints the run id and a resume command to stderr.

## Stream stop conditions

- Default: the stream ends when the run reaches a terminal status.
- `--until input-required`: also ends (exit 0) when the run parks at
  `waiting_user_input`. This is the primitive for the agent turn loop:
  send → stream until input-required → read events/screenshots → send the
  next message (or answer the question) → repeat → cancel or let it complete.
- `--until terminal`: explicit form of the default.
- `--max-seconds <n>`: ends with the failure exit code if no stop condition
  is met in time. Always set it — never hold an unbounded stream.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Success: objective passed, or the requested stop condition was reached |
| 1 | Objective failed, blocked, cancelled, or timed out |
| 2 | Invalid usage or missing configuration |
| 3 | Authentication or authorization failure |
| 4 | Backend availability failure |
| 5 | `qyrion run` parked on an agent question with no way to reply (`input_required`) |
| 130 | Interrupted (SIGINT) |

With the `run_input_required_exit` capability, `qyrion run` in machine mode
exits `5` promptly when a question parks the run, with one structured
`input_required` error naming the question — the run-level equivalent of
`--until input-required` + exit 0 on `sessions stream`. On older binaries a
pending unanswered question at `run --timeout` expiry exits `1` (the run is
not passed); use the stream signal there instead.

## Capabilities handshake

```bash
qyrion capabilities --json
```

```json
{
  "cli_version": "x.y.z",
  "event_schema_versions": ["1"],
  "features": {
    "session_questions": true,
    "artifact_presign": true,
    "stream_cursor": true,
    "idempotent_create": true
  }
}
```

Check flags before relying on gated features and fail with an actionable
message (upgrade/install guidance) otherwise.

## Sanitization guarantees

CLI/JSONL output never contains: signed/presigned URLs (except the explicit
`presign` command's response), cloud ARNs, provider/model/API-mode names,
runtime session ids, raw device WebSocket endpoints, gateway tokens, or API
keys. Do not attempt to recover any of these; their absence is intentional.
