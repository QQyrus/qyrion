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
| `compact_session_output` | `sessions steps` / `sessions result` `--compact` and `--fields` (older binaries reject them as unknown options: fall back to the plain `--json` form, paged with `--limit`) |
| `session_wait_any` | `sessions wait --any <run_id> <run_id> ... --timeout N --json`, one wait over several sessions (older binaries answer "No such command": fall back to one `sessions result --wait` per session, with `sessions question` for each between waits) |

If a required flag is `false`, tell the user which feature the backend/CLI
does not support yet and degrade (e.g. skip screenshot download) or stop,
rather than calling the gated command and parsing its failure.

For names, project/test discovery and saved-test/session reruns, read
`session-workflows.md`. Check installed help: new sessions accept
`--session-name`/`--run-name`; reruns accept `--run-name`. Keep submit success
separate from terminal assertion success.

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

Project references and test-owned dataset commands require the capability
flags `project_references`, `project_variable_management`,
`test_dataset_management`, and `rerun_test_data_preflight`. The matching
Qyrion MCP discovery tool is `qyrion_capabilities`. Follow
`test-data-workflows.md` for commands, schemas, revisions and confirmation;
do not infer support from the plugin version alone.

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
completion.

**Long sessions in a host that limits one command** (a sandboxed agent box, a
shell tool with a time or output cap): do not hold the command with `run` or
`sessions create --stream`. A session may run for as long as its own
`--timeout` (1800 by default), longer than such a command is allowed to, and
the host ends the command while the session goes on. Start with
`qyrion sessions create ... --mode ci --json --timeout 1800` (it returns at once;
`run.run_id` is in its last output line), then observe with
`qyrion sessions result <run_id> --wait --timeout 240 --json --compact` in a
loop. A wait that ran out exits `0` with a `run.status` that is not final: that is normal,
not a failure, and the session is still running. If a `run` was ended by the
host after it printed its run ID, the session is still running as well (see
`sessions result --wait` below). Between waits, check
`qyrion sessions question <run_id> --json`; the loop ends at a final status,
on your own stall rule, or when the person stops it. Check `--help` before using options on an older installed CLI.
The Qyrus tenant URL and the target website URL are separate values.

Interactive session lifecycle (live mode — parks between objectives):

```bash
qyrion sessions create "Open the app and log in" \
  --device-ref <device-ref> --app <app-id> --mode live --jsonl
# First JSONL line is a snapshot carrying run.run_id — capture it.

qyrion sessions stream <run_id> --jsonl --until input-required --max-seconds 900
qyrion sessions send <run_id> --message-file ./next-objective.md --follow --jsonl
qyrion sessions question <run_id> --json      # what a parked run waits for (waiting_for)
qyrion sessions result <run_id> --wait --json
qyrion sessions cancel <run_id>
qyrion sessions list --json
```

`sessions result --wait` holds the command until the run reaches a final
status (`completed`, `failed`, `cancelled`, `blocked`, `timed_out`), parks
(`waiting_user_input`; a run already parked returns at once) or `--timeout`
seconds pass; without `--timeout` it waits 300 seconds (at most 3600;
`--timeout 0` reads the status once). It exits `0` in every case, so read
`run.status`: any other status means the wait ran out and the session is
still running. A parked run is not final: run
`qyrion sessions question <run_id> --json` instead of waiting again. Its
`waiting_for` is `answer` (answer `question` with `sessions send`),
`next_instruction` (a live run did its instruction; `last_message` is what it
found: send the next step with `sessions send`, or end the run when the job is
done) or `replay_input` (`sessions send --secure`). Older backends hold the
wait through a park until the timeout. Older binaries return at once when `--timeout` is left out
(the default was 0); always pass `--timeout` explicitly in scripts that may
meet one. Prefer a loop of waits (`--timeout 240` where the host or a proxy limits a
call to about five minutes, otherwise up to `--timeout 300`) to polling
`sessions steps`, `events` or `stream`, and read `sessions steps` once, after
the session ended.

**Several sessions at once.** With the `session_wait_any` feature, watch
every session you started with one wait instead of waiting on them one at a
time (a question one session asks would otherwise sit unseen while you wait on
another):

```bash
qyrion sessions wait --any <run_a> <run_b> <run_c> --timeout 240 --json
```

It returns on the first real event across them and exits `0` in every case;
`woke.kind` says which: `question` (the session asks or needs input; answer
with `sessions send`, the question text is in `woke.question` or `sessions
question`), `finished` (a final status after at least one step),
`failed_to_start` (a final status that is not a success before any step) or
`timeout`. `sessions` lists each watched session's `status`, `final`,
`step_count`, `last_event` (newest event sequence) and `question`. A session
that is already final or already asking wakes the wait at once, so give the
next wait only the ids in `watch_next`. At most six ids; `--any` is required.
`woke.question_seq` tells a question you already answered (the backend can
show it for a few more seconds) from a new one.

 Plain `--json` from `sessions result` and
