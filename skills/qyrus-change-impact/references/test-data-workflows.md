# Project variables and test-owned datasets

Check `qyrion capabilities --json` before using this workflow. Require
`project_references`, `project_variable_management`, `test_dataset_management`
`rerun_test_data_preflight` and `variable_types` in `features`. With Qyrion MCP, call
`qyrion_capabilities` and discover the tool schemas first. If a required
capability or tool is absent, refresh Qyrion and the plugin; report an older
backend rejection as a blocker rather than inventing a raw API workaround.
The hosted Aegis MCP and Qyrion MCP are separate servers.

## Discover before writing

List projects, then tests and their dataset metadata before creating anything.
Reuse confirmed IDs from the current environment/team. Ask the user to choose
when several projects match; never select the first silently. Fresh sessions
use flat project variables; named datasets belong to saved tests, not projects.
List variable metadata with search/pagination before proposing duplicates.

## Fresh session and Default capture

Create or update variables through `projects variables`. Names use uppercase
letters, digits and underscores; no `@` prefix is stored. Values are supplied
by `--value-file <path>` or `--value-file -` (stdin), or the hidden prompt.
New project variables default to `secret`; updates keep their current kind
unless `--kind text|secret` is supplied. Changing an existing Secret to Text
asks for interactive confirmation; automation must pass
`--confirm-secret-to-text`. Updates require the current `--revision`. Use
authorized values only.

```bash
qyrion projects variables list --project <project-id> --json
qyrion projects variables create --project <project-id> --name LOGIN_USER --value-file ./user.txt --json
qyrion run --project <project-id> --message-file ./objective.md --platform web --start-url https://test.example.com --mode ci --jsonl
qyrion sessions save-test <run-id> --project <project-id> --test-name "Login check" --json
```

The objective can say `Log in using @LOGIN_USER and @LOGIN_PASSWORD`.
Send literal references; never resolve them in the plugin or fetch saved values
to construct an objective. `sessions create` also accepts `--project`.
Follow-up messages use the established session project. A reference without
a selected project must be corrected before provisioning. Saving captures
Default automatically; old save-data flags are compatibility options, not
an opt-out. New saves do not require `prepare`.

## Manage and rerun test data

Use `tests datasets list|get|create|update|delete|prepare|template|export`
with `--test <test-id>`. Create/update accept a JSON file or stdin containing
string values and optional `--types-file <path|->`, a name-to-`text`/`secret`
JSON object. Values and types cannot both read from stdin. New dataset keys
default to `secret` when their kind is omitted; existing keys preserve their
kind unless the type map explicitly changes it. A type-only update is
supported. Changing an existing Secret to Text asks interactively or requires
`--confirm-secret-to-text` in automation. Obtain `template` to get Default's
names with empty values; fill the values explicitly instead of copying secrets
from Default.
`template --typed` returns `{ "values": ..., "variable_kinds": ... }`.
Updates use the current revision. MCP key removal also requires `confirmed: true`;
terminal key removal requires confirmation or `--yes`. Preserve omitted values and explicitly
remove unwanted names. Renaming a variable creates a new identity; differently
named keys are never inferred as equivalent. `prepare` is for legacy datasets.

```bash
qyrion tests datasets list --test <test-id> --json
qyrion tests datasets template --test <test-id> --json
qyrion tests datasets create --test <test-id> --name QA --values-file ./values.json --types-file ./types.json
qyrion tests rerun <test-id> --check-test-data --json
qyrion tests rerun <test-id> --test-dataset <dataset-id> --check-test-data --json
qyrion tests rerun <test-id> --test-dataset <dataset-id> --json
```

Reruns need no new objective. Web uses its saved URL unless explicitly
overridden; datasets never change that URL. Mobile still needs a valid device.
Omitted selection follows the saved test default or source run's selection.
An alternate source affects only that run unless the user explicitly requests
remembering it. `--project-test-data` selects project variables;
`tests rerun --dataset` preserves legacy arbitrary-JSON execution variables;
it is separate from the reference-based `--test-dataset` selector. Legacy
datasets need no registry preparation. Do not combine these selectors, even
with the same ID. Reference preflight, replacements and saved-source preferences
require `--test-dataset` or `--project-test-data`. For legacy data, rerun the
owning saved test; session replay uses `--test-dataset` for reference-based data.
The selected reference source must contain every required key;
missing keys never fall back to another source.

