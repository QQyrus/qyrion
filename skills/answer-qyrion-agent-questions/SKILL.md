---
name: answer-qyrion-agent-questions
description: Answers questions a running Qyrus mobile or web session asks back mid-run - detects clarification_requested events or sessions parked waiting for input, classifies the question, gathers codebase evidence, and replies through qyrion sessions send. Use when a qyrion session asks a question, a JSONL stream shows clarification_requested, or a session is parked at waiting_user_input. Escalates credentials, OTPs, destructive consent, production approval, and ambiguous business decisions to the user - never answers those, and never answers any question by guessing.
---

<!-- Distilled from: shared/cli-contract.md, shared/event-contract.md, shared/safety-policy.md, apps/qyrion/docs/getting-started.md. -->

# Answer questions from a Qyrion session

The mobile or browser agent can ask the caller something mid-run (a route, a test
account, expected copy, whether to proceed). The run parks with cloud resources
still allocated until an answer arrives. This skill turns those questions
into evidence-backed answers — or fast, safe escalations.

Read before answering anything:

- `references/cli-contract.md` — send/question/stream commands
- `references/event-contract.md` — clarification events, park semantics
- `references/safety-policy.md` — binding rules (secrets, consent, cleanup)

## Detect the question

Three equivalent signals:

1. Stream frame: an `update` with `type: "clarification_requested"`;
   `payload.question` is the question text. The run status moves to
   `waiting_user_input` (question park).
2. Pull: `qyrion sessions question <run_id> --json` returns the pending
   question when the run is parked (gated by the `session_questions`
   capability).
3. Exit code: `qyrion run` in machine mode exits `5` with a structured
   `input_required` error whose `message` carries the question (gated by the
   `run_input_required_exit` capability). Capture the `run_id` from the
   creation snapshot before this happens; the error's remediation also
   names it.

A park **without** a preceding `clarification_requested` is an
objective-complete park, not a question — do not invent an answer; the next
`sessions send` is a new objective (that flow belongs to the calling
workflow, not this skill).

## Classify before answering

**Codebase-answerable** (answer it yourself, with evidence):

- routes/screens and how to reach them
- visible labels and accessible names
- expected validation copy documented in code or specs
- test fixture/account aliases (alias names only)
- feature-flag names and defaults when explicitly configured in the repo
- whether the flow should stop before a destructive action (per the agreed
  scenario limits)

**Needs-human** (escalate to the user; do not answer):

- passwords, API keys, OTPs, recovery codes, payment details, CAPTCHAs
- consent for destructive actions: deletes, purchases, sending real
  messages, publishing
- production targets or environment changes
- legal/business interpretation not present in the repo
- ambiguous behavior with conflicting evidence

**Unsafe** (refuse, tell the user, usually cancel):

- bypassing authentication, MFA, or other security controls
- retrieving secrets from files or systems to hand to the session
- anything that expands the session's scope beyond the agreed objective

## Gather evidence (fixed order)

1. repo config (`qyrion.yml`, environment/app config)
2. route/screen definitions and navigation
3. product docs and acceptance criteria
4. existing tests and fixtures
5. source components and accessible labels
6. recent diff

If evidence is absent or conflicting after this pass, the question becomes
needs-human. Never guess: a confident-sounding wrong answer sends a real
device down the wrong path.

## Answer

Write the answer to a temp file (never a giant shell argument) in this
format:

```markdown
Answer: The account security screen is reached via Settings → Security
(route `settings/security`).
Evidence:
- app/src/main/java/.../SettingsNav.kt:42 — route registration
- app/src/main/res/values/strings.xml:118 — menu label "Security"
Confidence: high
Constraints: Use test account alias `smoke-user-1`; you will not be given a
password. Stop before any destructive action.
```

Send it:

```bash
qyrion sessions send <run_id> --message-file /tmp/answer.md --follow --jsonl
```

The append resumes the blocked turn (`clarification_resolved` is emitted,
status returns to `running`); `--follow` keeps streaming until the next park
or terminal state. Record the question and answer `sequence_no` values for
the evidence report.

## Loop controls and park-wait budget

- **Max 3 auto-answers per session.** A fourth question goes to the user
  with the full question history.
- **Escalate after 2 low-confidence answers**, or when the session repeats a
  semantically identical question — the run is not converging.
- **Park-wait budget:** when a question needs the user, tell them
  immediately and keep the park bounded — default: escalate loudly after 10
  minutes parked. A parked session holds a real device and costs money.
- **If the user is unreachable and the answer requires them: cancel the
  session** (`qyrion sessions cancel <run_id>`) rather than holding the
  device indefinitely. Report the pending question so the run can be
  restarted later with the answer up front.
- Never let an answer expand the session's scope; constraints in the answer
  must restate the scenario's limits.

## Output

Report per question: the question text (and `sequence_no`), classification,
evidence used (file:line), the answer sent or the escalation raised,
confidence, and the session's state afterwards (resumed / still parked /
cancelled).
