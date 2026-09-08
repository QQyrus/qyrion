---
name: qyrus-device-testing
description: Tests the app being built on real cloud devices end to end - discovers user journeys from the codebase, proposes ranked test scenarios, uploads the app build, and drives Qyrus AI device sessions through the qyrion CLI to a verdict-and-evidence report. Use for requests like "test this app/build on a real device", "run a smoke or E2E pass on device", or "verify this app build". Do not use for web browser testing, for selecting tests from a specific git diff or PR (use qyrus-change-impact), or for plain qyrion command help (use qyrion-cli).
---

# Test the app on real devices

Turn "test my app" into ranked scenarios, then into Qyrion device sessions,
then into a verdict-and-evidence report. This skill owns scenario quality;
the CLI mechanics live in the embedded references.

Read before starting:

- `references/cli-contract.md` — CLI resolution, handshake, command catalog
- `references/event-contract.md` — JSONL frames, park semantics, artifacts
- `references/safety-policy.md` — binding rules (production, secrets, cleanup)
- `references/parallel-orchestration.md` — multi-scenario fan-out
- `references/scenario-format.md` — required scenario fields and ranking
- `references/qyrion-yml.md` — optional repo mapping file

## Phase A — Preflight

1. CLI handshake: `qyrion capabilities --json` (resolution order and failure
   guidance in the CLI contract). Abort with install/upgrade instructions if
   missing or too old.
2. Auth + team: probe with `qyrion auth teams --json`. If it fails or no team
   is selected, run the first-run setup flow from
   `references/cli-contract.md` § "Authentication, profiles, and first-run
   setup" (user runs `qyrion configure` in their own terminal, or exports the
   env vars; multiple teams → ask the user which one, then
   `qyrion auth use-team <team-id>`). Never prompt for or print the three
   credential values.
3. Project mapping: if the repo has a `qyrion.yml`, parse it for app
   name/platform, preferred device pool, path→journey hints, and test-account
   aliases (see `references/qyrion-yml.md`). It is optional — proceed without
   it, but say so.
4. Locate the app build: an `.apk`/`.aab`/`.ipa` the user names, or the most
   recent build output in the repo. If there is no build, stop and ask —
   never guess a binary.
5. Confirm the target is not production (safety policy). Default to
   staging/test configuration.

## Phase B — Discovery: propose scenarios from the codebase

Inspect only relevant evidence; do not infer journeys from filenames alone:

- route/navigation definitions and screen registries
- screens/components and their accessible labels and visible copy
- API clients and feature flags that change UI behavior
- existing tests (unit/E2E) and fixtures/test accounts
- product docs and acceptance criteria when present
- error, empty, and loading states
- `qyrion.yml` path→journey hints

Produce ranked scenarios. Rank by, in order:

1. user/business criticality
2. changed or untested surface
3. regression likelihood
4. observability and determinism
5. setup cost and destructive risk

Every scenario carries: title, intent, preconditions/data, user-intent steps,
assertions, evidence to capture, confidence, and the source files that
justify it (full field spec in `references/scenario-format.md`).

Deduplicate against saved tests when a project id is known:
`qyrion tests list --project <id> --json` → classify each proposal as
`covered`, `extend_existing`, or `new`.

## Phase C — Plan gate (default: stop and ask)

Present the ranked scenario table (title, intent, device, est. sessions,
risk) and get the user's approval before any device run, unless the user
already pre-approved the exact scope ("run the top 3 smoke scenarios" counts;
"test my app" does not). Device runs cost real device time.

In plan-only requests, stop here and output the plan.

## Phase D — App upload (dedup-aware)

```bash
qyrion apps upload ./app-release.apk --platform android \
  --name "<app-name>" --skip-if-uploaded --json
```

`--skip-if-uploaded` computes the build's sha256 and reuses an existing
identical upload instead of re-uploading. Capture the returned app id. If the
flag is unavailable (old CLI), fall back to matching `qyrion apps list
--json` by name/version and tell the user which build you matched.

Pick the device from `qyrion.yml`'s preferred pool, the user's request, or
`qyrion devices list --platform <p> --json` (choose one sensible default,
don't fan out across devices without approval).

## Phase E — Execution: one session per scenario

One-shot scenarios (single objective, pass/fail): use ci mode —

```bash
qyrion run --message-file ./scenario-01.md \
  --device-ref <device-ref> --app <app-id> --mode ci --timeout 1800 --jsonl
```

Multi-step scenarios: use the live-mode turn loop, one session per scenario:

1. `qyrion sessions create --message-file ./step-1.md --device-ref <ref>
   --app <app-id> --mode live --jsonl` → capture `run_id` from the first
   snapshot frame.
2. `qyrion sessions stream <run_id> --jsonl --until input-required
   --max-seconds 900`.
3. Inspect the segment's events; download the latest `observe_raw` screenshot
   (`sessions artifacts` → `sessions download`) and look at it — screenshots
   are the ground truth for assertions.
4. Decide: send the next objective (`sessions send <run_id> --message-file
   ./step-N.md --follow --jsonl`), answer a `clarification_requested`
   question (from repo evidence only; escalate secrets/consent per the safety
   policy), or finish.
5. When the scenario is done: let it complete, then `sessions result
   <run_id> --wait --json`; or `sessions cancel <run_id>` if aborting.

Multiple scenarios: fan out per `references/parallel-orchestration.md` — one
subagent per session, 2–3 concurrent max, `PENDING_CONCURRENCY` means wait,
unique run names, and a mandatory final cancel-sweep.

Objectives sent to the device agent must be user-intent level ("log in as
alias smoke-user-1 and verify the dashboard shows the Projects list"), carry
the scenario's assertions, and embed the safety limits (stop-before points,
no destructive actions). Never include credentials — aliases only.

## Phase F — Evidence report

For each scenario report:

- verdict: `passed` / `failed` / `blocked` / `inconclusive` / `cancelled` —
  passed requires the run completed AND the assertions are supported by
  evidence, not merely exit 0
- run_id and final status
- evidence: downloaded artifact file paths + event `sequence_no` citations
- failure triage when applicable: app bug vs. wrong scenario assumption vs.
  environment/data issue vs. flake
- open risks and human decisions needed

End with the leftover-session sweep (`sessions list --json` → cancel anything
you started that is still `running`/`waiting_user_input`) and state its
result in the report.
