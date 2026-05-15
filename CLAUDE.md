# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code skill (`aso-appstore-screenshots`) that guides users through creating high-converting App Store screenshots. It is invoked via the `/aso-appstore-screenshots` slash command from within a user's app project.

## Architecture

The skill is composed of:

- **SKILL.md** — The skill prompt. Defines a multi-phase workflow: Benefit Discovery → Screenshot Pairing → iPhone Generation → optional iPad Extension. Uses Claude Code's memory system to persist state across conversations so users can resume mid-workflow. Generation first creates a deterministic scaffold via `compose.py` (or `compose_ipad.py`), then sends it to Nano Banana Pro via `enhance.py` for AI enhancement. The iPad extension is opt-in and only runs after the iPhone set is approved.
- **compose.py** — Standalone Python compositing script (Pillow-based) for iPhone screenshots. Produces a pixel-perfect 1290×2796 PNG with headline text, iPhone device frame template, and the screenshot composited inside. Verb text auto-sizes.
- **compose_ipad.py** — iPad variant of `compose.py`. Produces a 2064×2752 PNG using `assets/device_frame_ipad.png`. Typography and layout constants are pre-tuned for iPad's larger canvas (verb 200-300px, desc 140px, DEVICE_Y=860, text_top=180) — these values avoid the headline-overlapping-device-frame regression seen in earlier iPad runs.
- **enhance.py** — Thin wrapper around the `google-genai` SDK that calls Google's Nano Banana Pro (default model `gemini-3-pro-image-preview`) to edit/enhance the scaffold. Takes `--prompt`/`--prompt-file`, one or more `--image` flags (order preserved), and `--output`. Validates `GEMINI_API_KEY` and all input paths before making the API call. Replaces the previous dependency on the `gemini-mcp` MCP server. Shared between iPhone and iPad pipelines.
- **generate_frame.py** — Generates the iPhone device frame template PNG (`assets/device_frame.png`). Run once. RGBA PNG with a black iPhone body, transparent screen cutout, Dynamic Island, and side buttons.
- **generate_frame_ipad.py** — Generates the iPad device frame template PNG (`assets/device_frame_ipad.png`). Run once. 1720×2300 RGBA PNG with uniform thin bezels on all sides, a tiny front camera dot at top centre (no Dynamic Island), and subtle top-edge power/volume buttons.
- **showcase.py** — Generates a showcase image showing up to 3 final screenshots side-by-side with an optional GitHub link at the bottom. Used as the final step after all screenshots are approved. Works for both iPhone and iPad finals — just point `--screenshots` at the right directory.
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
export GEMINI_API_KEY="..."  # from https://aistudio.google.com/apikey

uv run enhance.py \
  --prompt-file prompt.txt \
  --image scaffold.png \
  [--image style-template.jpg] \
  --output v1.jpg
```

Repeat `--image` to pass multiple references — order is preserved and matches "FIRST image" / "SECOND image" / "THIRD image" wording in the prompt templates inside SKILL.md.

## Key Design Decisions

- **Two-stage generation**: scaffold (deterministic, Pillow) → enhance (Nano Banana Pro). Avoids the inconsistencies of generating from scratch.
- **Scaffold scripts output exact App Store Connect dimensions** — iPhone 1290×2796 from `compose.py`, iPad 2064×2752 from `compose_ipad.py`.
- **Device frames are template images** (`assets/device_frame.png`, `assets/device_frame_ipad.png`) — not drawn at compose time. Regenerate with `uv run generate_frame.py` or `uv run generate_frame_ipad.py` if a frame design needs updating.
- **Verb text auto-sizes** — shrinks within a `(VERB_SIZE_MIN, VERB_SIZE_MAX)` range to fit multi-word verbs (e.g. "TURN YOURSELF" / "FREE UP") within the canvas width.
- **SKILL.md always generates 3 versions in parallel** for each benefit so the user can pick the best one.
- **iPhone needs a side-crop step; iPad does not.** Nano Banana outputs ~0.747 aspect. iPhone target 0.461 is much narrower, so iPhone scaffolds get cropped + resized after every enhance call. iPad target 0.750 is virtually identical, so iPad output just gets resized — no center-crop.
- **iPhone and iPad use separate style templates.** The first approved iPhone screenshot is the style template for subsequent iPhone screenshots; the first approved iPad screenshot is the style template for subsequent iPad screenshots. Never pass an iPhone final as a reference image to an iPad call (or vice versa) — wrong device, wrong aspect, confuses Gemini.
- **iPad extension is opt-in and gated on iPhone approval.** SKILL.md only offers the iPad phase after the iPhone showcase is shown and the user is happy with the iPhone set. Benefits and brand colour are reused — there is no re-discovery.
- **No MCP dependency**: enhancement calls Google's Gemini API directly via `enhance.py` (google-genai SDK). The previous `@houtini/gemini-mcp` integration was removed — only `GEMINI_API_KEY` is required.
- **Memory is central to the workflow** — benefits, screenshot assessments, pairings, brand colour, and per-device generation state are all persisted so users can resume across conversations.
