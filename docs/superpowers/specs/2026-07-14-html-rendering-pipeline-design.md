# HTML-First Rendering Pipeline — Design

**Date:** 2026-07-14
**Status:** Historical design record — frozen at the reviewed design
**Replaces:** the Pillow-scaffold → full-canvas Nano Banana enhance pipeline

> **This document is a point-in-time record, not living doctrine.** The
> implementation has since evolved (e.g. the breakout scale rule now targets a
> magnified ≥ ~1.5× *read* rather than "never above ~1.0×", and the readiness
> gate grew from fonts+decode into a broader fail-closed check set in a shared
> `ready.js`). Where this document and SKILL.md / CLAUDE.md disagree, those
> files are canonical.

## Problem

The current pipeline sends the entire canvas through a generative image model
(Nano Banana Pro via `enhance.py`) for every screenshot. That causes:

1. **Cost and latency.** Baseline 3 + 1×(N−1) paid calls per set, N×M more for
   localization (~$50+ for a full locale run), 30–60s per call plus retries.
   Experimentation is expensive by construction.
2. **Full-canvas repaint artifacts.** Smears, blurred edges, mushy in-screen UI
   text. The iPad frame (long, thin bezels) is re-hallucinated with visible
   artifacts on nearly every run. Quality tops out around 6/10.
3. **Derived complexity.** Text-garbling self-checks, the 9:16→0.461 crop
   dance, the horizontal safe-area rule, style-template bookkeeping, the
   "never switch backends mid-set" rule — all exist to fight model drift.

## Core idea

**The LLM decides *what* and *where*; deterministic code renders the pixels.**

Claude authors per-app HTML/CSS (design judgment), a headless browser renders
it at exact App Store dimensions (pixel fidelity), and the generative image
model is demoted to an opt-in tool for isolated pieces it is uniquely good at.
An element can only smear if genai painted it — so almost nothing can smear.

## Architecture

### Rendering backend: agent-browser

Renders are produced by the [agent-browser](https://github.com/vercel-labs/agent-browser)
CLI (headless Chromium via CDP):

```bash
agent-browser set viewport 1290 2796        # or 2064 2752 for iPad
agent-browser open "file://$PWD/screenshots/design/01-track-card-prices.html"
agent-browser screenshot screenshots/final/01-track-card-prices.png
agent-browser close
```

- Output is natively the exact App Store Connect size. **The happy path has
  no crop or resize step at all** (the QA loop still *verifies* dimensions
  with `sips -g`). Exception: `set viewport W H 2` (retina scale) may be
  used if extra anti-aliasing quality is ever wanted — that explicitly
  reintroduces one downscale step.
- Verified working end-to-end (spike, 2026-07-14): exact 1290×2796, crisp
  text, clean frame edges, CSS breakout with drop shadow, ~2s, $0. (The spike
  page that seeded the base template has since been deleted — it demonstrated
  the retired hand-placed breakout; the shipped `assets/html/` templates are
  the living version.)
- **Render readiness is explicit, not assumed.** Local fonts and images
  still load asynchronously relative to first paint. The base template
  includes a small script that adds `class="ready"` to `<body>` once
  `document.fonts.ready` has resolved and every `<img>` has `decode()`d;
  the pipeline runs `agent-browser wait "body.ready"` before every
  screenshot. Vendored assets shrink the load window, but the wait is the
  guarantee.
- **Renders are sequential.** agent-browser is a stateful session (global
  viewport, one active page). Design directions, shots, and iPhone/iPad
  interleaving render one after another (~2s each); do not parallelize
  within one session.

**Prerequisites check** — cheap existence check up front, full verification
at point of use:

- At the start of the generation phase, run `command -v agent-browser`
  (~free). If missing, show `npm install -g agent-browser` and stop before
  any design work.
- **No standing smoke render.** `command -v` doesn't verify the Chromium
  download (fetched on first run; can fail on restricted networks), but the
  *first real render* verifies that for free — the QA loop already checks
  dimensions and Reads every output, so a broken backend cannot slip
  through. Unlike the gemini-key pre-flight this replaces, there is nothing
  expensive downstream to protect: if the first render fails, the design
  files persist, we surface agent-browser's own error output (which names
  the remedy) and stop; the user fixes the install and we re-render at zero
  cost.
