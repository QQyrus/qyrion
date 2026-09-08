# Qyrion CLI contract (plugin copy)

How a coding agent must locate, verify, and call the `qyrion` CLI. This copy is
embedded in every skill of the qyrion-agent-plugin; the canonical source lives
at `shared/cli-contract.md` in the plugin repository.

## Resolving the CLI

Resolve the executable in this order and use the first hit:

1. `QYRION_CLI` environment variable — an explicit path to the executable.
   Always honor it when set.
2. `qyrion` on `PATH`.
3. Pinned npm runner: `npx @qqyrus/qyrion@<pinned-version>` (the npm wrapper
   published by the Qyrion release workflow). Requires npm registry auth for
   the `@qqyrus` scope; see the install guide.

Never auto-install anything without telling the user first. If steps 1–2 fail,
say so, name the npx fallback you intend to run, and point the user at the
install guide (`apps/qyrion/docs/getting-started.md` in the Qyrus repo, or the
plugin README's install pointer) before running it.

## Capabilities handshake (always the first call)

Before any other qyrion command in a task, run:

```bash
qyrion capabilities --json
```

Expected shape:

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

Interpretation:

- Command missing / unknown (usage error, exit 2): the installed CLI predates
  the plugin contract. Stop and tell the user to upgrade per the install
  guide. Do not attempt workarounds against an old CLI.
- `event_schema_versions` must include `"1"`.
- Feature gates (check before using the gated surface):

| Feature flag | Gates |
|---|---|
| `session_questions` | `sessions question`, relying on `clarification_requested` frames |
| `artifact_presign` | `sessions artifacts` / `sessions presign` / `sessions download` |
| `stream_cursor` | `sessions stream --after-sequence <n>` |
| `idempotent_create` | idempotency keys on session create |
| `run_input_required_exit` | treating `qyrion run` exit `5` as the "agent question pending" signal (older binaries hang until `--timeout` and exit `1` instead) |

If a required flag is `false`, tell the user which feature the backend/CLI
does not support yet and degrade (e.g. skip screenshot download) or stop,
rather than calling the gated command and parsing its failure.

## Authentication, profiles, and first-run setup

Qyrion needs exactly three credentials, plus a selected team:

| Value | Env var |
|---|---|
| Application URL (the Qyrus URL the user logs in to) | `QYRION_APP_URL` |
| API key | `QYRION_API_KEY` |
| Gateway Authorization token (raw or `Bearer <token>` — both work) | `QYRION_AUTHORIZATION` |
| Team id (skips interactive team selection) | `QYRION_TEAM_ID` |

The application URL is the only endpoint the user ever supplies — qyrion
derives everything else from it. Agents must never prompt for, print, echo,
or store credential VALUES, and must never place them in session messages,
files, command arguments, or logs. Precedence everywhere is:
command-line flag → env var → stored profile.

### Probe auth state first

```bash
qyrion auth teams --json
```

- Exit `0` with a team list → credentials work; continue to team selection.
- Exit `3` → credentials present but rejected (expired/invalid API key or
  gateway token). Ask the user to refresh them.
- Exit `2` (or a missing-configuration error) → nothing configured yet; run
  first-run setup below.

### First-run setup — two paths

**Path A — user at a terminal (preferred for local development).** Tell the
user to run, in their own terminal:

```bash
qyrion configure
```

It interactively prompts for the three credentials, fetches their teams, and
lets them pick one; everything is stored in the OS keyring under the active
profile. The agent must NOT try to drive this wizard (it requires interactive
prompts) — hand it to the user, wait, then re-run the probe.

**Path B — non-interactive (agent shells, CI).** Ask the user to export the
three env vars in the environment the agent runs in (shell profile or CI
secret store — never pasted into the conversation or committed):

```bash
export QYRION_APP_URL="https://app.qyrus.com"
export QYRION_API_KEY="..."        # secret
export QYRION_AUTHORIZATION="..."  # secret
```

Then complete team selection yourself (see below) and persist it with
`qyrion auth use-team <team-id>` or `QYRION_TEAM_ID`.

### Team selection

Most operations are team-scoped and fail without a selected team. After the
probe succeeds:

```bash
qyrion auth teams --json
```

The payload contains a team list under `teams` (or `items`, possibly nested
under `data`); each item's id is its `uuid` (fallbacks: `team_id`, `teamId`,
`id`) and its display name is `name`/`teamName`. Handle all of these key
variants when parsing.

