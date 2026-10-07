# Quiet Qyrion update checks

Scope: checking the public CLI release during plugin activity and installing
an accepted update. The plugin does not wake itself or run a background timer.
This updates Qyrion binaries; refreshing the plugin and its skills remains a
separate host installation/update operation.

## Check at task entry

Once a private-file path and an existing CLI are available, run the helper
at the start of a Qyrus task. Resolve it from the installed plugin root:

```bash
python3 scripts/qyrus_updates.py check
```

Reuse the selected/default credentials path, or pass `--env-file <path>`.
The helper uses that path to locate private state; public GitHub requests
never include Qyrus credentials. It executes `qyrion version --json` to inspect
the installed version. A verified `--cli <path>` or inherited `QYRION_CLI`
selects a custom executable. `--current-version` supports a caller's already
verified version for a check only; it cannot establish successful installation.

The default cache interval is **four hours**. `updates.json` beside the
records directory stores `last_checked_at`, `last_successful_check_at`,
installed/latest versions, offered/declined versions, the offered release and
asset, and `last_updated_at`.
The latter is set only after installed-version verification. A failed check
does not imply the installed CLI is current. Cached failures are retried after
the interval; an explicit user request to retry/check now may use `--force`.
Concurrent callers share a short lock; a busy check must not block the task.

The newest published `qyrion/v*` release is selected by publication time,
including betas and excluding drafts. Discovery follows the public release
list within a bounded budget; incomplete traversal is reported as unavailable.
Asset selection uses the returned official release assets for the current
OS/architecture, without checksum downloads. No matching asset means a
platform/source-install decision, not permission to guess a download URL.

## Offer once, keep working, update after acceptance

When `notify` is false, do not add routine “checked for updates” chatter.
If a check is unavailable, continue with a working CLI; mention it only when
the user asked about updates or it blocks required compatibility. Never
misreport an unavailable check as “up to date.”

When an offer is due, ask briefly: **“A Qyrion update is available
(<version>, beta if applicable). Install it?”** Continue independent work
while awaiting a response. Record `offered` only after displaying that offer:

```bash
python3 scripts/qyrus_updates.py offered --version <offered-version>
python3 scripts/qyrus_updates.py decline --version <declined-version>
```

Keep a pending offer bound to its version/asset; do not overwrite it with a
new offer before resolving the user's outstanding choice. Release checks may
refresh `latest` while the saved `offered_release` remains available.
Record a decline only for an actual user decline. Silence, a timeout, and a
cached release are not acceptance. Offered/declined releases stay quiet on
ordinary subsequent checks; a newer version can produce a new offer.
Explicit user requests to update count as acceptance; do not ask twice.

For known source/editable/pinned installations use the matching
`--install-kind` so the result preserves the installation. An explicit CLI
override is also protected. If provenance is unknown, inspect the resolved
executable/install metadata before choosing an update path. A source package
version differing from a release version does not prove a broken install.
Do not convert a development checkout, pinned installation, or unrelated
executable to a public binary without the user's explicit choice.

After acceptance, follow `prerequisites.md`'s verified-source installation
steps. Use the cached official release/asset for the accepted version;
do not silently install a newer release that appeared after the offer.
Keep current sessions running on their current executable; finish or wait
before replacing a binary, especially on Windows. Preserve credentials,
profiles, PATH entries, and a recoverable previous binary until validation.
Then run the actual installed `qyrion version --json` and helper-wrapped
`capabilities --json`, and confirm the required features before recording:

```bash
python3 scripts/qyrus_updates.py record-installed --version <accepted-version>
```

Pass `--cli <installed-path>` if it is not the normal executable. The command
requires the actual executable version to match the checked or preserved
offered release, even if a subsequent check found a newer version;
it does not download or install anything. If validation fails, retain/recover
the working prior installation and report the actual failure; do not write a
successful installation timestamp or request a new API key as a workaround.

Check and installation state is private and atomic. A crashed process may
leave `.updates.lock`; do not automatically steal a possibly active lock.
Confirm no updater is running before removing that stale lock and retrying.
No helper command grants consent or bypasses host installation policy.