The saved-test UI rerun selector offers test-owned datasets. Project variables
remain an explicit source through the CLI, MCP, and API; the UI scope does not
remove `--project-test-data` or `project_test_data` from those interfaces.
Historical-run replay without an override keeps its recorded source. Choosing a
test dataset for replay applies only to the new run and never changes the
historical run or the saved-test default.

Preflight returns readiness, issues, safe identities and `test_updated_at`.
Do not start when it is not ready. A deleted/recreated variable requires
explicit user confirmation of the exact name, previous ID and new ID; pass
`--confirm-test-data-replacement NAME:OLD_ID:NEW_ID` only after that confirmation.
Recheck when identities change. Persisting a selected default or replacement
requires the current test revision and explicit preference flags; a historical
session replay must never mutate its source run. A concurrent edit means reload
and reconcile, not retry with an invented revision. Authoritative Start checks
still apply after successful preflight.

Ordinary list/get/template/preflight responses contain metadata and masks.
Secret values are masked in ordinary dataset reads; Text values remain visible.
Templates and type-confirmation checks request metadata only. `export --typed`
keeps the default values-only format unless explicitly selected and writes
`{ "values": ..., "variable_kinds": ... }` to the requested file.
Only an explicit user request to export saved values permits
`tests datasets export <dataset-id> --test <test-id> --output <new-local-file>`.
Do not read/export values merely to choose data or run a test. Never put an
export in chat, source control or evidence. Deletion needs explicit confirmation
(interactive or `--yes` for an already-authorized automation).

## MCP parity

Use structured arguments directly, never shell out from MCP tools:

| Workflow | Qyrion MCP tools |
|---|---|
| Variables | `qyrion_list_project_variables`, `qyrion_create_project_variable`, `qyrion_update_project_variable`, `qyrion_delete_project_variable` |
| Datasets | `qyrion_list_test_datasets`, `qyrion_get_test_dataset`, `qyrion_create_test_dataset`, `qyrion_update_test_dataset`, `qyrion_delete_test_dataset`, `qyrion_prepare_test_dataset`, `qyrion_test_dataset_template` |
| Explicit private export | `qyrion_export_test_dataset` with a new local `output` path |
| Readiness | `qyrion_project_test_data_preview` with `subject_id` and `source: test` or `run` |
| Saved preferences | `qyrion_save_test_data_preference` with `expected_test_updated_at` and requested save flags |
| Execution | `qyrion_create_session` with `project_id`; `qyrion_save_session_as_test`; `qyrion_rerun_test` or `qyrion_rerun_session` |

Rerun/preflight selection uses `test_dataset_id` or `project_test_data: true`.
Replacement objects contain exactly `name`, `previous_id`, `variable_id`.
Saved-test preference flags are `save_test_data_default` and
`save_test_data_replacements`; neither is supported on historical-run replay.
Management edits require revisions; deletion requires `confirmed: true`.
Create/update schemas accept `kind` or `variable_kinds`; Secret-to-Text changes
require the top-level `confirm_secret_to_text: true` field.
After submission retain the new run ID, inspect terminal results and steps,
and stop task-owned sessions. A successful submission is not a passing test.
Apply the advisory replay rules in `event-contract.md`: retain separate passed,
failed and unverified counts and the unverified reasons. Completed status,
exit 0 and `is_error: false` do not turn an advisory check into a pass.

## Pre-send masking and consent

The browser composer detects supported labelled credentials before Send. Secret
chips remain hidden; explicitly marking a chip Not secret requires the user's
consent. Users may change that choice until Send. Sent choices are immutable.
Only the final submitted choice is audited, without storing values in the consent
row; saving the test captures used inputs in encrypted Default data.

Qyrion CLI/MCP do not provide the browser's interactive chips or eye controls.
Prefer project references for terminal/agent workflows. Ordinary objectives with
no reviewed-input envelope retain backend Secret handling. Never claim consent
on the user's behalf, invent a receipt, or treat project/dataset Text as permission
to send its value literally to the model. The shared client supports typed
reviewed-input transport for callers that actually collected the explicit choice;
its decision API uses the CLI gateway alias. This is not a new terminal reveal UI.
