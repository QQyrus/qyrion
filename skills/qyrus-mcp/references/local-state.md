# Reusable local records

Scope: remember the resources created or verified during a Qyrus task without
copying its secrets or transcript. This is a lookup aid, not permission to
rerun, modify, or delete anything. Resolve scripts from the installed plugin
root; do not assume the user's working directory is the plugin directory.

## Read before reuse, record after read-back

Use `scripts/qyrus_state.py` with the same private-file selection as
`qyrus_env.py`. The helper creates a `qyrusai-assure/` subfolder beside that
file, outside the plugin cache and repository. By default this is
`~/.config/qyrus/qyrusai-assure/`. A custom credentials path moves the record
store with it; do not silently search other environments' stores.

```bash
python3 scripts/qyrus_state.py path
python3 scripts/qyrus_state.py list --target-origin https://test.example.com
python3 scripts/qyrus_state.py record --kind test --id <returned-test-id> \
  --project-id <returned-project-id> --session-id <returned-session-id> \
  --platform web --target-origin https://test.example.com \
  --source-issue MON-65 --status created --verified
```

Replace angle-bracket IDs with values actually returned by Qyrus. Use
`--env-file /absolute/path/credentials.env` when explicitly selecting a file,
and `--team <verified-team-id>` when the file has no selected team. The helper
does not require printing the credentials file or placing its key in arguments.
Use `--help` for exact flags. These commands are local; `--verified` records
the caller's preceding live read-back, not a verification performed by the helper.

- Scope is normalized Qyrus application URL + exact team + optional target
  origin. The tested website is distinct from the Qyrus tenant URL. An origin
  has no path, query, fragment, or user information. For mobile/API records
  without a useful target origin, omit it consistently. An omitted origin
  queries only that bucket; it never searches every target automatically.
- At task start, look up relevant records when resuming or reusing coverage.
  Re-read the resource through the live CLI/MCP and confirm scope, current
  revision, and authorization. Missing, archived, or inaccessible IDs are
  stale references, not permission to guess replacement IDs or claim a pass.
- After a create/update/run and its read-back, record the returned IDs and
  status, then add another observation when terminal results are verified.
  Keep source issue IDs and relationships where available. Parallel workers
  write independent observations; the parent aggregates without inventing IDs.
- `--verified` means resource read-back. `--outcome passed` is appropriate only
  when terminal execution and assertion evidence support it. Created/saved,
  completed, and passed are different facts; default outcome is unverified.
- The helper accepts only defined record kinds, IDs, enums, and scope fields.
  Do not store objectives, titles, usernames, passwords, API keys, auth headers,
  raw responses, screenshot pixels, signed URLs, or arbitrary notes. Identifier
  syntax cannot detect every secret; copy only the relevant returned ID fields.

## Host memory and retention

When the current host offers a permitted memory facility, remember a compact
pointer to this record directory plus non-secret environment/team/target and
useful resource IDs. A suggested entry is: “Qyrus records: <absolute path>;
read the matching scope and revalidate IDs before reuse.” Honor host-specific
memory permissions. If unavailable, the local store is sufficient; do not
claim that the host has remembered anything or invent a memory API.

Do not turn a one-task choice into a permanent execution preference. Reuse
preferences stated in the current conversation; persist a durable preference
only when the user asks and the host supports it. A stored result is never a
standing instruction or authorization for a future external write.

Records are local immutable JSON observations with timestamps, under hashed
scope directories. Independent atomic writes prevent concurrent sessions from
overwriting each other. POSIX directories/files use 0700/0600; Windows access
control is inherited from the user's private directory. There is no cloud sync
or automatic expiry. Users may remove selected record files or the `records/`
subdirectory to forget local history, without deleting Qyrus tests or the
credentials file. Preserve `updates.json` unless resetting update history is
also intended. Never commit this store.
