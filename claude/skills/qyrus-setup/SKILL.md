---
name: qyrus-setup
description: Check existing Qyrus capabilities and identify which testing tasks can run in this session.
---

# Check Qyrus access

Inspect the tools already available to Claude. If Qyrus tools are present, use their guide and a read-only team lookup to confirm the tenant and team. On a host with terminal access and an existing Qyrion client, use `qyrion capabilities --json` to check the client and `qyrion auth teams` to confirm CLI access.

## User-requested installation

When the user requests installation of a missing standalone tool, use the matching artifact below. This skill pins Qyrion CLI to **0.4.3-beta** and the qyrusai Python SDK to **1.0.9**.

1. Select the exact CLI artifact for the host OS and architecture, or the SDK wheel for the user's Python environment. If there is no matching artifact or the host lacks installation permissions, stop and explain the limitation.
2. Save the linked artifact to a local file. Before extracting, installing, importing, or running it, compute the SHA-256 of the complete file and compare it to the literal digest in that row. On a missing or mismatched digest, stop and report the failure. Never substitute another release, artifact, or remote checksum.
3. Install from that verified local file. For the CLI, place the Windows executable or the binary from the verified archive on the user's executable path. For the SDK, install the local wheel in the selected project environment. Verify the CLI capabilities or SDK import before resuming the task.

| Artifact | Required SHA-256 |
| --- | --- |
| [qyrion-0.4.3-beta-linux-x64.tar.gz](https://github.com/QQyrus/qyrion/releases/download/qyrion/v0.4.3-beta/qyrion-0.4.3-beta-linux-x64.tar.gz) | `1a71f11dfd11af852e6d86fe8d4e4ecdcdd3cae30533d44bcb8471832c1cfd76` |
| [qyrion-0.4.3-beta-macos-arm64.tar.gz](https://github.com/QQyrus/qyrion/releases/download/qyrion/v0.4.3-beta/qyrion-0.4.3-beta-macos-arm64.tar.gz) | `e1f7ce3527b6f373c8058e1e61160bdc32e0406ed23a32c0e6ae08e3e6766df1` |
| [qyrion-0.4.3-beta-windows-x64.exe](https://github.com/QQyrus/qyrion/releases/download/qyrion/v0.4.3-beta/qyrion-0.4.3-beta-windows-x64.exe) | `4a3aa834fd4b10d1a47dda141465fad56dce0a5b73017f74f89bf048eaede94b` |
| [qyrusai-1.0.9-py3-none-any.whl](https://files.pythonhosted.org/packages/1d/4e/99d948c255194994f3190e34bc194412d792962bb25052247ae168b4784f/qyrusai-1.0.9-py3-none-any.whl) | `4b716f7515d5994e938471b5bb27a02296885f8539a29def9301695cc25fb671` |

Use the available capabilities for the requested task. If a required capability is unavailable, tell the user which operation needs it. Continue with work that can be done in this session, such as drafting test scenarios and expected results. Keep credentials private and distinguish proposed tests from executed tests.
