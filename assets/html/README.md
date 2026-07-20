# Base HTML template — App Store screenshots

This directory is the skill's **shipped base template**. At runtime the skill
copies and adapts these files into the user's project as `screenshots/design/`,
then renders each page to a PNG with [agent-browser](https://github.com/vercel-labs/agent-browser)
(headless Chromium). Deterministic pixels, `$0` per render.

## Files

| File | Role |
|---|---|
| `base.css` | The design system: reset, canvas sizing, type scale, CSS-drawn device frame, and the breakout crop pattern — all behind CSS custom properties. Copied to `screenshots/design/set.css` and adapted per app. |
| `ready.js` | The shared **fail-closed readiness gate** (one copy — pages load it via `<script src="ready.js">`). Vendored next to `set.css` at runtime; never inlined or edited per shot. |
| `iphone.html` | Example iPhone page (1290×2796). Copy per shot; edit only the marked slots. |
| `ipad.html` | Example iPad page (2064×2752). Same structure, `body.ipad` + iPad viewport. |
| `placeholder-screen-iphone.png` / `placeholder-screen-ipad.png` | Demo simulator raws so the pages render standalone. **Replace** with the captured app screenshot at runtime. |

Fonts live one level up in `../fonts/` (bundled Inter, SIL OFL).

## How a page is built (the slots)

Each page is a tiny, fixed skeleton. Only three things change per shot:

1. **Headline** — `<div class="verb">` + `<div class="desc">`. Text only.
   Never set a font-size here (see the type-scale rule below).
2. **Screenshot** — `<img class="screen" src="…">`. Point at the raw simulator
   PNG for this shot.
3. **Breakout** (optional) — `<div class="breakout" style="--crop-…">` wrapping
   an `<img>` of the *same* raw. It nests **inside `.device`** (right after
   `<img class="screen">`) so it can position against the device frame.
   (Opt-in genai hero variant: the wrapped image is a generated piece with its
   own src and `class="piece"` — the `img.piece` rule fills the card window via
   `object-fit: cover` instead of the raw-offset math; the crop vars still
   drive the window's size and placement. See `references/genai-pieces.md`.) It is a
   *magnified copy* of a panel that must **fully cover (occlude) its source** —
   never sit beside the still-visible original (that reads as duplication).
   Placement is **automatic**: the card centres itself over the exact spot its
   crop occupies on screen (derived from the `--crop-*` vars + `--screen-scale`),
   so do not hand-place it — nudge only with `--shift-x`/`--shift-y`. Because
   placement is derived, only break out a panel that is **fully visible on the
   canvas** (the device bleeds off the canvas bottom — see the containment
   invariant below). **Measure**
   the crop against the raw's real pixels and inset it 8-12px inside the panel's
   true bounds (any page background left in the crop shows as a stripe inside the
   card); the mandatory 1:1 QA of the render catches a bad crop (optionally
   pre-verify the crop rect at 1:1 when the measurement was tricky). If the
   panel is near-full-screen-width, crop a tight **sub-block** and magnify
   that. Delete the block when a clean shot reads better.

Everything else — frame geometry, colours, sizes, shadows — lives in the
stylesheet behind custom properties.

## Key custom properties (set in `base.css`)

**Brand / type** (override per app): `--bg`, `--fg`, `--verb-size`,
`--desc-size`, `--verb-tracking`, `--desc-tracking`, `--headline-side-pad`.

**Frame** (per-device blocks `body.iphone` / `body.ipad`): `--device-w`,
`--bezel`, `--bezel-color`, `--frame-radius`, `--screen-radius`,
`--island-w`/`--island-h`/`--island-top` (Dynamic Island on iPhone, a small
camera dot on iPad), `--frame-shadow`.

**Breakout** (set inline per shot, all in *raw screenshot pixels* except
`--zoom`, the display scale): `--crop-x`, `--crop-y`, `--crop-w`, `--crop-h`,
`--zoom`, and the placement nudges `--shift-x`/`--shift-y` (default `0px`).
`--screen-scale` (per-device, in `base.css` — read the shipped value from the
`body.iphone` / `body.ipad` block rather than copying it into prose) is the
ratio of on-canvas screen px to raw px, and it is **the device-size knob**:
`--device-w` is derived from it (`--raw-w * --screen-scale + 2*--bezel`, in the
shared `body` rule), so resizing the device cannot desync breakout placement.
Tune `--screen-scale`, never `--device-w`. Card styling: `--breakout-radius`,
`--breakout-shadow`, `--breakout-border`. There is **no** `--breakout-top`/`-left`
— placement is auto-occluding.

## Invariants (enforced by `base.css`)

- **Exact canvas size** — iPhone 1290×2796, iPad 2064×2752. The QA loop verifies
  with `sips -g pixelWidth -g pixelHeight`.
- **Uniform type scale** — `--verb-size` / `--desc-size` are set once and apply
  to every shot in the set. If a headline overflows, adjust the set-wide scale
  or reword — never add a per-shot size override.
- **Headline edge margin** — `--headline-side-pad` (default 7%) keeps text
  ≥ ~6% off every canvas edge.
- **Breakout auto-occlusion + measured crops + containment + 1:1 QA** — a
  breakout is a magnified copy that covers its source (a full-panel card
  occludes the whole panel; a sub-block card covers its own crop's footprint —
  the rest of the panel is context, not duplication). Placement is **derived**
  from the crop vars + `--screen-scale` (never eyeballed); `--shift-x`/`--shift-y`
  are the only manual nudges. Crops are **measured** against the raw's real
  pixels and inset 8-12px inside the panel's true bounds. The card reads
  `--zoom ÷ --screen-scale` bigger than its on-screen original — reach for a
  **≥ ~1.5× read** (`--zoom ≥ ~1.2`), usually via a tight sub-block crop;
  softness is the ceiling, judged in the mandatory 1:1 QA read. Only
  fully-on-canvas panels are eligible (the device bleeds off the canvas
  bottom by design). The coverage/shift formulas, the card-box containment
  computation, the panel-eligibility ladder, and the 1:1 QA recipe are
  **canonical in SKILL.md's Breakout flow** (the `.breakout` comment in
  `base.css` documents the placement geometry the CSS implements).

## Render sequence (strictly sequential, one agent-browser session)

```bash
agent-browser set viewport 1290 2796          # 2064 2752 for iPad
agent-browser open "file://$PWD/01-<slug>.html"
agent-browser wait "body.ready"               # fonts loaded + images decoded
agent-browser screenshot 01-<slug>.png
# … next shot: open → wait → screenshot …
agent-browser close                            # once the batch is done
```

`body.ready` is added by the shared `ready.js` each page loads via
`<script src="ready.js">` (one vendored copy next to `set.css`; do not inline
or edit it per shot). Readiness is **fail-closed**: it adds `ready` only when
`document.fonts.ready` resolved, every `<img>` decoded (`complete` +
`naturalWidth > 0`), every copy of the raw matches the `--raw-w` contract
(`img.screen` plus a same-src breakout `<img>`; a genai piece with its own src
is exempt),
the headline font face actually loaded (checked against the `.verb` element's
computed family, so a swapped CJK face is verified too — and a CJK headline
still resolving to the Latin face fails), the stylesheet applied (`--canvas-w`
non-empty), the body background resolved to a real colour (a malformed `--bg`
would silently render transparent), and the headline fits its box (no
`overflow:hidden` clipping). If any check fails it adds `body.render-error` and
writes a semicolon-joined cause to `data-render-error` instead — so a broken
asset never passes the gate silently. Read the cause with agent-browser's JS
evaluation when a page stalls without `body.ready`. Additionally, `base.css`
paints a full-canvas magenta **NOT-READY banner** until `body.ready` exists, so
even a capture that skipped the wait (the timer-based fallback renderer) shows
an unmissable failure instead of a plausible-looking page.

## Runtime adaptation notes

- **`base.css` → `set.css`.** The skill copies `base.css` into
  `screenshots/design/set.css` and tunes the brand/frame tokens for the app.
  Pages `<link>` `set.css` instead of `base.css`. `ready.js` is copied
  alongside it (same directory as `set.css`) so the pages' relative
  `<script src="ready.js">` resolves; locale pages one directory deeper use
  `../ready.js`, mirroring their `../set.css` link.
- **Fonts are vendored.** `@font-face` here uses the relative url
  `../fonts/InterDisplay-Black.otf` (resolves inside the skill dir). At runtime
  Inter is copied into `screenshots/design/assets/` and the url is rewritten to
  point there, so final renders load **zero** external resources. CJK locales
  (`lang="ja"` / `"ko"` / `"zh-Hans"`) additionally vendor a heavy CJK webfont
  (e.g. Noto Sans JP/KR/SC Black) as extra `@font-face` blocks.
- **Placeholder raws are replaced** with the real captured simulator PNGs; the
  `src` on both the `.screen` image and any `.breakout` image points at the same
  raw for a shot.
- **Localized pages** set `<html lang="…">` and re-render into
  `screenshots/final/<locale>/`.

## Developer smoke test

Render both example pages, confirm dimensions, eyeball the result:

```bash
agent-browser set viewport 1290 2796
agent-browser open "file://$PWD/iphone.html"
agent-browser wait "body.ready"
agent-browser screenshot /tmp/iphone.png
agent-browser set viewport 2064 2752
agent-browser open "file://$PWD/ipad.html"
agent-browser wait "body.ready"
agent-browser screenshot /tmp/ipad.png
agent-browser close
sips -g pixelWidth -g pixelHeight /tmp/iphone.png /tmp/ipad.png
```