- The gemini/codex image backends become *optional* prerequisites, needed
  only when an opt-in genai piece is actually requested.

### Per-app design authoring

For each set, Claude writes design files into the user's project:

```
screenshots/design/
  set.css                     ← the set's design system: colours, type scale,
                                 frame include, accent style (shared by all shots)
  01-<benefit-slug>.html      ← one page per shot: headline + raw PNG + breakout
  02-<benefit-slug>.html
  assets/                     ← vendored: fonts, icon SVGs, anything external
```

- Claude designs by looking at the simulator screenshots, brand colour, and
  benefits — layout, device position, accent shapes are *per-app decisions
  expressed in code*, not a frozen template. Design variance where wanted,
  render variance nowhere.
- The skill ships a high-quality **base template** (`assets/html/` in the
  skill directory: iPhone page, iPad page, frame CSS, readiness script,
  reset CSS) so the
  design floor is high; Claude customizes from there rather than from blank.
- Design files live in the user's repo → diffable, re-renderable, reusable.

### Typography and fonts

- Bundled Inter loaded via `@font-face` (file:// URL into the skill dir).
- Other typefaces allowed when the brand calls for it — downloaded into
  `screenshots/design/assets/` at design time (see CSS-library policy).
- **Headline sizing is owned by `set.css`, not per-shot files.** The type
  scale (verb size, descriptor size, wrap/padding rules) is defined once as
  custom properties — this is how the format spec's "same size on every
  screenshot" invariant survives per-shot HTML. If one headline overflows
  (long German descriptors will), the fix is a set-wide scale adjustment or
  a wording/wrap change — never a silent per-shot size override.
- **CJK is vendored, not left to system fallback.** An unqualified fallback
  can resolve to a mid-weight face (violating the heavy/black headline
  requirement), and without a `lang` attribute Chromium can render Japanese
  kanji with Chinese glyph forms (Han unification). So: every locale page
  sets `<html lang="ja">` / `lang="zh-Hans"` / etc., and localized sets
  vendor a matching heavy CJK webfont at design time (e.g. Noto Sans
  JP/KR/SC Black) per the vendoring policy. This also mitigates the
  cross-platform font-rendering risk below. The `.ttc`-scanning machinery
  in `compose_common.py` (`font_for`, `contains_cjk`, per-char wrapping) is
  still retired.

### Device frame: CSS-drawn, centralized in `set.css`

Plain HTML has no include mechanism on `file://` (and `fetch()` is blocked),
so "SVG partials" would mean N diverging copies of frame markup per set — a
bezel tweak would touch every page. Instead:

- The frame **markup** is a tiny fixed snippet in each page
  (`<div class="device"><img class="screen" src="…"></div>`), written once
  per shot and never edited afterwards.
- All frame **geometry and styling** — bezel width/colour, corner radii,
  Dynamic Island / camera dot (pseudo-elements), shadow — live in `set.css`
  behind CSS custom properties, so a frame tweak is a one-file edit shared
  by every shot. The spike drew its frame this way.
- If a detail ever genuinely needs SVG, it is vendored as a static asset
  and referenced via `<img>`/`background-image`; static detail needs no
  CSS-variable parametrization, so the external-SVG limitation doesn't bite.
- Retired: `generate_frame.py`, `generate_frame_ipad.py`,
  `assets/device_frame.png`, `assets/device_frame_ipad.png` (replaced by
  frame rules in the shipped base `set.css`).

### Breakout elements: vision-picked, deterministically cropped

1. Claude Reads the simulator screenshot and picks the UI panel that
   reinforces the headline (or none — "clean beats forced" rule unchanged).
2. The panel is cropped from the **real screenshot pixels** (CSS crop of the
   same `<img>`: container with `overflow:hidden`, offset/scaled image) and
   styled with `border-radius`, scale-up, drop shadow.
3. Claude renders, Reads the result, and nudges the crop box if it's off —
   free iteration until aligned.

**Scale invariant:** a crop is never displayed above ~1.0× its native pixel
size in the raw. Raws are native resolution and the in-frame device is
downscaled, so typical breakout zooms sit well under 1.0× — but enlarging a
small crop past its native pixels would be visibly soft, so the QA loop
checks this explicitly. Within that invariant, panel text stays
capture-sharp — the exact thing the repaint used to smear.

### Secondary decorations

Vanilla CSS shapes/gradients plus vendored MIT-licensed icon SVGs
(Lucide/Heroicons). This replaces most genai-invented decorative elements
deterministically. Restraint rules from the current spec carry over.

### CSS-library policy

- **No framework** (no Tailwind/Bootstrap): single-poster pages, one author;
  vanilla CSS is fully expressive and adds no reproducibility risk.
- **Pluggable assets allowed — vendored and pinned.** Fonts and icon sets may
  be fetched at design time but MUST be downloaded into
  `screenshots/design/assets/` before the final render. Final renders load
  zero external resources. Rationale: (1) re-renders months later (new
  locale, tweaked headline) aren't perturbed by CDN version drift or URL
  rot — note the honest limit: Chromium version bumps can still shift
  antialiasing/kerning, so re-renders are *structurally* identical, not
  byte-identical (when extending a set much later, re-render the whole set
  in one sitting so it stays internally uniform — it's free); (2) a much
  smaller font-load window — though the `body.ready` wait is the actual
  guarantee against capturing a fallback font; (3) a deterministic pipeline
  step never flakes on CDN outages.

### genai: opt-in, per-piece, never full-canvas

`enhance.py` and both backends (gemini/codex) are kept, with a narrowed role:

- Irregular extractions a rectangular crop can't handle (non-rect panels,
  content bleeding behind an element).
- Invented decorative pieces the user explicitly wants.
- Generated **in isolation** (flat known-colour background), then composited
  into the HTML page as an `<img>` layer. An artifact is one small rejectable
  element, not a poisoned canvas.
- **Compositing requires an explicit cutout step** — image models output
  opaque rectangles and won't reproduce the brand hex exactly, so a raw
  paste would show as a visible plate. Two supported paths: (a) frame the
  piece intentionally — display it inside a visible rounded card with a
  shadow, making the rectangle a design element; or (b) chroma-key it with
  a small kept Pillow utility, `cutout.py` (PEP 723; keys out a commanded
  flat background colour with tolerance and edge feathering, writes a
  transparent PNG). `compose*.py` are deleted, but Pillow stays in the
  toolbox via this one helper.
- Backend selection logic (env → memory → detection) is unchanged but only
  runs when a genai piece is actually requested.

### QA loop (replaces the paid self-check/retry loop)

Every screenshot is taken only after `agent-browser wait "body.ready"`
(fonts loaded, images decoded — see Rendering backend). Then Claude Reads
the PNG and checks: headline wording + edge margins, frame integrity,
background colour, breakout alignment and ≤1.0× crop scale, exact pixel
dimensions (`sips -g pixelWidth -g pixelHeight`). Failures are fixed in CSS
and re-rendered — $0 per iteration. Only clean renders are shown to the user.

## Workflow changes (SKILL.md)

- **Phases unchanged:** Recall → Benefit Discovery → Pairing → Generation →
  optional iPad / Localization. Memory-driven resumability unchanged.
- **Version policy replaced.** The 3-versions-then-style-template mechanism
  existed because genai exploration was paid and drifty. Now: render **2–3
  design directions** for the first shot (different CSS, $0), user picks one,
  that `set.css` becomes the set's design system — consistency by
  construction. Subsequent shots render once and iterate freely.
- **Removed:** aspect-ratio/crop step, style-template prompts and "styled
  against vN" bookkeeping, never-switch-backends rule (renderer is
  deterministic), paid-call cost warnings (baseline is $0).
