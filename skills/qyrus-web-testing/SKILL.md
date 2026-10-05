---
name: qyrus-web-testing
description: Test a website with Qyrion browser sessions and optionally turn observed behavior into reusable Qyrus web tests through Aegis MCP. Use for a story plus website URL, browser smoke/E2E validation, web bug reproduction, or exploration-to-saved-test workflows.
---

# Web intent to verified automation

<!-- Distilled from: apps/qyrion/docs/getting-started.md, docs/integrations/qyrion-web/README.md, shared/cli-contract.md, supplied A2 value-loop example. -->

Read `references/cli-contract.md`, `references/event-contract.md`, and
`references/safety-policy.md` before execution. Setup uses
`references/credentials.md`. Use Qyrion for browser-agent exploration and
evidence; use the live Aegis guide for durable web assets when requested.

1. Resolve the user's objective and website URL. Read source work items
   through available connectors when relevant. Identify assertions, test
   data, account aliases, target environment, and a finite session budget.
2. Check helper-wrapped `qyrion capabilities --json`: require `web_sessions`;
   `web_live_view` is needed only for local viewing. Verify auth and team.
3. Execute the authorized scenario:

   ```bash
   qyrion run --message-file ./web-objective.md --platform web \
     --start-url https://test.example.com --mode ci --timeout 1800 --jsonl
   ```

   Prefix with the credential helper from `references/credentials.md`.
   Never supply mobile `--device-ref` or `--app` flags to a web run.
   A deployed build/version must match the change being validated.
4. Capture `run_id` immediately. A question or `waiting_user_input` is not
   completion. Apply the clarification policy, inspect result/steps/artifacts,
   and require evidence for each assertion. A submit-only `sessions create`
   still needs later result inspection. Bound streams with `--max-seconds`.
5. For reusable automation, retrieve observed steps with
   `qyrion sessions steps <run_id> --locators --json` (check help/capability
   support first). These contain candidates, not automatically valid Aegis
   steps. Discover `qyrus_guide_get`, read the identifier/step/run contracts,
   resolve the destination, translate observed actions and assertions,
   validate, deduplicate, then save within the authorized scope. Rerun the
   saved asset and inspect terminal results before reporting it reusable.
6. Report requirement → scenario → run → assertion → artifact → saved test
   links/IDs. Cancel only sessions created for this task that remain active;
   record failed cleanup. Return evidence to the source only when authorized.

If Aegis is unavailable, finish Qyrion verification and retain a local export
candidate with observed locators. Say the durable asset is not yet created.
Do not fabricate a tool name, destination ID, locator, or saved-test success.
