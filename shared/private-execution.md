# Private objective and output handling

Scope: Qyrion commands whose objective or session history contains authorized
target-app login details. Plain stdin protects command arguments but does not
sanitize Qyrion's JSON responses or local execution logs. Use the bundled
`scripts/qyrus_private.py` wrapper for these calls. It loads the same selected
Qyrus environment as `qyrus_env.py`; do not nest the two wrappers.

## Prepare the input without exposing it

The agent owns this handoff; do not hand the user a new technical setup
checklist. Reuse authorized ticket/private-source data through a host-permitted
non-echoing transfer. Where a connector exposes a response as a local resource,
extract values programmatically without printing its contents. Do not paste
literal credentials into tool-call code, shell commands, or chat. If the host
cannot transfer those values confidentially or requires human authentication,
follow that restriction and ask only for the missing permitted login method.

Create private files outside Git and the plugin cache: an objective text file
and a redaction JSON file containing an array of the exact sensitive values
that can appear in the objective or response (including the test-account
username and password). The API key is loaded separately and automatically
included in output redaction; it never belongs in the objective. On POSIX,
files must be mode 0600 and their containing directory should be 0700.
Do not reuse these files as the permanent result registry or host memory.

From the actual installed plugin root:

```bash
python3 scripts/qyrus_private.py --redact-file /private/login-values.json \
  --message-file /private/web-objective.txt --timeout 1900 -- \
  run --platform web --start-url https://test.example.com \
  --mode ci --timeout 1800 --jsonl
```

The wrapper supplies `--message-file -` and sends the objective through stdin.
Use the same pattern for `sessions create` or `sessions send <run-id>`.
For mobile, use `--platform mobile --device-ref <ref> --app <app-id>`.
Add `--env-file <selected-path>` only when explicitly selecting credentials;
the default path-selection contract and `QYRION_CLI` override still apply.

## Protect subsequent output too

Creation is not the only command that can echo credentials. Use the same
redaction file for session `show`, `list`, `stream`, `question`, `result`,
`steps`, `send`, and saved-test reads/writes whenever their responses may
contain the credential-bearing history. For example:

```bash
python3 scripts/qyrus_private.py --redact-file /private/login-values.json \
  --timeout 70 -- sessions stream <run-id> --max-seconds 60 --jsonl
```

Use machine output (`--json`/`--jsonl`). The wrapper filters known values from
parsed JSON before displaying it, replaces non-JSON output with a generic
suppression notice, and redirects the CLI's execution logs into a private
temporary directory removed at command completion. It preserves the child
exit status and does not retry. A timeout/interrupt stops the local command;
the remote session may still exist. Reconcile its run ID and cancel owned
active sessions as required by `parallel-orchestration.md`.

Inspect only filtered output. Never open the raw temporary logs in a
model-visible tool or attach them to a report. For later resumption, recover
the relevant redaction values from the original authorized source before
reading credential-bearing history; do not put those values in result records.
Remove objective/redaction files when all dependent operations finish. A hard
process kill can leave private temporary files; remove only confirmed stale
files owned by this workflow, never another active task's files.

This helper protects its textual CLI boundary, not Qyrus server retention,
screenshots, videos, downloaded files, or every possible transformation of a
secret. Inspect/redact artifacts before sharing, and verify a live secure
variable/reference facility before saving login inputs for reusable tests.
Do not claim credentials are erased from Qyrus history or a saved test.
