# Qyrion CLI contract (plugin copy)

How a coding agent must locate, verify, and call the `qyrion` CLI. This copy is
embedded in every skill of QyrusAI Assure; the canonical source lives
at `shared/cli-contract.md` in the plugin repository.

## Resolving the CLI

Resolve the executable in this order and use the first hit:

1. `QYRION_CLI` environment variable — an explicit path to the executable.
   Always honor it when set.
2. `qyrion` on `PATH`.
3. If missing, follow `references/prerequisites.md` to install a verified
   public release binary or the explicitly selected source checkout, then
   repeat resolution. Existing private npm installations remain supported.

Tell the user what needs installing and perform it within the setup/session
request. Do not make the user enumerate dependencies or hand them a manual
installation checklist. Preserve explicit executable overrides and respect
host installation restrictions.

Apply `execution-routing.md` before choosing an execution surface. Web and
mobile objectives use Qyrion sessions unless the user chooses another tool;
an unavailable Qyrion feature is not permission to use the host's browser.
At task entry, follow `update-checks.md` for the throttled release check;
use `qyrion version --json` for the version, not a root `--version` flag.

Ordinary calls use the shared credential wrapper. Credential-bearing
objectives and all later reads that can echo their history instead use
`qyrus_private.py` as specified in `private-execution.md`. It loads the same
environment and filters output/logs; plain `--message-file` is not redaction.

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
  the plugin contract. Offer an update per `update-checks.md`, upgrade through
  its trusted source only after acceptance, and repeat the handshake once. Report a
  persistent compatibility blocker; do not improvise against an old CLI.
- `event_schema_versions` must include `"1"`.
- Feature gates (check before using the gated surface):

| Feature flag | Gates |
|---|---|
| `session_questions` | `sessions question`, relying on `clarification_requested` frames |
| `artifact_presign` | `sessions artifacts` / `sessions presign` / `sessions download` |
| `stream_cursor` | `sessions stream --after-sequence <n>` |
| `idempotent_create` | Reported create behavior; inspect live help/contract before using any key mechanism (current CLI has no caller-supplied create key flag) |
| `web_sessions` | `--platform web --start-url <website-url>` |
| `web_live_view` | web `--view` / `sessions view` |
| `run_input_required_exit` | treating `qyrion run` exit `5` as the "agent question pending" signal (older binaries hang until `--timeout` and exit `1` instead) |

If a required flag is `false`, tell the user which feature the backend/CLI
does not support yet and degrade (e.g. skip screenshot download) or stop,
rather than calling the gated command and parsing its failure.

## Authentication, profiles, and first-run setup

Qyrion requires the Qyrus application URL and API key, plus a selected team
for team-scoped operations. Gateway Authorization is optional legacy input
and is never sent by current Qyrion clients.

| Value | Env var |
|---|---|
| Qyrus tenant URL (not the website under test) | `QYRION_APP_URL` |
| Shared API key | `QYRION_API_KEY` (mapped from private `X-API-Key`) |
| Selected team | `QYRION_TEAM_ID` |

### First-run setup

Read `references/credentials.md` (or `shared/credentials.md` in the plugin
repository). Reuse the supplied/saved/default private env file before asking
for a missing file with `X-API-Key` and `QYRION_APP_URL`. Use the helper to validate it, remember
the path, and wrap all Qyrion calls. The helper derives and writes the MCP
endpoint. Never shell-source a key containing hyphens or echo secret values.

Discover teams through Qyrus MCP using the flow in `references/credentials.md`:
guide first, then `qyrus_teams_get_by_api_key` with `{}`. The separate gateway
route used by `qyrion auth teams` is not a required plugin preflight; its 401
does not establish that the key is invalid on the other Qyrus surfaces.
Missing configuration means use the setup skill. `qyrion configure` in the
user's own terminal remains an alternative for CLI-only keyring setup; it
asks for the app URL and key, not a gateway token. Keyring-only setup does
not configure the hosted Aegis MCP or SDK.

Direct Qyrion precedence remains command flags → environment → keyring.
Never put credential values in command flags. Shared-file mode deliberately
uses that file's values rather than unrelated exported Qyrion overrides.

### Team selection

