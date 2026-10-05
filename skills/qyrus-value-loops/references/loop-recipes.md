# Adaptable value-loop recipes

Scope: examples adapted from the user-supplied *QyrusAI Autonomous Value
Loops — Structural Edition* HTML. Its labels were A1/A2 active, A3–A7
"source: platform ready", O1–O5/M1–M6 proposed. Those are source labels,
not independently verified availability. Discover actual tools and permissions
for each task. This plugin supplies orchestration instructions, not the
external infrastructure required by every recipe.

## Assurance

| Loop | Composition | Proof needed |
|---|---|---|
| A1 Mobile quality | Read acceptance criteria → Nova candidates → Qyrion real-device runs → authorized source update | Requirement assertions plus result, screenshots/video/logs; OTP handled via the user's secure platform flow |
| A2 Web quality + MCP export | Story + site URL → Qyrion browser exploration → observed locators → Aegis validation/save/rerun | Trace and assertions from the saved asset's rerun, not just its successful creation |
| A3 API + contract | OpenAPI/Postman/observed response → candidate positive/negative/schema/auth checks → live Aegis API guide → suite execution | Actual responses and contract assertions; SLA claims need measured latency and defined thresholds |
| A4 Reproduce + verify fix | Bug + environment → smallest reproduction → capture baseline failure → changed build → same assertions | Before/after evidence with build IDs; do not call an unreproduced bug fixed |
| A5 Cross-channel journey | Test API setup → web action → mobile action → reconcile shared state | Correlation IDs and state transitions across channels; requires each capability and authorized test data |
| A6 Locator repair | Read failing step + current DOM/image evidence → propose replacement → validate original assertion → persist authorized repair | Before/after locator, rationale, unchanged functional assertion, successful bounded rerun |
| A7 PR gate | Diff + source intent → minimal impacted tests → correct deployed build → execution → permitted check/comment | Test mapping, terminal outcomes, build SHA; merge authority remains separate |

## Operations: conditional on external connectors and authority

| Loop | Useful work with this plugin | Additional capability required to close |
|---|---|---|
| O1 Service assurance | Reproduce the affected journey with targeted web/API/mobile probes | Readable SLO/telemetry and approved baseline/thresholds |
| O2 Incident diagnosis + remediation | Correlate supplied diagnostics, rank hypotheses, verify a recovery proposal with tests | Telemetry/change inventory; explicit remediation authority, rollback and recovery checks |
| O3 Progressive delivery | Test impacted journeys; compare available cohort evidence | Release controller, telemetry, exposure/rollback authority |
| O4 Environment/data recovery | Separate blocked setup from product defects; generate synthetic candidate data; rerun after repair | Environment/data write tools, precise repair scope and rollback |
| O5 Capacity/cost | Compare supplied cost/latency evidence and draft bounded tuning experiment | Cost/utilization sources, change controller, rollback and measurement window |

## Modernization: prove a small slice

| Loop | Useful work with this plugin | Additional capability required to close |
|---|---|---|
| M1 Legacy characterization | Capture observed journeys and create executable baselines | Authorized legacy access; dependency/traffic sources for claims beyond observed behavior |
| M2 Migration parity | Run the same representative journey on legacy and target; explain output/rule/latency deltas | Both targets, equivalent datasets and versions, agreed tolerance; migration authority for cutover |
| M3 API extraction | Draft candidate contracts/assertions from supplied evidence; validate known consumers | Source/traffic inventory and implementation/deployment tools for actual extraction |
| M4 Portfolio conversion | Inventory authorized scripts; translate candidates via Aegis guide; run old/new equivalents | Existing runner and coverage history; retirement is a separately reviewed action |
| M5 Data reconciliation | Compare authorized extracts and business rules; produce discrepancy evidence | Readable source/target data, reconciliation rules, migration/repair authority |
| M6 Decommission readiness | Produce residual-use and test-parity evidence available from connected sources | Traffic/dependency inventory, rollback drill, explicit cutover/retirement authority |

For an unlisted scenario, identify the trigger, desired change, measurable
proof, available tools, missing dependencies, and return destination. Build
the smallest useful loop from those facts. If a dependency is missing, finish
the evidence or proposal stage and name the precise remaining step.
