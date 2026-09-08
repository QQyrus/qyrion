# Qyrion CLI troubleshooting

Failure signatures and remediations. Always reproduce with `--json`/`--jsonl`
so you get a structured `{"error": {code, message, retryable, remediation}}`
instead of prose.

## Exit 3 — authentication / authorization failure

The three credentials are wrong, expired, or incomplete. Check in order:

1. **Application URL** (`QYRION_APP_URL` or profile): must be the exact Qyrus
   URL the user logs in to (e.g. `https://app.qyrus.com`). A wrong URL can
   also masquerade as 404s.
2. **API key** (`QYRION_API_KEY`): expired or revoked keys return auth
   failures on every call.
3. **Gateway token** (`QYRION_AUTHORIZATION`): raw token and
   `Bearer <token>` both work; anything else does not.
4. In CI, `QYRION_TEAM_ID` must be a team the credentials can access — get it
   once via `qyrion auth teams` on a configured machine.

Remediation: the user re-runs `qyrion configure` in their own terminal
(interactive wizard — the agent must not drive it) or fixes the env vars.
Verify with the probe `qyrion auth teams --json`, then re-select the team if
needed (`qyrion auth use-team <team-id>`; multiple teams → ask the user which
one). Full flow: cli-contract.md § "Authentication, profiles, and first-run
setup". Never ask the user to paste credential values into the chat.

## Team-scoped calls fail after auth succeeds

`auth teams --json` works but sessions/apps/devices calls fail or land in the
wrong workspace: no team (or the wrong team) is selected. List teams, confirm
the intended one with the user, then `qyrion auth use-team <team-id>` (or set
`QYRION_TEAM_ID` in CI). Check `--profile` too — a command run with a
different profile than the one configured uses different stored credentials
and team.

## Exit 4 / HTTP 404 with code `backend_route_missing`

The CLI is newer than the backend it is talking to: the route the command
needs is not deployed in that environment yet. This is not a CLI bug and not
an auth problem.

- Tell the user which command hit it and that the backend feature is not
  deployed for their environment.
- Cross-check `qyrion capabilities --json` — if the corresponding feature
  flag is `false`, treat the feature as unavailable and degrade (e.g. skip
  screenshot downloads) instead of retrying.

## Exit 4 — other backend availability failures

Transient service/gateway failures. If the structured error says
`"retryable": true`, retry once with backoff. If it persists, report the
error `code` and `message` to the user and stop; do not hammer the backend.

## `capabilities` command not found (exit 2 / unknown command)

The installed CLI predates this plugin's contract. Stop and point the user at
the install guide (`apps/qyrion/docs/getting-started.md`: GitHub Releases
binaries, macOS `.pkg`, or `npx @qqyrus/qyrion`). Do not attempt the workflow
against an old CLI.

## npx fallback fails to download / 401 from npm

`@qqyrus/qyrion` is served from a private npm registry. The user needs the
one-time `~/.npmrc` scope setup described in the getting-started guide, and
(while the repo is private) a `QYRION_GITHUB_TOKEN`/`GH_TOKEN` with package
read access. This is user setup — do not create or request tokens yourself.

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