Most operations are team-scoped and fail without a selected team. Use the
MCP discovery/selection contract in `references/credentials.md`. Preserve the
returned team UUID exactly; an organization ID is not a team ID. Revalidate
an existing selection, select a sole team when none was chosen, or ask the
user to choose among multiple teams.

Persist the choice:

```bash
qyrion auth use-team <team-id>    # stores it in the active profile
```

or set `QYRION_TEAM_ID` in the selected private file (also suitable for CI).
Verify the selected Qyrion scope with helper-wrapped
`qyrion sessions list --json`; MCP success alone is not Qyrion authorization.

### Profiles

Every command accepts `--profile <name>` (default `default`). Interactive
CLI setup stores credentials/team per profile in the OS keyring. The plugin
shared-file flow uses a private dotenv file and overrides profile credentials
and service URLs. Select a different private file to change its environment;
changing `--profile` alone cannot override that file. Pass a consistent profile
throughout a task when using a profile-selected team.

## Output modes

- `--json`: single JSON object on stdout for request/response commands.
- `--jsonl`: one JSON object per line on stdout for streams (see the event
  contract). All human/Rich output goes to stderr in these modes; parse stdout
  only.
- Updated CLI builds emit plain JSON with Unicode escapes. JSON parsing
  restores the original text; do not interpret escapes as corrupted content.
- Structured errors (in `--json`/`--jsonl` modes):

```json
{"error": {"code": "...", "message": "...", "retryable": false, "remediation": "..."}}
```

Never scrape human-formatted output. If a command lacks `--json`, check
`qyrion <command> --help` before assuming a shape.

### Windows JSON encoding failures

A traceback through `_print_json` / `Rich` ending in `UnicodeEncodeError:
'charmap' codec can't encode character '\u2192'` (seen in 0.3.4-beta) is a
local output failure after the payload was fetched. It does not establish an
API authentication error or native access violation. Record the exact
executable, command, stderr and exit code; partial JSON or a traceback is not
successful verification, even if an older wrapper reports exit 0.

This requires a CLI binary containing the plain-JSON fix; updating only the
plugin cannot patch an existing executable. Follow `prerequisites.md` to select
the latest published release, preserve explicit overrides, and verify the
read-only command. If that release still reproduces it, report the remaining
CLI blocker and complete independent MCP/SDK setup. Do not rotate credentials,
reinstall the same release repeatedly, or create a session as a diagnostic.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Success: objective passed, or the requested stop condition was reached |
| 1 | Objective failed, blocked, cancelled, or timed out |
| 2 | Invalid usage or missing configuration |
| 3 | Authentication or authorization failure (check key, tenant, and team) |
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
qyrion auth teams --json                 # direct gateway lookup; not the plugin setup gate
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

Browser execution uses the same lifecycle and evidence contract:

```bash
qyrion run --message-file ./web-objective.md --platform web \
  --start-url https://test.example.com --mode ci --timeout 1800 --jsonl
qyrion sessions create --message-file ./web-objective.md --platform web \
  --start-url https://test.example.com --mode ci --jsonl
qyrion sessions steps <run_id> --locators --json
```

Require `web_sessions`; omit mobile-only `--device-ref` and `--app`.
`run` waits/streams. `sessions create` without `--stream` or `--view`
returns after bootstrap and submission, while execution continues. Always
retain the run ID and inspect the terminal result later. It is not proof of
completion. Check `--help` before using options on an older installed CLI.
The Qyrus tenant URL and the target website URL are separate values.

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
SIGINT the CLI also prints the run id and a resume command to stderr. Record
scoped handles and final outcomes using `local-state.md`; never store raw
objectives or credentials in that record.

## Long messages

Never pass long objectives or answers as shell arguments (quoting bugs,
command-history leakage). Write them to a temporary file and use
`--message-file <path>` on `run`, `sessions create`, and `sessions send`.
All three also support `--message-file -` for stdin. Follow `safety-policy.md`
for authorized target-account credentials; message files/stdin do not prevent
the submitted message from being retained in Qyrus session history.

## Modes

- `--mode ci`: one objective, terminal result, meaningful exit code. Use for
  one-shot verification and CI.
- `--mode live`: after each objective segment the run parks at
  `waiting_user_input` with the device still allocated; the next
  `sessions send` message becomes the next objective. Use for multi-step
  agent-driven testing. Parked devices still consume device time — always
  cancel or finish sessions you started.
