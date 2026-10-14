# Session names, discovery and reruns

Scope: Qyrion CLI session naming and reusing Qyrion saved tests. Verified
against `apps/qyrion/src/qyrion/cli/main.py`, `client/api.py`, `mcp/server.py`
and `apps/qyrion/dev-docs/command-catalog.md` (2026-10-09). Check installed
help after the capabilities handshake; a source change is not proof that an
older release or the deployed backend supports it. Use the shared credential
wrapper, or `private-execution.md` for credential-bearing input/history.

## Name new sessions

`qyrion run` and `qyrion sessions create` accept `--session-name`; `--run-name`
is an alias on those two commands. Both web and mobile forward `run_name`.
The supplied name takes precedence over automatic naming. Omitting the option
keeps automatic naming; it does not rename an existing session or saved test.

- Honor a user-supplied non-secret name exactly, without replacing it with a
  generated title. For a multi-scenario task without explicit names, use short
  scenario-specific names such as `AS-609 | S01 | Login validation`.
- Never put passwords, account identifiers, raw ticket content or secrets in
  names. If a supplied name contains a secret, use a safe descriptive label.
- Names aid navigation, not identity or duplicate prevention: capture the
  returned `run_id`, and reconcile uncertain creates before retrying.

Examples below omit the wrapper for readability; resolve it from the installed
plugin root. Objective files and subsequent output follow private execution.

```bash
qyrion run --message-file ./objective.md --platform web \
  --start-url https://test.example.com --session-name "AS-609 | S01 | Login" \
  --mode ci --timeout 1800 --jsonl
qyrion sessions create --message-file ./objective.md --platform mobile \
  --device-ref <device-ref> --app <app-id> \
  --session-name "AS-609 | S02 | Onboarding" --mode ci --jsonl
```

## Discover an existing Qyrion test

Use discovery for an explicit reuse request or a save destination, not as a
replacement for requested fresh exploration (`execution-routing.md`).

```bash
qyrion projects list --page 1 --page-size 25 --json
qyrion tests list --project <project-id> --page 1 --page-size 25 --json
qyrion tests get <test-id> --json
```

Both lists are scoped to the configured team and support `--profile`.
Follow their returned page/total metadata until the relevant inventory is
exhausted; these commands use `--page`/`--page-size`, not step-history cursors.
Read the chosen test and verify project, platform, saved target and replayable
steps. Reuse a confirmed destination once per task (`test-preservation.md`).
Qyrion projects/tests and Aegis web projects/modules are separate contracts;
do not substitute IDs between them or invent Qyrion module flags.

## Choose the intended rerun

| Request | Command and boundary |
|---|---|
| Run the current saved test definition | `tests rerun <test-id>`; automatically uses that test's project; no `--project` flag needed |
| Replay a prior completed session's recorded steps | `sessions rerun <source-run-id>`; current CLI requires `--device-ref`, with optional `--app`; it has no web `--platform`/`--start-url` options |
| Continue an existing live/parked session | `sessions send <run-id>`; a new objective in that session, not a rerun |
| Fresh exploration/new coverage | `run` or `sessions create`; do not silently switch to replay |

Saved-test reruns support web and mobile. Web uses the saved/previous-run URL;
`--start-url` explicitly overrides it or supplies a missing URL. Omit mobile
device/app flags for web. Mobile requires `--device-ref` or
`--project-device-id`, with `--app` when needed. Select actual returned IDs.
Both rerun commands use **`--run-name`**, not `--session-name`. A rerun name
labels the new run and does not rename the saved test. Optional `--dataset`
on `tests rerun` selects a known supported dataset; do not invent one.

```bash
qyrion tests rerun <web-test-id> --run-name "AS-609 | S01 | Verification" --json
qyrion tests rerun <mobile-test-id> --device-ref <device-ref> \
  --app <app-id> --run-name "Onboarding verification" --json
qyrion sessions rerun <source-run-id> --device-ref <device-ref> \
  --run-name "Prior mobile run replay" --json
```

All create a **new run ID**. Capture it immediately; record the source test/run
relationship in sanitized evidence. The rerun command's exit 0 means submission
worked, not that assertions passed. Prefer submission with `--json`, then bounded
`sessions stream <new-run-id> --until input-required --max-seconds 900 --jsonl`
and terminal `sessions result`/step inspection. Handle questions and cleanup as
for fresh sessions. `--stream --jsonl` is available on reruns, but does not by
itself add a finite wait budget or turn exit 0 into a passing-test verdict.
Both replay paths require curated replayable steps; missing steps or unsupported
web session-replay options are concrete blockers, not permission to invent flags
or silently create a different test/project. Reconcile before any retry.

## MCP and attribution

When the separate Qyrion MCP server is connected, discover its live schemas:
`qyrion_list_projects`, `qyrion_list_tests`, `qyrion_get_test`,
`qyrion_rerun_test`, `qyrion_rerun_session`, and `qyrion_create_session` mirror
these operations; naming arguments use `run_name`. The bundled hosted Aegis
MCP is different and need not expose these `qyrion_*` tools.

Runbridge/TestHub can resolve the run creator email from the validated API
token response, including its `login` field. This is backend attribution,
not the target-app test account. Do not request a separate email/gateway token
or put that identity into the objective to work around missing attribution.
Deployment and auth configuration determine availability; old run records are
not automatically backfilled by a CLI/skill update.