- **Replaced, not removed:** the crop-driven ~70% safe-area rule becomes a
  plain design margin — headline text keeps ≥ ~6% padding from each canvas
  edge (edge-hugging text is still bad at thumbnail size), owned by the
  base template's type/wrap rules.
- **Memory schema:** `aso_generated_screenshots.md` records the design dir,
  per-shot HTML file, render status, and breakout crop notes instead of
  style-template paths. Brand colour stays where it is.
  `aso_localization.md` drops the Flow A/B choice and per-shot
  "styled against" records; it keeps the per-locale translation table and
  adds the raws source per locale (localized simulator raws vs English
  fallback) and per-shot render status.

### iPad (`references/ipad-extension.md`)

Same design files with the iPad frame variables, `set viewport 2064 2752`, adjusted
type scale. Reuses the iPhone set's `set.css` design language. The reference
shrinks to layout constants + workflow deltas.

### Localization (`references/localization.md`)

Flow A/B collapse into one flow: translate headlines (LLM, free), swap in
localized simulator raws if the app UI is localized (keep English raws
otherwise), re-render per locale into `final/<locale>/`. **Zero paid calls;
N locales × M shots = minutes.** Every locale page sets `<html lang>` and
CJK locales vendor a matching heavy webfont (see Typography). The
style-locked enhance choreography and simctl-clone-for-repaint machinery
are deleted (the simctl recipe for *capturing* localized raws stays).

