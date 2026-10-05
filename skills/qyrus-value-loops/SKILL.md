---
name: qyrus-value-loops
description: Close a Qyrus quality loop from a connected work item, requirement, bug, PR, incident, or migration objective through generation, testing, evidence, and authorized write-back. Use for autonomous multi-step workflows spanning work management and Qyrus, including mobile/web/API assurance, defect verification, parity checks, and open-ended outcome requests.
---

# Close the loop with evidence

<!-- Distilled from: supplied qyrus_autonomous_value_loops_turbo HTML (2026-09-29), existing plugin skills, Qyrion source contracts, and qyrusai 1.0.9. Roadmap labels are not live capability guarantees. -->

This skill composes the agent's available tools around an outcome. It does
not add a background worker, scheduler, work-management connector, telemetry
system, deployment authority, or permanent memory. Installation is not an
instruction to act on every visible issue.

Read `references/loop-recipes.md` for a matching example; read
`references/loop-contract.md` for execution, resumption, and write-back.
Do not read every reference up front. Examples are starting points, not a
closed list: adapt the same trigger → context → act → verify → evidence
structure to new outcomes using capabilities actually available.

## Establish the scope once

Resolve the source object, desired outcome, environment, authorized actions,
available connectors, and a bounded run/retry budget. Use prior user
authorization; do not ask for the same approval at each step. Clarify only
material ambiguity or a missing capability/permission needed to continue.
Proceed with independent read-only work while that input is pending.

Connection gives access, not blanket authority to comment, transition,
publish, deploy, repair shared data, spend without limits, or delete assets.
For a requested end-to-end loop, complete the authorized steps autonomously;
prepare a concrete write-back or remediation before requesting any missing
authorization. Honor read-only and no-publish constraints throughout.

## Compose only the needed capabilities

| Need | Capability |
|---|---|
| Work-item context and permitted write-back | Existing Jira/Linear/Azure/Rally/GitHub/etc. connector, discovered schemas |
| Generate candidate scenarios/data/assertions | `qyrusai-sdk` skill, shared key |
| Mobile execution | `qyrus-device-testing` and Qyrion |
| Browser execution and observed locators | `qyrus-web-testing` and Qyrion |
| Durable web/API assets and runs | `qyrus-mcp`, live Aegis guide |
| Diff-driven selection | `qyrus-change-impact`; use web execution for web targets |
| Questions during a run | `answer-qyrion-agent-questions` |
| Setup/authentication | `qyrus-setup` |

If a skill is unavailable, use the corresponding embedded contract and live
tool schemas. If a necessary service/tool is absent, say what is unavailable
and finish the remaining useful steps. Do not invent integrations.

## Completion

Every loop ends with a requirement-to-evidence record, verified terminal
outcomes, explicit failures or inconclusive assertions, created/updated
asset IDs, source write-back status, and cleanup status. Generation, a saved
test, a queued run, or an issue transition alone cannot prove the objective.
Do not silently turn a failing check into a pass by weakening its assertion.

Recurring monitoring is separate: use an available host scheduler only when
the user requests recurring work. Specify the scope, credentials path,
budgets, state location, and notification condition; no change means no new
comment. Never imply the plugin itself will keep running after the chat ends.
