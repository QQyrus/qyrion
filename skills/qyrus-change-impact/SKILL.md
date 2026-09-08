---
name: qyrus-change-impact
description: Selects the minimal real-device test set for a specific code change - reads the git diff, classifies behavior changes, maps them to existing saved Qyrus tests and new scenarios, produces an action plan table, then runs only the impacted set through the qyrion CLI. Use for "what should I test for this change/PR/diff", "validate this branch on a real device", or post-merge device validation of a change. Do not use for broad test generation from scratch with no diff in scope (use qyrus-device-testing) or for plain qyrion command help (use qyrion-cli).
---

# Diff-driven minimal device test selection

Given a base..head diff, decide which device tests must run unchanged, be
updated then run, be newly created, or be proposed for retirement — then run
only that minimal set and triage the results.

Read before starting:

- `references/cli-contract.md` — CLI resolution, handshake, command catalog
- `references/event-contract.md` — JSONL frames, park semantics, artifacts
- `references/safety-policy.md` — binding rules (production, secrets, cleanup)
- `references/parallel-orchestration.md` — running the selected set
- `references/change-classification.md` — classification taxonomy and mapping

## Phase 1 — Preflight

1. `qyrion capabilities --json` handshake (abort with install/upgrade
   guidance per the CLI contract if missing/old), then auth probe with
   `qyrion auth teams --json` — on failure or missing team selection, follow
   the first-run setup flow in `references/cli-contract.md`
   § "Authentication, profiles, and first-run setup" (multiple teams → ask
   the user; persist via `qyrion auth use-team <team-id>`).
2. Determine base and head revisions. Default to the merge base with the
   default branch and the working head; state what you chose.
3. Parse `qyrion.yml` if present for path→journey hints, project id, and
   preferred devices. Optional — proceed without it.
4. Confirm the changed build is actually what will run on device (a fresh
   build containing head). If you cannot confirm, produce the plan but say
   clearly that execution would not validate this change.

## Phase 2 — Read and classify the diff

```bash
git diff --name-status <base>...<head>
git diff <base>...<head> -- <interesting paths>
```

Classify every behavior-relevant change with the taxonomy (details and
signals in `references/change-classification.md`):

```text
screen_added | screen_removed | flow_changed | validation_changed |
label_changed | api_contract_changed | copy_only | style_only | unknown
```

`copy_only`/`style_only` rarely justify device runs; `unknown` must never be
silently dropped — it becomes an `investigate` row.

## Phase 3 — Map to existing tests and scenarios

Fetch the saved-test inventory when a project id is known:

```bash
qyrion tests list --project <project-id> --json
qyrion tests get <test-id> --json     # steps/objective for close candidates
```

Evidence priority when mapping changes to tests: explicit `qyrion.yml`
journey mappings → test objective/steps that reference the changed screen or
flow → repo call graph and component ownership → name similarity (weak signal
only). For gaps, draft new scenarios (same scenario shape the device-testing
workflow uses: title, intent, steps, assertions, evidence, confidence,
sources).

## Phase 4 — The plan table (always produced, before any run)

One row per credible test/scenario:

```text
action | test/scenario | evidence | confidence | risk
```

`action` is one of:

| Action | Meaning |
|---|---|
| `run_unchanged` | behavior may regress but the saved test still matches the contract |
| `update_then_run` | steps/assertions/labels must change first (propose the exact edit) |
| `create_then_run` | new behavior lacks coverage; new scenario drafted |
| `retire_candidate` | removed behavior makes a test obsolete — **propose only, never delete** |
| `investigate` | evidence insufficient or conflicting |
| `not_impacted` | no credible path from the change to the scenario |

Confidence: high = explicit mapping plus matching steps; medium = strong code
path but no exact step match; low = name similarity or shared dependency
only. Do not run mutations from low-confidence rows without user review.

Stop here and get approval before device execution unless the user
pre-approved running the selected set. Never delete tests under any
instruction level — retirement is always a proposal for a human.

## Phase 5 — Execute the minimal set

- `run_unchanged` rows with a saved test: `qyrion tests rerun <test-id>
  --device-ref <ref> --app <app-id> --jsonl`.
- `update_then_run`: apply the approved edit (`qyrion tests update`) first,
  then rerun; record before/after.
- `create_then_run` and ad hoc scenarios: one session per scenario via the
  turn loop — `sessions create --jsonl` (capture run_id) → `stream --until
  input-required --max-seconds 900` → inspect events + download the latest
  `observe_raw` screenshot → `send --follow` next objective or finish →
  `result --wait --json`. ci mode for single-objective checks.
- Ensure the changed build is uploaded first: `qyrion apps upload <build>
  --skip-if-uploaded --json`.
- Include a minimal smoke dependency (e.g. login) when the changed flow sits
  behind it.
- Bounded parallelism and the mandatory final cancel-sweep per
  `references/parallel-orchestration.md`.

## Phase 6 — Triage and report

Classify every non-pass before blaming the product:

- **product regression** — evidence in screenshots/events that head behavior
  broke the assertion
- **stale test** — the diff intentionally changed the behavior the test
  asserts (feeds an `update_then_run` proposal)
- **environment/deployment mismatch** — wrong build, backend not matching
  head, missing test data
- **flaky** — timing/nondeterminism; rerun once before claiming flake
- **tool/backend failure** — qyrion or device-cloud errors, not the app

Report: the classified diff summary, the plan table with final outcomes per
row, verdicts with artifact file paths and event `sequence_no` citations,
proposed test updates/retirements awaiting human review, and the result of
the leftover-session sweep.