## Retired vs kept

| Component | Fate |
|---|---|
| `compose.py`, `compose_ipad.py`, `compose_common.py` | **Deleted** (HTML render replaces scaffold entirely) |
| `generate_frame*.py`, `assets/device_frame*.png` | **Deleted** (frame drawn in `set.css`) |
| `enhance.py` + backends | **Kept**, opt-in per-piece role |
| `showcase.py` | **Kept** (works on any finals) or later rewritten as an HTML render itself — out of scope here |
| `assets/fonts/` (Inter) | **Kept**, loaded via `@font-face` |
| Crop/resize `sips` loop in SKILL.md | **Deleted** |
| New: `assets/html/` base template (frame CSS, readiness script, type scale) | **Added** |
| New: `cutout.py` (chroma-key helper for genai pieces) | **Added** |

## Migration for existing users

Old memory states (style-template lines, per-shot genai records) still parse
on Recall; the skill reports them and offers a re-render into the new
pipeline. Mixing old genai finals with new HTML finals in one set will look
inconsistent — the skill recommends regenerating the whole set (now free).
No compatibility shim: the genai full-canvas path is gone.

## Risks

- **agent-browser availability.** New required dependency (~Chromium-sized
  install via npm). Mitigated by the existing detect-and-instruct pattern.
- **Cross-platform font rendering.** Mostly mitigated: Latin headlines use
  bundled Inter, CJK locales vendor their webfont (see Typography), so no
  headline depends on a system font. The skill is already macOS-centric
  (simctl, sips) regardless.
- **Design quality variance.** Claude-authored CSS replaces a tuned genai
  prompt. Mitigated by the shipped base template (high floor), the free
  render-Read-adjust loop, and 2–3 design directions for the first shot.
- **Expectation shift.** Output is a clean flat composite, not an embellished
  genai render. Accepted: the genai output was never truly photoreal, and a
  consistent 8/10 floor beats occasional 9/10 with 5/10 smears.

## Testing

Manual, matching the repo's current convention: the developer smoke test is
the one in `assets/html/README.md` (render the shipped `iphone.html` /
`ipad.html` templates → verify dimensions → eyeball), which exercises the
real frame/breakout/readiness code. (An earlier hand-placed spike page that
predated the shipped templates has been deleted — it demonstrated the
retired eyeballed-placement pattern.) At skill runtime there is no dedicated
test render — the first real render plus the QA loop's dimension check
covers it (see Prerequisites check). If the base template grows complex, a
scripted dimension check can be added later.

## Out of scope

- Android/Play Store sizes, video previews, showcase.py rewrite.
- Automated visual-regression tooling.
