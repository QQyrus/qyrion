# Preserve executed coverage when saving tests

Scope: converting Qyrion web/mobile runs into Qyrion or Aegis reusable tests,
including multiple scenarios and long recordings. A summary is not a script.
Use the live CLI/MCP save contract; this reference does not invent save fields.

For Qyrion project/test discovery and reruns, use `session-workflows.md`.
Qyrion supports `projects list` and `tests list --project`; Aegis project/module
IDs must be resolved through Aegis, not substituted from these CLI lists.

## Resolve one destination for the work item

- Reuse the user's selected environment, team, project and module. Read back
  their IDs and relationships. Check scoped local records before creating
  anything; search all relevant inventory pages, not every unrelated project.
- If the user asks to choose existing versus new, ask once with relevant
  options. Otherwise reuse an unambiguous authorized destination. If none is
  known, resolve that choice once for the whole task, not once per scenario.
- Default to **one project and one module for this work item's related
  scenarios** where the destination supports modules. Create separate tests
  for independent scenarios within that module; create a suite only when
  requested/needed. Separate projects/modules require a user choice or a real
  application, team, or access boundary, not a new run ID or retry.
- The coordinating agent resolves/creates the destination once and passes
  the same returned IDs to every parallel worker/process. Workers save tests;
  they must not each create a project/module. Keep Qyrion and Aegis IDs distinct.
- Reconcile an uncertain create by reading/searching before retrying. Retain
  returned IDs immediately. Record supported fields with `local-state.md`;
  keep module relationships and the detailed mapping in the sanitized task
  manifest, not invented flags to the local-record helper.

## Retrieve the complete execution

1. Capture every scenario's run ID and terminal result. Read structured steps,
   not the final chat summary, a screenshot, table preview, or initial snapshot.
   Use `private-execution.md` for input/history containing login details.
2. Check installed help. Current `sessions steps <run-id> --locators --json`
   defaults to **100 rows** and supports `--cursor` and `--limit`. Follow each
   returned `next_cursor` until exhausted. Increasing the limit alone is not
   evidence of completeness; detect repeated cursors and report truncation.
3. Persist sanitized pages incrementally to the user's requested output
   directory (or a private task directory). Use UTF-8 and platform-native paths.
   Preserve run/step IDs, sequence order, action, locator candidates, expected
   result, observed result and status. Do not dump secret-bearing raw history
   into shared JSON; keep private material only as permitted by private execution.
4. Deduplicate by run ID + step ID; repeated actions with different IDs are not
   duplicates. Reconcile retrieved steps against available run/event totals
   and the last executed step. Distinguish tool events from executable actions.
   Persisted steps can lag terminal stream state: perform bounded read-only
   reconciliation, then report any gap as incomplete. Never rerun the app merely
   to hide missing history or invent steps from the original objective.

## Map, save, and read back every scenario

- Create a coverage manifest: `scenario -> run -> source step ID/sequence ->
  saved test ID + saved step position`, with destination IDs and totals.
  Every source step needs a disposition: mapped, consolidated with an explicit
  reason, non-replay observation/retry with reason, or blocked/unmapped.
- Preserve all meaningful actions, navigation, data entry, readiness waits,
  assertions and outcomes in order. Do not compress a 120-step journey into
  12–18 headline steps. Raw observations/retries need not become artificial
  clicks; account for them explicitly. Failed checks remain failed evidence;
  never weaken assertions or describe an unverified repair as passed.
- Split by actual scenario boundaries, not arbitrary lengths. A standalone
  test must include its own required setup/login. Dependent parts must retain
  explicit ordering and supported state handoff; separate tests do not inherit
  another cloud browser's cookies or state.
- Use supported MCP batches/updates if payload limits require chunking.
  Confirm append versus replace semantics first: do not overwrite an earlier
  chunk with the last chunk. Keep IDs/order and reconcile ambiguous writes.
  Missing locators or unsupported actions are gaps, not permission to drop them.
- Parameterize login inputs only through a verified destination contract.
  Sanitized exports may carry clearly marked non-executable placeholders plus
  a binding-needed status. A placeholder is not a working secret alias or a
  runnable test; never save literal secrets merely to satisfy the step count.
- Read back **all saved steps**, including all pages, and compare their order,
  actions, assertions, data bindings and mapping to the candidate. A create
  acknowledgement or a matching count alone does not prove complete coverage.
  For Qyrion `save-test`, verify the actual saved steps too; automatic curation
  is not proof that the user's requested coverage was preserved.
- Report per scenario: retrieved source count, mapped/consolidated/excluded
  counts, unmapped count, saved step count, test ID and read-back result.
  Example: 120 source steps, 18 saved steps, 102 unexplained omissions is
  **incomplete**, never "saved successfully". A justified smaller script needs
  the full mapping. Save verification and a passing rerun are separate claims.

If conversion is incomplete, keep the sanitized export and manifest, name the
missing range/actions and next step, and report partial coverage. Do not create
another project to work around it. Publish only within the user's write-back
scope; redact evidence and verify the post/attachment separately.
