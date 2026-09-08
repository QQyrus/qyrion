---
name: qyrion-cli
description: Starts, monitors, replies to, downloads artifacts from, and cancels Qyrus AI device sessions through the qyrion CLI. Use for explicit qyrion commands, direct session operations (start/stream/send/question/result/cancel), artifact/screenshot download, app upload, device or test listing, and troubleshooting qyrion CLI errors or exit codes. Do not use for deciding what to test (use qyrus-device-testing) or for git-diff test impact analysis (use qyrus-change-impact).
---

# Qyrion CLI operations

Direct, single-session operations against the Qyrus device cloud through the
`qyrion` CLI. Use structured modes only (`--json` / `--jsonl`); never scrape
human-formatted output.

Read before the first call in a task:

- `references/cli-contract.md` — resolution order, full command catalog, flags
- `references/event-contract.md` — JSONL frames, statuses, park semantics
- `references/safety-policy.md` — binding safety rules

## Preflight (mandatory, in order)

1. Resolve the CLI: `QYRION_CLI` env override → `qyrion` on `PATH` → pinned
   `npx @qqyrus/qyrion` (tell the user before using the npx fallback; never
   auto-install silently).
2. Handshake: `qyrion capabilities --json`.
   - If the command is unknown or fails with a usage error, the CLI is too
     old for this plugin. Stop and tell the user to install/upgrade per the
     Qyrion getting-started guide (`apps/qyrion/docs/getting-started.md` in
     the Qyrus repo; binaries on the repo's Releases page, or
     `npx @qqyrus/qyrion`). Do not improvise against an old CLI.
   - Check the `features` flags before using gated commands (artifact
     download, `sessions question`, `--after-sequence`); see the CLI
     contract's gating table.
3. Probe auth: `qyrion auth teams --json`.
   - Exit 0 with teams → authenticated; make sure a team is selected (see
     step 4).
   - Exit 3 → credentials rejected; ask the user to refresh their API key /
     gateway token.
   - Exit 2 / missing configuration → first-run setup
     (`references/cli-contract.md` § "First-run setup"): either tell the user
     to run `qyrion configure` in their own terminal (interactive wizard —
     never drive it yourself), or have them export `QYRION_APP_URL` /
     `QYRION_API_KEY` / `QYRION_AUTHORIZATION` in the agent's environment.
     Never prompt for or print credential values; re-probe afterwards.
4. Confirm team selection: if the probe listed multiple teams and no team is
   configured, show the team names to the user and ask which to use — never
   guess — then persist it with `qyrion auth use-team <team-id>` (or
   `QYRION_TEAM_ID` in CI). A single team may be auto-selected; say so.
   Honor `--profile <name>` if the user works with multiple environments and
   pass the same profile to every subsequent command.

## Core operations

Capture and keep the `run_id`: the first `--jsonl` line of `run` /
`sessions create` is a `snapshot` frame with `run.run_id`. Every later
operation takes that id, from any process.

One-shot verification (terminates on objective completion, meaningful exit
code):

```bash
qyrion run "Log in and verify the dashboard loads" \
  --device-ref <device-ref> --app <app-id> --mode ci --timeout 1800 --jsonl
```

In machine mode `run` never blocks on stdin: if the agent asks a mid-run
question, it exits `5` with a structured `input_required` error naming the
question (gate on the `run_input_required_exit` capability; older binaries
hang until `--timeout` and exit `1`). Answer with
`qyrion sessions send <run_id> "..." --follow`.

Interactive turn loop (live mode parks at `waiting_user_input` between
objectives, device stays allocated):

```bash
qyrion sessions create "Open the app and log in" \
  --device-ref <device-ref> --app <app-id> --mode live --jsonl
qyrion sessions stream <run_id> --jsonl --until input-required --max-seconds 900
qyrion sessions send <run_id> --message-file ./next.md --follow --jsonl
qyrion sessions result <run_id> --wait --json
qyrion sessions cancel <run_id>
```

Always pass `--max-seconds` on streams. Write long messages to a file and use
`--message-file`, not shell arguments.

## Park state: what a stopped stream means

`--until input-required` exiting 0 means the run parked at
`waiting_user_input`, not that it finished. Distinguish the two park reasons
by the preceding events:

- A `clarification_requested` frame precedes the park → the device agent
  asked a question (`payload.question`, or fetch with
  `qyrion sessions question <run_id> --json`). Answer it via
  `sessions send`, or apply the answer-qyrion-agent-questions policy if that
  skill is available.
- No clarification event → objective-complete park (live mode). Your next
  `sessions send` message becomes the next objective.

A parked session holds a real device. Never end a task with a session still
parked or running: send a final objective, let it complete, or cancel it.

## Artifact (screenshot) download flow

Gated by the `artifact_presign` capability. Screenshots ride on
`tool_result.payload.artifact_refs` (role `observe_raw` = raw device
screenshot).

```bash
qyrion sessions artifacts <run_id> --role observe_raw --json   # list handles
qyrion sessions download <run_id> <artifact_id> --output ./shot.png
```

Then read/view the local file. Prefer `download` over `presign`: local files
are reliable, and presigned URLs are short-lived secrets that must never be
logged, pasted, or committed.

## Exit codes

| Code | Meaning | First response |
|---:|---|---|
| 0 | Success / requested stop condition reached | proceed |
| 1 | Objective failed, blocked, cancelled, or timed out | inspect events + result; report verdict |
| 2 | Invalid usage or missing configuration | fix the command; check `--help` |
| 3 | Auth/authorization failure | see troubleshooting: verify the three credentials |
| 4 | Backend availability failure | see troubleshooting |
| 130 | Interrupted (SIGINT) | re-attach with `sessions stream <run_id>` |

## Troubleshooting

Read `references/troubleshooting.md` for the failure → remediation table
(auth exit 3, backend 404 `backend_route_missing`, missing capabilities,
device-slot waits, npm auth for the npx fallback).

## Output

Report: the commands run (at a safe level — no credentials, no presigned
URLs), run_id(s), final status and verdict, downloaded artifact paths, cited
event `sequence_no` values, and anything left running (there should be
nothing).
