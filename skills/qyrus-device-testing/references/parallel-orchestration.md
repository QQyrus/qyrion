# Parallel session orchestration (plugin copy)

How to fan multiple Qyrion device sessions out to subagents safely. Applies
whenever more than one scenario should run on devices in the same task.

## Ownership model: one subagent per session

Each subagent owns exactly one session for its full lifecycle:

```text
create --jsonl (capture run_id)
  → stream --until input-required --max-seconds <budget> --jsonl
  → inspect events + download latest observe_raw screenshot
  → decide: send next objective (--follow) | answer question | finish | cancel
  → repeat until terminal
  → result --json (verdict) + artifact downloads
```

Rules:

- The subagent receives the full scenario (objective sequence, assertions,
  device-ref, app id, park-wait budget) up front and returns a structured
  verdict — it must not need to ask the orchestrator mid-run.
- The subagent embeds the CLI contract, event contract, and safety policy —
  never assume another skill is loaded in the subagent's context.
- A subagent never touches a run_id it did not create.
- Every subagent ends with its session in a terminal state: completed,
  failed, or explicitly cancelled. No parked sessions may outlive a subagent.

## Concurrency caps

- Start with 2–3 concurrent sessions, never more without user approval.
- Device Farm capacity is the real limit. A session sitting in
  `PENDING_CONCURRENCY` is waiting for a device slot: do not start more
  sessions while one is pending — wait or reduce concurrency.
- Queue remaining scenarios and start the next only when a slot frees
  (a running session reaches terminal state).

## Naming and idempotency

- Give every session a unique, greppable run name:
  `<app>-<scenario-slug>-<yyyymmddHHMM>` (e.g. via `--run-name` where
  supported, otherwise in the objective preamble).
- When `capabilities` reports `idempotent_create: true`, key creates on
  `{project, commit, scenario, device}` so a retried subagent re-attaches to
  its existing run instead of double-allocating a device.

## Aggregation

The orchestrator collects from every subagent:

- scenario id + title
- verdict: `passed` / `failed` / `blocked` / `inconclusive` / `cancelled`
- run_id and final status
- evidence: local artifact file paths + event `sequence_no` citations
- open questions or escalations raised mid-run

Render one report table for the user. A scenario is only `passed` when the
run completed AND the scenario's assertions are supported by the evidence —
not merely because exit code was 0.

## Mandatory final sweep

At the end of the task — success, failure, or user abort — the orchestrator
must sweep for leaked sessions:

```bash
qyrion sessions list --json
```

Filter for sessions created by this task with status `running` or
`waiting_user_input`, and cancel each:

```bash
qyrion sessions cancel <run_id>
```

Cancellation is idempotent; cancelling an already-terminal run is safe.
Report any session that could not be cancelled so the user can stop it from
the Qyrus UI. Never skip the sweep: a leaked parked session holds a real
device indefinitely.