`sessions steps` repeats artifact paths, hashes, screenshots, raw tool
input/output and locator chains: a 500-step page was about 555 KB, and an agent
that paged through it in pieces filled its context and failed on its next model
call (Assure Box `cnv_444d7ec7038a4d21`, 2026-10-22). With the
`compact_session_output` feature, add `--compact` whenever you wait on a
session, poll it, or report what it did:

```bash
qyrion sessions result <run_id> --wait --timeout 240 --json --compact
qyrion sessions steps <run_id> --json --compact --limit 500
qyrion sessions steps <run_id> --json --fields sequence_no,step_label,status
```

Compact `result` keeps `run.status`, `run.summary` (`summary`, `verdict`),
`run.step_count` (instead of the `run.steps` list), `run.recent_events` (only
the newest event, so `run.recent_events[-1].sequence_no` is still the "is it
moving" signal), `run.pending_question` when a question is unanswered,
`run.usage.total_tokens` if the CLI returns it, and `report`. Compact `steps`
keeps `sequence_no`, `step_id`, `tool_name`, `step_label`, `status`,
`latency_ms` and, where present, `error` (why a step failed), `milestone` and
`replay_status`, with `next_cursor` for paging. `--locators` adds a one-line
`locator`. `--fields a,b,c` returns exactly the named fields; an unknown name
exits `2` and lists the known ones. Use the plain `--json` form only when you
need the bulk itself (locator candidates, raw output, artifacts), and then read
a page at a time with `--limit` instead of one huge page.

Inspection and artifacts:

```bash
qyrion sessions messages <run_id> --json
qyrion sessions events <run_id> --json
qyrion sessions steps <run_id> --json
qyrion sessions artifacts <run_id> --role observe_raw --json
qyrion sessions download <run_id> <artifact_id> --output ./shot.png
qyrion sessions presign <run_id> <artifact_id> --json   # avoid; prefer download
```

Step extraction is paginated: `sessions steps` defaults to 100 rows. Follow
returned `next_cursor` values with `--cursor <cursor> --limit 100` (compact
pages keep `next_cursor`, so `--json --compact --limit 500` pages the same
way); check the installed help and response shape. A snapshot or first page is not the full
recording. For complete run-to-test conversion, use `test-preservation.md`.

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

## Explicit objective pattern opt-out (0.3.9)

When the caller explicitly requests literal objective handling, `run` and
`sessions create` accept `--skip-credential-pattern-matching`. This bypasses
automatic credential classification and hiding for the initial objective,
including its first runtime handoff; inline text may persist and appear in
responses. Use explicit project `@VARIABLE` references for actual secrets.
Project reference authorization, start-URL credential checks, and later-message
parsing remain active. Never add this flag automatically or combine it with
reviewed `message_inputs`. It requires matching Runbridge deployment; older
strict backends reject the new field with 422. Verify installed command help
before invoking it. Existing private-execution requirements still apply.

## Confirming one @NAME as literal data (AS-1436)

`--skip-credential-pattern-matching` is not the tool for an unknown `@NAME`,
and there is no global "ignore missing variables" switch. A submission whose
`@NAME` matches no test data in the selected project is rejected with the
structured `unresolved_references` error, which names each occurrence
(`field_index`, `start`, `end`, `name`) and never a value:

```bash
qyrion run --project <project-id> --message-file ./objective.md --platform web \
  --start-url https://test.example.com --mode ci --jsonl
# {"error": {"code": "unresolved_references", "message": "... No test data matches @pass1.",
#            "references": [{"field_index": 0, "start": 12, "end": 18, "name": "pass1"}]}}
qyrion run --project <project-id> --message-file ./objective.md --platform web \
  --start-url https://test.example.com --mode ci --jsonl --literal-reference pass1
```

`--literal-reference NAME` is repeatable and is accepted by `run`,
`sessions create` and `sessions send`. Each name is resolved against the exact
text being sent, so it applies to every occurrence of that spelling in that
message and fails with exit 2 when the message no longer contains it — editing
the text invalidates an earlier confirmation instead of moving it. It cannot be
combined with `--secure`, whose reply is never appended as a message. Retried
starts reuse the first attempt's idempotency key, so a confirmed resend cannot
produce a second run.

On a terminal the command names the expressions on stderr and asks once; only
an explicit `y` resends as written, and stdout stays parseable. With
`--json`/`--jsonl` (or `--no-interactive` on `run`) it exits 2 and returns the
occurrences instead. Ask the person; never pass `--literal-reference` on your
own judgement.

A confirmed literal keeps the exact spelling and case the person typed and
still goes through credential detection — literal is not public text, so
`Password: @pass1` confirmed as literal remains protected. Never use a
confirmation to work around a missing variable, and never put a secret value on
the command line, in a shell history or in machine output in its place: create
the variable with `projects variables create --value-file <path>`.
`qyrion capabilities --json` advertises
`features.literal_reference_confirmation`; it requires a matching Runbridge
deployment, and an older backend rejects the new field with a plain 422.

## Optional report email (0.4.0)

Email is opt-in on a fresh session: omit `--email` to send no mail when it ends.
`qyrion run` and `qyrion sessions create` accept repeated `--email address`.
Never implicitly select the signed-in user or add recipients to an ordinary
objective. Confirm that sending to those recipients is authorized by the task.

`qyrion tests rerun` and `qyrion sessions rerun` inherit the linked saved test's
enabled notification recipients when both flags are omitted. An unlinked rerun,
or a saved test with notifications disabled, sends no email by default.
Repeated `--email` replaces the defaults for that execution; `--no-email`
suppresses enabled defaults. These two flags conflict. No opt-out flag is needed
for a fresh session that has no recipients.

MCP `qyrion_create_session` and `qyrion_send_message` accept the same decisions
as optional `literal_references`, whose objects are copied verbatim from the
rejection's `data.references` (hosted MCP: `body.literal_references`, with the
rejection as `error.code: "unresolved_references"` and
`error.details.references`). Omitting the field keeps the request older clients
send.

