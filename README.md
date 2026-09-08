# Qyrion Agent Plugin

A portable coding-agent plugin (Claude Code / Codex / Cursor) that lets a
coding agent test the app it is building on real cloud devices through the
[Qyrion CLI](../../apps/qyrion/README.md). Build the package locally; Qyrion
runs it on real devices; the agent reads the evidence.

The plugin is **CLI-only**: skills invoke the `qyrion` executable directly.
It ships no MCP configuration (decision 2026-07-11).

## Skills

| Skill | Owns |
|---|---|
| `qyrion-cli` | Direct session operations (start/stream/send/question/result/cancel), artifact download, and CLI troubleshooting |
| `qyrus-device-testing` | "Test my app on a real device": codebase discovery → ranked scenarios → plan gate → upload → sessions → evidence report |
| `qyrus-change-impact` | "What should I test for this diff/PR": change classification → mapping to saved tests → minimal run set → triage |
| `answer-qyrion-agent-questions` | Answering questions a running device session asks back (`clarification_requested`), with escalation rules |

Skills are independently executable: each carries its own copy of the shared
contracts under `references/`. The canonical sources live in `shared/` and
are embedded by `scripts/build-packages.sh` — edit `shared/*.md`, then re-run
the script; never edit the generated copies.

```text
plugins/qyrion-agent-plugin/
├── .claude-plugin/plugin.json      # Claude Code manifest
├── .codex-plugin/plugin.json       # Codex manifest
├── .cursor-plugin/plugin.json      # Cursor manifest (untested — see below)
├── skills/<skill>/SKILL.md         # 4 skills + references/
├── shared/                         # canonical single-source contracts
├── scripts/build-packages.sh       # embeds shared/ into each skill
├── tests/trigger-evals.md          # routing + safety eval cases
├── tests/fixtures/*.jsonl          # fake session streams for dry-runs
└── README.md
```

## Prerequisite: the Qyrion CLI

Skills locate the CLI via `QYRION_CLI` env override → `qyrion` on `PATH` →
pinned `npx @qqyrus/qyrion` (announced, never silent). Install and configure
it per the Qyrion getting-started guide:
[`apps/qyrion/docs/getting-started.md`](../../apps/qyrion/docs/getting-started.md)
— GitHub Release binaries, macOS `.pkg`, or npm/npx, then `qyrion configure`
with the three credentials (Application URL, API key, Gateway token). Every
workflow starts with a `qyrion capabilities --json` handshake and stops with
upgrade guidance if the CLI is too old.

## Install

### Claude Code

```bash
claude --plugin-dir /path/to/df-ai-session/plugins/qyrion-agent-plugin
```

After edits inside a running session: `/reload-plugins`. Skills are
namespaced, e.g. `/qyrion-agent-plugin:qyrus-device-testing`. Validate with:

```bash
claude plugin validate plugins/qyrion-agent-plugin --strict
```

### Codex

This repo ships a repo-local marketplace at `.agents/plugins/marketplace.json`
listing this plugin with a `local` source of `./plugins/qyrion-agent-plugin`
(path relative to the repository root). Add the marketplace, then install the
plugin from the desktop plugin directory. The installed copy is cached — after
changing plugin source, reinstall/refresh rather than expecting live reloads.

### Cursor

`.cursor-plugin/plugin.json` is provided but **untested** — Cursor has no
one-command local directory loader; validate with the official
`cursor/plugin-template` scripts and install through a private/test
marketplace. For quick iteration, copy individual skill folders to
`.cursor/skills/`.

## Development

```bash
./scripts/build-packages.sh   # re-embed shared/ into every skills/*/references/
```

Testing layers (see `tests/trigger-evals.md`):

1. **Trigger evals** — positive/negative/ambiguous prompts per skill with
   expected first action and a safety assertion.
2. **Fixture dry-runs** — `tests/fixtures/*.jsonl` are fake `--jsonl` streams
   (happy path, mid-run clarification question, blocked run, timeout) for
   replaying workflows against a stub CLI without spending device time.

Contracts embedded in the skills mirror upstream docs — if they drift, the
upstream files win and `shared/` must be refreshed:

- event vocabulary / park semantics / exit codes:
  [`apps/qyrion/docs/event-contract.md`](../../apps/qyrion/docs/event-contract.md)
- install + credentials:
  [`apps/qyrion/docs/getting-started.md`](../../apps/qyrion/docs/getting-started.md)

## Safety posture (summary)

Full policy in `shared/safety-policy.md`, embedded in every skill: three
credentials only and never echoed; no secrets/OTPs in session messages or
`qyrion.yml` (account aliases only); no production targets without explicit
confirmation; presigned artifact URLs treated as short-lived secrets
(download, never paste); destructive in-app actions require explicit user
approval; saved tests are never deleted (retirement is proposal-only); and
every task ends with a sweep that cancels leftover live sessions.
