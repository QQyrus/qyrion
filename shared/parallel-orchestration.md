# Parallel web and mobile sessions

Scope: a Qyrus task whose objective can be divided into independent scenarios.
Parallel sessions are supported through multiple Qyrion CLI invocations from
one agent. Subagents are optional, not a prerequisite.

## Establish independence first

Split by independent outcomes with separate assertions and run IDs. Check
account login rules, mutable test data, application state, device capacity,
and ordering dependencies. Independent browsers/devices do not prove that
the application's account or backend state is independent.

- Separate accounts/data, or a known policy permitting concurrent logins and
  nonconflicting state: run in parallel within the authorized scope/budget.
- Same account with unknown simultaneous-login behavior: ask the one relevant
  question, **"Can this test account be signed in on multiple sessions at once?"**
  Reuse a prior answer for the same account policy/scope; do not ask every run.
  While unanswered, execute sequentially if that safely meets the request.
- Shared cart/profile mutation, one-login policy, or prerequisite/dependent
  journeys: serialize the affected objectives. Do not force a parallel split.
- A single end-to-end journey stays together when later checks depend on the
  earlier session's login or state.

Start with up to 2–3 independent sessions, or the user's lower run/concurrency
budget. Do not expand into an unrequested device/browser matrix. More than
three at once needs an agreed concurrency budget. When a session is
`PENDING_CONCURRENCY`, stop submitting more and wait for capacity.

## One lifecycle owner per session

The parent may own several independent sessions, or assign one to each
available subagent. Each session has exactly one owner for sending messages,
answering questions, collecting evidence, and cleanup. Pass the scenario,
target, assertions, deadline, and safety limits to an assigned owner.
Give subagents the CLI/event/safety contracts; do not assume their context.

For each web objective, submit a separate helper-wrapped command:

```bash
qyrion sessions create --platform web --start-url https://test.example.com \
  --message-file ./objective-01.md --mode ci --timeout 1800 \
  --run-name checkout-cart --jsonl
```

For mobile, use `--platform mobile --device-ref <ref> --app <app-id>` instead
of `--start-url`. For supplied test credentials, use `private-execution.md`'s
wrapper for the create and all history reads; never put values in arguments.
Give each lifecycle owner access only to its authorized private inputs, not
literal credentials in subagent prompts or result records. `sessions create`
without `--stream` submits the run and returns while it continues remotely.
Capture `run_id` immediately, record ownership, then submit the next
independent objective. Separate `qyrion run` processes are also valid.

Monitor **all** active run IDs using bounded `sessions stream` calls or result
polls; do not wait indefinitely on one while another is parked. Answer
clarifications promptly. Stop launching new work if a shared setup failure
invalidates the remaining objectives. Unique `--run-name` values help
reconciliation; they are not an idempotency guarantee. After an ambiguous
create, reconcile `sessions list` and the recorded IDs before retrying; do
not invent a CLI idempotency flag.

## Aggregate and clean up

Collect each scenario's verdict, run ID, final status, supported assertions,
local artifact paths/event sequence numbers, and pending questions. A pass
requires assertion evidence, not merely CLI exit 0. Save scoped IDs/outcomes
per `local-state.md`; no raw objectives or login details belong there.

At task completion, failure, or abort, inspect `qyrion sessions list --json`
and reconcile every task-owned ID. Cancel task-owned sessions still active,
including pending/running/parked sessions, using
`qyrion sessions cancel <run_id>`. Do not cancel another task's sessions.
No active session may outlive its owner; report any failed cancellation so
the user can stop it. Respect finite run/park budgets from `safety-policy.md`.