MCP `qyrion_create_session`, `qyrion_rerun_test` and `qyrion_rerun_session` use
optional `email_recipients`: omission follows the same fresh/rerun rules, an
explicit empty array suppresses, and a nonempty array replaces. Hosted MCP
forwards that field inside its operation's `body`; deployment must enable
`TESTHUB_MCP_ENABLED` separately from report-email delivery.

Retained TUI `/run` and `/send` take repeated `--literal-reference NAME`
alongside the message; bare chat has no options, so a rejection there names the
`/run` or `/send` command that resends the same text with the confirmation
attached.

Retained TUI `/run`, `/test-rerun` and `/session-rerun` preserve repeated email
options; reruns accept `--no-email`. `/email address ...` configures the next
fresh bare-chat session, `/email` shows its count and `/email clear` clears it.
Selection survives a failed creation and is consumed only after a successful
fresh start; active-session messages do not change recipients.

Emails contain Download PDF and Download HTML links for the exact report,
without report attachments. Links expire 48 hours after email is sent and anyone
with a link can download that report without Qyrus sign-in. Email acceptance
does not confirm inbox receipt or change the run verdict or CLI exit code.
At most ten supplied addresses are accepted; trim, lowercase and deduplicate,
reject invalid addresses, and never print credentials or signed report links.
Deploy matching TestHub/RunBridge/ArtifactArchiver contracts before the client.

## Email reports from History without rerunning

Use an existing run ID from `qyrion sessions list --json`. This operation does
not start, resume, finish or cancel an execution and does not edit saved-test
notifications. Select recipients explicitly; no signed-in user or saved defaults
are added. Up to ten supplied addresses are trimmed, lowercased and deduplicated.

```console
qyrion sessions email-report RUN_ID --email qa@example.com --email lead@example.com --idempotency-key share-1 --json
qyrion sessions email-status RUN_ID REQUEST_ID --json
```

`--report-type auto` (default), `session` or `rerun` uses the same report
resolution as the UI. The service reuses an available report or prepares missing
artifacts through the existing pipeline; it never reruns the test. Both PDF and
HTML are shared as 48-hour download links, with one separate email per recipient.

Reuse the same key after uncertain acceptance/timeouts. Do not change recipients
or report type under that key (HTTP 409). A new key intentionally resends. Keep
the returned request ID for progress lookup. Machine status `queued` describes
preparation; `accepted` means SMTP/provider acceptance, not mailbox receipt.
Other terminal statuses are `failed` and `partial_failure`, with sanitized counts
and error codes only. Human output avoids queue terminology.

TUI uses `/email-report RUN_ID --email qa@example.com --idempotency-key share-1`
and `/email-status RUN_ID REQUEST_ID`. Repeated `--email` is supported. These
commands do not consume `/email` choices for the next fresh chat or change the
active session. Existing fresh omission still means no email; linked rerun
omission still inherits enabled saved defaults and `--no-email` suppresses them.

Local MCP tools are `qyrion_email_session_report` (run_id, email_recipients,
idempotency_key, optional report_type) and `qyrion_get_report_email_status`
(run_id, request_id). Hosted MCP exposes the same operation names through
`qyrion_search`/`qyrion_execute`; sharing recipients/report_type are nested in
`body`, while run_id and idempotency_key are top-level operation arguments.

Deploy Runbridge aliases before using these commands:
- POST `/api/cli/sessions/{run_id}/reports/email` (Idempotency-Key required).
- GET `/api/cli/sessions/{run_id}/reports/email/{request_id}`.

They share the existing browser handlers, team authorization, request ledger and
delivery worker. Publish these two aliases in the Runbridge CLI gateway Swagger;
no new env variables, tables, cloud resources or credentials are introduced.
Hosted MCP also requires the updated TestHub catalog. No public Qyrion release
is cut by this change; 0.4.0 remains unreleased until the release branch is pushed.
