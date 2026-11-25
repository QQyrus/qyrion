---
name: qyrus-setup
description: Check existing Qyrus capabilities and identify which testing tasks can run in this session.
---

# Check Qyrus access

Inspect the tools already available to Claude. If Qyrus tools are present, use their guide and a read-only team lookup to confirm the tenant and team. On a host with terminal access and an existing Qyrion client, use `qyrion capabilities --json` to check the client and `qyrion auth teams` to confirm CLI access.

When a task needs a missing standalone dependency, identify it. If the user asks Claude to install it and the session has terminal, network, and installation permissions, carry out the requested installation in that environment. For Qyrion, follow the platform instructions at [Qyrion releases](https://github.com/QQyrus/qyrion/releases) for the CLI binary. For the Python SDK, use the [qyrusai package](https://pypi.org/project/qyrusai/) and the user's project environment. Verify Qyrion with `qyrion capabilities --json` or verify that the selected Python interpreter can import `qyrusai`, then resume the task. If the host prevents installation, explain which permission or capability is missing and provide the relevant installation link.

Use the available capabilities for the requested task. If a required capability is unavailable, tell the user which operation needs it. Continue with work that can be done in this session, such as drafting test scenarios and expected results. Keep credentials private and distinguish proposed tests from executed tests.
