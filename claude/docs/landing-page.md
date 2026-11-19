# Landing page maintenance

`index.html` is the QyrusAI Assure installation and usage page. It ships in
the plugin root so the public mirror publishes it at
<https://qqyrus.github.io/qyrion/>. `.nojekyll` keeps it a static site.

The page is plain HTML with inline CSS and JavaScript, native controls, and
Tailwind's CDN utilities. It uses Qyrus color tokens and the system font in
continuous full-width landing-page sections, with display-size headings. It
does not load the private Qyrus Web Components package or use the application
island layout. Light and dark themes share `qyrus-theme` in localStorage. The
page remains readable when the CDN is unavailable; clipboard failure selects
the prompt for manual copying. It does not accept or transmit API credentials.

## Content sources

Keep these sections aligned with the files they summarize:

- Value loop stages and the assurance loop recipes (A1-A7):
  `skills/qyrus-value-loops/SKILL.md` and its `references/loop-recipes.md`.
  The page covers the assurance loops only. The operations and modernization
  recipes are left out on purpose; do not add them.
- The nine skill cards: the `Skills` table in `README.md`.
- The hero run panel is an illustration and is labelled as one. Do not put
  real ticket ids, customer names, or measured results in it.

## Motion

All motion is decorative and the page works without it:

- Sections fade up on scroll (`data-reveal`, IntersectionObserver).
- The hero run panel types its request and completes its steps in a loop.
- The value-loop track lights each stage in turn (CSS keyframes).
- Cards lift on hover with a glow that follows the pointer.

With `prefers-reduced-motion: reduce` every animation and transition is off
and the hero panel shows its finished state. Without JavaScript all content
is visible. New content must stay readable in both of those cases.

## Local preview

From the plugin root:

```bash
python3 -m http.server 8766 --bind 127.0.0.1
```

Open <http://127.0.0.1:8766/index.html>. Check desktop and narrow mobile widths
in both themes, theme persistence, prompt copying, disclosure controls,
relative links, and video playback. The source HTML can also be opened as a
file; clipboard permissions vary by host, so the manual-copy fallback is
intentional. No build or package installation is required.

## Tutorial media

- `assets/qyrusai-logo.png`: the supplied QyrusAI brand asset.
- `assets/favicon.svg` and `assets/favicon-180.png`: the Qyrus mark used as
  the browser-tab and home-screen icon, copied from
  `apps/qyrus-df-desktop/resources/icon.svg` and `icon.png`.
- `assets/create-x-api-key.mp4`: 60 seconds, H.264, 1600×900, 30 fps, no audio,
  approximately 1.6 MB, with MP4 metadata placed first for playback.
- `assets/create-x-api-key-poster.jpg`: a safe frame showing token setup.

The original screen recording showed a real key inside the generated MCP
JSON even though the token input was masked. Only the redacted derivative
belongs in this package. In the 1920×1080 source, the derivative masks the
token field at `(558, 394, 860, 46)` and the entire MCP configuration box at
`(558, 549, 860, 244)` from 46.5 seconds to the end, before the result dialog
appears. Masking is applied before scaling and encoding; the source recording
is not included. The original tutorial selects broad permissions; the written
instructions tell viewers to grant the permissions their tasks need.

For a replacement recording, review the entire video and every transition
where credentials appear. Do not reuse the current rectangles or timestamps
without checking the new recording. Cover keys in inputs, JSON, downloads,
notifications, and clipboard previews; inspect the exported frames after
encoding. Strip source metadata, export H.264/yuv420p with `+faststart`, then
regenerate a safe poster. Keep the written instructions and duration label
aligned with the recording. Do not add raw recordings or unredacted frames.

## Publication

The private release mirror copies this directory to the public repository,
including the page, logo, favicons, tutorial, poster, and `.nojekyll`. It configures
GitHub Pages from the root of `master`, then verifies a successful build of
the mirrored commit and the exact HTML served at the public URL. Source sync
or a queued build alone is not verified publication. A feature-branch push
does not publish the site; the release must include these assets.
