# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code skill (`aso-appstore-screenshots`) that guides users through creating high-converting App Store screenshots. It is invoked via the `/aso-appstore-screenshots` slash command from within a user's app project.

## Architecture

The skill is composed of:

- **SKILL.md** — The skill prompt. Defines a multi-phase workflow: Benefit Discovery → Screenshot Pairing → iPhone Generation → optional iPad Extension / optional Localization. Uses Claude Code's memory system to persist state across conversations so users can resume mid-workflow. Generation first creates a deterministic scaffold via `compose.py` (or `compose_ipad.py`), then sends it to Nano Banana Pro via `enhance.py` for AI enhancement. The iPad and localization phases are opt-in and their full workflows live in `references/` (see below) — SKILL.md keeps only the offer + a "Read this reference" instruction, and loads the file on demand when the user opts in.
- **references/ipad-extension.md** — The full opt-in iPad phase (offered only after the iPhone set is approved). SKILL.md reads it on demand. Reuses benefits and brand colour; no re-discovery.
- **references/localization.md** — The full opt-in localization phase (offered after a device's English set is approved). Two flows, chosen per locale: **Flow A (primary)** — the user captures real localized simulator raws (simctl clone + AppleLanguages/AppleLocale recipe included), per-locale scaffolds are composed with translated headlines, and ONE style-locked enhance call per shot repaints only the decorative shell (locale's shot 01 styled against the English final 01; shots 02..N against the locale's own approved 01); **Flow B (fallback, app UI not localized)** — swap only the headline on the approved English final, on-screen UI intentionally stays English. Both cost N×M enhance calls. Outputs under `final/<locale>/`.
- **compose_common.py** — Shared Pillow-only module (PEP 723 header) holding the `ComposeConfig` frozen dataclass, the `compose()` compositing routine, and the `word_wrap`/`fit_font`/`draw_centered`/`font_for`/`contains_cjk`/`parse_hex_color`/`die`/`warn` helpers that both compose scripts import. The device frame slides down dynamically: `compose()` measures the headline block from `text_top`, then sets `device_y = max(cfg.device_y, text_bottom + min_text_device_gap)` so a tall/wrapping headline never overlaps the frame. Also validates `--bg` (hex, with 3-digit shorthand) and `--screenshot` existence. **CJK fallback**: the bundled Inter font is Latin-only, so `font_for()` transparently swaps in a heavy-weight CJK-capable macOS system font whenever a headline field (verb or desc) contains CJK *letters* (Han incl. Ext-A, kana incl. halfwidth katakana, Hangul — shared CJK punctuation/fullwidth forms alone do NOT trigger it) — Hiragino Sans W8 for Japanese, Apple SD Gothic Neo Heavy for Korean, PingFang SC / Hiragino Sans GB for Chinese. The script family is classified once per `compose()` call from verb+desc combined, so a Han-only verb in a Japanese headline still gets the Japanese face. It scans each `.ttc`'s font indexes at runtime (via `getname()`) to pick the right family+weight rather than hardcoding an index, and warns (no crash) if no CJK font is found. Latin-only text is byte-for-byte unchanged (still Inter). `word_wrap` falls back to per-character wrapping for spaceless CJK text so long CJK descriptors don't overflow.
- **compose.py** — Thin CLI wrapper for iPhone: holds only the iPhone `ComposeConfig` (device_y=720, min_text_device_gap=40, text_top=200, verb 150-256px, desc 124px) and calls `compose()`. Produces a 1290×2796 PNG.
- **compose_ipad.py** — Thin CLI wrapper for iPad: holds only the iPad `ComposeConfig` (device_y=860, min_text_device_gap=40, text_top=180, verb 200-300px, desc 140px). Produces a 2064×2752 PNG using `assets/device_frame_ipad.png`. Identical CLI shape to `compose.py`.
- **enhance.py** — Wrapper around the `google-genai` SDK that calls Google's Nano Banana Pro (default model `gemini-3-pro-image`, overridable via `--model`/`$GEMINI_MODEL`) to edit/enhance the scaffold. Takes `--prompt`/`--prompt-file`, one or more `--image` flags (order preserved), `--output`, an optional `--aspect-ratio` (e.g. `9:16`/`3:4`, passed through to the API as `ImageConfig`; omitted → model default), and `--backend {gemini,codex}`. The gemini backend accepts either `GEMINI_API_KEY` or `GOOGLE_API_KEY`, applies a 300s timeout and bounded retry on transient failures, and saves in the format implied by the output extension. The `codex` backend (env `ENHANCE_BACKEND=codex`) shells out to the OpenAI `codex` CLI instead — no Gemini key needed, but the codex CLI must be installed and signed in; the output is validated as a readable image afterwards. Replaces the previous `gemini-mcp` MCP dependency. Shared between iPhone and iPad pipelines.
- **generate_frame.py** — Generates the iPhone device frame template PNG (`assets/device_frame.png`). Run once. RGBA PNG with a black iPhone body, transparent screen cutout, Dynamic Island, and side buttons.
- **generate_frame_ipad.py** — Generates the iPad device frame template PNG (`assets/device_frame_ipad.png`). Run once. 1720×2300 RGBA PNG with uniform thin bezels on all sides, a tiny front camera dot at top centre (no Dynamic Island), and subtle top-edge power/volume buttons.
- **showcase.py** — Generates a showcase image showing any number of final screenshots side-by-side (the pipeline passes all finals, typically 3-5) with an optional GitHub link at the bottom. Used as the final step after all screenshots are approved. Checks each `--screenshots` path exists first. Works for both iPhone and iPad finals — just point `--screenshots` at the right directory.
- **assets/device_frame.png** — Pre-rendered iPhone device frame template used by `compose.py`.
- **assets/device_frame_ipad.png** — Pre-rendered iPad device frame template used by `compose_ipad.py`.
- **assets/fonts/** — Bundled Inter fonts (SIL OFL): `InterDisplay-Black.otf` for headlines (compose scripts), `Inter-Regular.otf` for the showcase URL (showcase.py), and `LICENSE-Inter.txt`.

## Running compose.py (iPhone)

```bash
uv run compose.py \
  --bg "#E31837" \
  --verb "TRACK" \
  --desc "TRADING CARD PRICES" \
  --screenshot path/to/simulator.png \
  --output output.png
```

## Running compose_ipad.py (iPad)

```bash
uv run compose_ipad.py \
  --bg "#2563EB" \
  --verb "FREE UP" \
  --desc "GIGABYTES OF STORAGE" \
  --screenshot path/to/ipad-simulator.png \
  --output output.png
```

Identical CLI shape — only the layout/typography constants and output dimensions differ.

## Running enhance.py

```bash
export GEMINI_API_KEY="..."  # or GOOGLE_API_KEY; from https://aistudio.google.com/apikey

uv run enhance.py \
  --prompt-file prompt.txt \
  --image scaffold.png \
  [--image style-template.jpg] \
  --aspect-ratio 9:16 \
  --output v1.jpg
```

Repeat `--image` to pass multiple references — order is preserved and matches "FIRST image" / "SECOND image" / "THIRD image" wording in the prompt templates inside SKILL.md and references/ipad-extension.md. Pass `--aspect-ratio 9:16` for iPhone and `--aspect-ratio 3:4` for iPad. To route through the OpenAI codex CLI instead of Gemini (no key required, codex CLI must be installed and signed in), add `--backend codex` or set `ENHANCE_BACKEND=codex`.

## Key Design Decisions

- **Two-stage generation**: scaffold (deterministic, Pillow) → enhance (Nano Banana Pro). Avoids the inconsistencies of generating from scratch.
- **Scaffold scripts output exact App Store Connect dimensions** — iPhone 1290×2796 from `compose.py`, iPad 2064×2752 from `compose_ipad.py`.
- **Device frames are template images** (`assets/device_frame.png`, `assets/device_frame_ipad.png`) — not drawn at compose time. Regenerate with `uv run generate_frame.py` or `uv run generate_frame_ipad.py` if a frame design needs updating.
- **Verb text auto-sizes** — shrinks within each config's `(verb_size_min, verb_size_max)` range to fit multi-word verbs (e.g. "TURN YOURSELF" / "FREE UP") within the canvas width.
- **Version count is first-vs-subsequent, not always 3.** For the FIRST screenshot of a set (iPhone or iPad — each set has its own style template) there is no style template yet, so SKILL.md generates **3 versions in parallel** to explore style space and the approved pick becomes the template. For every SUBSEQUENT screenshot (2..N) the scaffold pins layout and the style template pins device rendering/background/typography, so it generates **ONE version** and presents it; it only fans out to 2-3 parallel alternative calls if the user rejects it or asks for alternatives, rewriting the breakout/secondary descriptions from feedback (never re-rolling the identical prompt). Rejected versions are never reused as creative anchors. Baseline cost is 3 for the first benefit + 1 per subsequent benefit (e.g. 5 calls for 3 benefits), plus iteration rounds. The same policy holds for iPhone (SKILL.md) and iPad (`references/ipad-extension.md`).
- **Aspect ratio is requested explicitly, not left to the model.** iPhone enhance calls pass `--aspect-ratio 9:16` (→ 0.5625) and are then **side-cropped** to Apple's narrower ~0.461 and resized — we remove excess width rather than stretch. iPad enhance calls pass `--aspect-ratio 3:4` (→ 0.750), which already matches the 2064×2752 target (0.750), so iPad output just gets resized — no center-crop.
- **enhance.py has two backends.** `gemini` (default, google-genai SDK, needs `GEMINI_API_KEY` or `GOOGLE_API_KEY`) and `codex` (OpenAI codex CLI, no key, best-effort with output validation). enhance.py itself is non-interactive; SKILL.md's Prerequisites Check owns backend selection: `ENHANCE_BACKEND` env → saved `Image backend:` line in `aso_generated_screenshots.md` → availability detection (ask only when both are usable, recommend gemini, save the answer). Backends are never switched mid-set, and the iPad/localization phases reuse the backend of the set they extend. When documenting the API-key prerequisite, note it only gates the gemini backend.
- **Device frame slides down for tall headlines.** `compose_common.compose()` computes `device_y = max(cfg.device_y, text_bottom + min_text_device_gap)`, so multi-line/wrapping headlines push the device down instead of overlapping the frame. Both compose scripts share this routine.
- **CJK headlines fall back to a system font.** Bundled Inter has no CJK glyphs, so `compose_common.font_for()` detects CJK letters per headline field (verb/desc) — with the script family classified once per `compose()` call from verb+desc combined, so a kanji-only verb in a Japanese headline still gets the Japanese face — and substitutes a heavy macOS system font (Hiragino Sans W8 for ja, Apple SD Gothic Neo Heavy for ko, PingFang SC / Hiragino Sans GB for zh), resolved by scanning `.ttc` indexes at runtime. This lets ja/ko/zh scaffolds render real glyphs instead of tofu, so localization no longer needs a flaky AI repaint step to fix headline text. Latin-only headlines are unchanged (still Inter). Spaceless CJK descriptors wrap per-character.
- **iPhone and iPad use separate style templates.** The first approved iPhone screenshot is the style template for subsequent iPhone screenshots; the first approved iPad screenshot is the style template for subsequent iPad screenshots. Never pass an iPhone final as a reference image to an iPad call (or vice versa) — wrong device, wrong aspect, confuses Gemini.
- **iPad extension and localization are opt-in.** SKILL.md only offers the iPad phase after the iPhone showcase is shown and the user is happy with the iPhone set; localization is offered once a device's English set is approved. Both defer to their `references/` file. Benefits and brand colour are reused — there is no re-discovery.
- **No MCP dependency**: the gemini backend calls Google's Gemini API directly via `enhance.py` (google-genai SDK). The previous `@houtini/gemini-mcp` integration was removed — either `GEMINI_API_KEY` or `GOOGLE_API_KEY` is required (or the codex backend, which needs neither).
- **Memory is central to the workflow** — benefits, screenshot assessments, pairings, brand colour, and per-device generation state are all persisted so users can resume across conversations. Canonical memory files are `aso_benefits.md`, `aso_screenshot_pairings.md`, `aso_generated_screenshots.md` (canonical home of brand colour + display size), `aso_ipad_pairings.md`, and `aso_localization.md` (may be app-prefixed). The generation state records an `iPhone style template: <path> (generated from version vN)` key (and the iPad equivalent) plus a per-screenshot "styled against" record.