- Exactly one team → select it and tell the user which one you selected.
- Multiple teams → present the names to the USER and ask which to use; never
  guess (sessions, uploads, and results land in that team's workspace).

Persist the choice:

```bash
qyrion auth use-team <team-id>    # stores it in the active profile
```

or set `QYRION_TEAM_ID` in CI. (`qyrion auth teams --select` is the
interactive picker for users at a terminal; agents use `use-team`.)

### Profiles

Every command accepts `--profile <name>` (default `default`). Credentials and
the selected team are stored per profile in the OS keyring — never in
plaintext files. Use separate profiles for separate environments (e.g.
`--profile staging` vs `--profile prod`) instead of swapping env vars; pass
the same `--profile` consistently through a whole task, including to
subagents running parallel sessions.

## Output modes

- `--json`: single JSON object on stdout for request/response commands.
- `--jsonl`: one JSON object per line on stdout for streams (see the event
  contract). All human/Rich output goes to stderr in these modes; parse stdout
  only.
- Structured errors (in `--json`/`--jsonl` modes):

```json
{"error": {"code": "...", "message": "...", "retryable": false, "remediation": "..."}}
```

Never scrape human-formatted output. If a command lacks `--json`, check
`qyrion <command> --help` before assuming a shape.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Success: objective passed, or the requested stop condition was reached |
| 1 | Objective failed, blocked, cancelled, or timed out |
| 2 | Invalid usage or missing configuration |
| 3 | Authentication or authorization failure (check the three credentials) |
| 4 | Backend availability failure |
| 5 | `qyrion run` parked on an agent question with no way to reply (`input_required`) |
| 130 | Interrupted (SIGINT) |

`sessions stream --until input-required` exits `0` when the run parks at
`waiting_user_input` — that is the "your turn" signal, not an error.

`qyrion run` handles agent questions itself. On a human TTY it prompts,
sends the reply, and resumes. In machine mode (`--jsonl`/`--json`) or without
a TTY — the normal case for a coding agent — it never blocks on stdin: it
exits `5` with one structured `input_required` error whose `message` carries
the question. Treat exit `5` like the stream's input-required signal: read
the question (from the error or `sessions question <run_id> --json`), decide
per the answer policy, and reply with
`qyrion sessions send <run_id> "..." --follow`. Answer promptly — the
backend closes a parked run as `timed_out` after a few minutes. Gate this
interpretation on the `run_input_required_exit` capability; older binaries
hang until `--timeout` and exit `1` instead.

## Command surface

Setup and inventory:

```bash
qyrion capabilities --json
qyrion auth teams --json                 # list teams for the credentials
qyrion devices list --platform android --json
qyrion apps list --json
qyrion apps upload ./app.apk --platform android --name "My App" \
  --skip-if-uploaded --json              # sha256 dedup: reuses an identical upload
```

One-shot run (CI mode — terminates when the objective completes):

```bash
qyrion run "Log in and verify the dashboard loads" \
  --device-ref <device-ref> --app <app-id> \
  --mode ci --timeout 1800 --jsonl
```

`--timeout` (default 1800, `0` disables) is a client-side execution budget;
its clock pauses while an agent question waits for a reply. Keep values
≤ 3600.

Interactive session lifecycle (live mode — parks between objectives):

```bash
qyrion sessions create "Open the app and log in" \
  --device-ref <device-ref> --app <app-id> --mode live --jsonl
# First JSONL line is a snapshot carrying run.run_id — capture it.

qyrion sessions stream <run_id> --jsonl --until input-required --max-seconds 900
qyrion sessions send <run_id> --message-file ./next-objective.md --follow --jsonl
qyrion sessions question <run_id> --json      # pending question when parked
qyrion sessions result <run_id> --wait --json
qyrion sessions cancel <run_id>
qyrion sessions list --json
```

Inspection and artifacts:

```bash
qyrion sessions messages <run_id> --json
qyrion sessions events <run_id> --json
qyrion sessions steps <run_id> --json
qyrion sessions artifacts <run_id> --role observe_raw --json
qyrion sessions download <run_id> <artifact_id> --output ./shot.png
qyrion sessions presign <run_id> <artifact_id> --json   # avoid; prefer download
```

Saved tests:

```bash
qyrion tests list --project <project-id> --json
qyrion tests get <test-id> --json
qyrion tests create --project <project-id> --name "Login smoke" --objective "Log in"
qyrion tests update <test-id> --script-file ./script.md --steps-file ./steps.json
qyrion tests rerun <test-id> --device-ref <device-ref> --app <app-id> --jsonl
qyrion sessions save-test <run_id> --project <project-id> --test-name "Login smoke"
```

## The run_id handle pattern

`run_id` is the only handle a session needs. The first JSONL line of
`run`/`sessions create` is a `snapshot` frame whose `run.run_id` field carries
it. Any other process (a subagent, a later turn, a re-attach after SIGINT) can
operate on the session with just that id: `sessions stream/send/question/
result/cancel <run_id>`. Persist the run_id immediately after create; on
SIGINT the CLI also prints the run id and a resume command to stderr.

## Long messages

Never pass long objectives or answers as shell arguments (quoting bugs,
command-history leakage). Write them to a temporary file and use
`--message-file <path>` on `run`, `sessions create`, and `sessions send`.

## Modes

- `--mode ci`: one objective, terminal result, meaningful exit code. Use for
  one-shot verification and CI.
- `--mode live`: after each objective segment the run parks at
  `waiting_user_input` with the device still allocated; the next
  `sessions send` message becomes the next objective. Use for multi-step
  agent-driven testing. Parked devices still consume device time — always
  cancel or finish sessions you started.
