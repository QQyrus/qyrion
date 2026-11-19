# Scenario format and ranking

The unit of work for device testing is a scenario. One scenario maps to one
Qyrion session.

## Required fields

| Field | Content |
|---|---|
| `id` | Short slug, unique in the plan (e.g. `login-happy-path`) |
| `title` | One line, user-visible framing |
| `intent` | What user/business behavior this protects, one sentence |
| `preconditions` | App state, test-account **alias** (never credentials), seeded data, flags |
| `steps` | Ordered user-intent steps ("tap Log in", not coordinates or selectors) |
| `assertions` | Observable outcomes to verify, each checkable on a screenshot or in app copy |
| `evidence` | What to capture: which screens to screenshot, which copy to confirm |
| `safety_limits` | Stop-before points and forbidden actions for this scenario |
| `mode` | `ci` (single objective, one-shot) or `live` (multi-objective turn loop) |
| `confidence` | high / medium / low that this scenario reflects real product behavior |
| `sources` | Repo files (path:line where useful) that justify steps and assertions |

## Ranking order

Score and order scenarios by, in priority order:

1. **User/business criticality** — login, core value path, payments-adjacent
   flows first.
2. **Changed or untested surface** — recently touched code, screens with no
   existing coverage.
3. **Regression likelihood** — complex state, validation, async/error paths.
4. **Observability and determinism** — prefer scenarios whose assertions are
   clearly visible on screen and repeatable.
5. **Setup cost and destructive risk** — cheap, safe scenarios outrank ones
   needing rare data or approaching destructive actions.

Propose a focused set (typically 3–7), not a permutation dump. Anything
ranked below the cut still appears in the plan as "not selected" with a one
line reason.

## Objective text for the device agent

When a scenario becomes a session objective (`--message-file`), write it as:

```markdown
Objective: <one sentence goal>

Steps:
1. <user-intent step>
2. ...

Verify:
- <assertion 1>
- <assertion 2>

Limits:
- Use the authorized test account for this target; follow the supplied
  login instructions and ask if a required detail is missing.
- Stop before <destructive/confirmation point>; do not confirm it.
- If something is ambiguous or blocked, ask instead of improvising.
```

Planning files contain account labels only, never credentials. Supply any
authorized target-account details separately under `safety-policy.md`; labels
are not automatically resolved by the CLI. Keep one scenario per session;
do not chain unrelated scenarios into one run. Serialize dependent scenarios
or carry them in one session when they require its state.

## Dedup classes against saved tests

Compare each proposal to `qyrion tests list --project <id> --json` by
journey, step intent, and expected outcome:

- `covered` — an existing saved test already asserts this; rerun it when
  reuse is the user's intent. Explicit new coverage still uses a fresh
  Qyrion session; this classification informs the save/dedup decision.
- `extend_existing` — an existing test is close; propose or perform the
  authorized update. Do not substitute its run for an explicitly requested
  new objective.
- `new` — no adequate coverage; run as a fresh session. Only persist it
  (`sessions save-test`) after inspecting the run and within the requested
  save scope. A request to create and save is already authorization; do not
  ask for the same permission again. Follow `execution-routing.md`.
