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
- Use test account alias `<alias>` (the platform resolves it; you will not
  be given a password by me).
- Stop before <destructive/confirmation point>; do not confirm it.
- If something is ambiguous or blocked, ask instead of improvising.
```

Never include credentials, OTPs, or secrets. Keep one scenario per session;
do not chain unrelated scenarios into one run.

## Dedup classes against saved tests

Compare each proposal to `qyrion tests list --project <id> --json` by
journey, step intent, and expected outcome:

- `covered` — an existing saved test already asserts this; prefer
  `qyrion tests rerun <test-id>` over a new session.
- `extend_existing` — an existing test is close; propose the extension, run
  the existing test now, and leave the test update as a follow-up proposal.
- `new` — no adequate coverage; run as a fresh session. Only persist it
  (`sessions save-test`) after a stable run and with user approval.
