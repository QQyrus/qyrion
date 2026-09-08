# qyrion.yml — optional repo project mapping

A repo-local, optional file at the repository root that gives Qyrion
workflows stable project facts. When present, prefer it over re-deriving the
same facts; when absent, proceed and note that no mapping exists.

## Shape

```yaml
# qyrion.yml — Qyrus device-testing project mapping (no secrets, ever)
app:
  name: "Acme Shopping"          # project_app naming convention
  platform: android               # android | ios
  build_output: app/build/outputs/apk/release/   # where builds land (hint)

project_id: project_123           # Qyrus project for saved tests (optional)

devices:
  preferred:
    - device_ref: dfdev_pixel8    # first choice
    - device_ref: dfdev_galaxy24  # fallback

accounts:
  # ALIASES ONLY. The device platform resolves aliases to real credentials
  # server-side. Passwords/OTPs/keys never belong in this file.
  - alias: smoke-user-1
    purpose: default logged-in journeys
  - alias: fresh-user
    purpose: onboarding/signup flows

journeys:
  # path → journey hints for scenario discovery and change-impact mapping
  - paths: ["app/src/**/checkout/**"]
    journey: checkout
    tags: [critical]
  - paths: ["app/src/**/auth/**", "app/src/**/login/**"]
    journey: login
    tags: [critical, smoke]
  - paths: ["app/src/**/settings/**"]
    journey: settings
```

## Rules

- **Never secrets.** Account entries are aliases plus purpose only. If a
  credential-looking value appears in this file, refuse to use it and tell
  the user to rotate it.
- Values are hints, not law: verify `build_output` and `project_id` against
  reality (`qyrion apps list --json`, `qyrion tests list --json`) before
  relying on them.
- `journeys[].paths` power diff→journey mapping (used by change-impact) and
  discovery focus (used by device-testing). Globs are matched against repo
  relative paths.
- When creating this file for a user, propose it in the report; do not write
  it without being asked.
