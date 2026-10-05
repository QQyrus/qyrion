# Qyrion CLI troubleshooting

Failure signatures and remediations. Always reproduce with `--json`/`--jsonl`
so you get a structured `{"error": {code, message, retryable, remediation}}`
instead of prose.

## Exit 3 — authentication / authorization failure

Identify the failing endpoint before changing credentials. Updated Qyrion
`auth teams` uses TestHub `/api/cli/auth/teams`; older binaries call gateway
`/usermgmt/v2/api/team-list` directly and can return 401 while MCP succeeds.
Use MCP discovery for plugin setup; do not rotate a working key or add a
gateway token merely because the older discovery route fails.
For a relevant Qyrion service call, check:

1. **Application URL** (`QYRION_APP_URL` or profile): must be the exact Qyrus
   URL the user logs in to (e.g. `https://app.qyrus.com`). A wrong URL can
   also masquerade as 404s.
2. **API key** (`QYRION_API_KEY`): confirm it belongs to the selected tenant
   and has access to the failing service; MCP success is not proof of that.
3. In CI, `QYRION_TEAM_ID` must be a team the credentials can access — get it
   through MCP team discovery and preserve the returned UUID exactly.

Remediation: the user re-runs `qyrion configure` in their own terminal
(interactive wizard — the agent must not drive it) or updates the shared private env file via `qyrus-setup`.
Current Qyrion never sends its legacy Authorization input, so adding a token
does not change the team-list request. Verify the selected Qyrion scope with
helper-wrapped `qyrion sessions list --json`; re-select the team if needed
(`qyrion auth use-team <team-id>`; multiple teams → ask the user which one).
Full flow: cli-contract.md § "Authentication, profiles, and first-run
setup". Never ask the user to paste credential values into the chat.

## Team-scoped calls fail after auth succeeds

MCP team discovery works but sessions/apps/devices calls fail or land in the
wrong workspace: check the selected team and service authorization. Discover
teams with MCP, confirm the intended UUID, then `qyrion auth use-team <team-id>` (or set
`QYRION_TEAM_ID` in CI). Check `--profile` too — a command run with a
different profile than the one configured uses different stored credentials
and team.

## Exit 4 / HTTP 404

Check the response source before deciding that a route is missing. Updated
Qyrion uses `backend_route_missing` only for an explicit gateway route miss;
resource or unspecified 404s are `not_found`. Older builds label every
artifact 404 `backend_route_missing`, which is not reliable evidence.

Use the canonical `artifact_id` from `sessions artifacts`. Updated Qyrion
encodes colons in that ID for the gateway and supports short event IDs after
an explicit unknown-artifact response. A listing that succeeds while the
canonical download returns 404 can indicate an older client failing to encode
`:`. Follow the bundled prerequisite runbook to refresh the client, then
repeat the read-only check.

## HTTP 422 on saved-test replay

Inspect `tests get` for curated replayable steps and execution inputs. A
newly created test with zero steps cannot be replayed merely by supplying a
start URL. Updated machine output reports `invalid_usage` (exit 2); arbitrary
server text and input values are not echoed.

## HTTP 5xx on session creation or replay

A run may already have been persisted before browser/runtime startup failed.
Check `sessions list/result` before repeating the creation; do not blindly
retry or report a run as never created based on the HTTP status alone.

## Exit 4 — other backend availability failures

Transient service/gateway failures. If the structured error says
`"retryable": true`, retry once with backoff. If it persists, report the
error `code` and `message` to the user and stop; do not hammer the backend.

## `capabilities` command not found (exit 2 / unknown command)

The installed CLI predates this plugin's contract. Use `prerequisites.md` to
upgrade through its existing trusted source and repeat the handshake once.
Preserve profiles and explicit overrides. If still incompatible, report the
missing capability; do not attempt the workflow against an old CLI.

## npx fallback fails to download / 401 from npm

`@qqyrus/qyrion` is served from a private npm registry. Prefer the verified
public binary installation in `prerequisites.md` when no npm source was
explicitly required. If the user selected npm, use existing registry access
or ask them to authenticate through its normal secure flow; never request
token values in chat or silently replace an explicitly selected source.

## Run stuck before any device action (`PENDING_CONCURRENCY`)

The run is waiting for a device slot — capacity, not failure. Wait (the
stream stays open), and do not start additional sessions while one is
pending. If it exceeds the task's time budget, cancel and tell the user the
device pool is saturated.

## Stream dropped / SIGINT

The run keeps going server-side. Re-attach:

```bash
qyrion sessions stream <run_id> --jsonl --until input-required --max-seconds 900
```

With the `stream_cursor` capability, pass `--after-sequence <last-seen>` to
replay the gap without duplicates. The CLI also prints a resume command to
stderr on SIGINT.

## `--jsonl` output will not parse

Machine data is stdout-only; human/Rich output goes to stderr. Make sure you
are not merging the two streams (`2>/dev/null` when piping). If a line still
fails to parse, skip it and continue — unknown frames must be ignored, not
fatal.

## Orphaned sessions after a failed task

```bash
qyrion sessions list --json
qyrion sessions cancel <run_id>   # for each running/waiting_user_input run you started
```

Cancellation is idempotent. Report anything you could not cancel.
