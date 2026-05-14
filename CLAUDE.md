# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code skill (`aso-appstore-screenshots`) that guides users through creating high-converting App Store screenshots. It is invoked via the `/aso-appstore-screenshots` slash command from within a user's app project.

## Architecture

The skill is composed of:

- **SKILL.md** — The skill prompt. Defines a multi-phase workflow: Benefit Discovery → Screenshot Pairing → Generation. Uses Claude Code's memory system to persist state across conversations so users can resume mid-workflow. Generation first creates a deterministic scaffold via compose.py, then sends it to Nano Banana Pro via enhance.py for AI enhancement.
- **compose.py** — A standalone Python compositing script (Pillow-based) that deterministically renders App Store screenshots. Takes a background hex colour, action verb, benefit descriptor, and simulator screenshot path, then produces a pixel-perfect 1290×2796 PNG with headline text, device frame template, and the screenshot composited inside. The verb text auto-sizes to fit the canvas width.
- **enhance.py** — Thin wrapper around the `google-genai` SDK that calls Google's Nano Banana Pro (default model `gemini-3-pro-image-preview`) to edit/enhance the scaffold. Takes `--prompt`/`--prompt-file`, one or more `--image` flags (order preserved), and `--output`. Validates `GEMINI_API_KEY` and all input paths before making the API call. Replaces the previous dependency on the `gemini-mcp` MCP server.
- **generate_frame.py** — Generates the device frame template PNG (`assets/device_frame.png`). Run once to create or update the template. The template is a 1290×2796 RGBA PNG with a black iPhone body, transparent screen cutout, Dynamic Island, and side buttons.
- **showcase.py** — Generates a showcase image showing up to 3 final screenshots side-by-side with an optional GitHub link at the bottom. Used as the final step after all screenshots are approved.
- **assets/device_frame.png** — Pre-rendered iPhone device frame template used by compose.py. Using a template instead of drawing the frame at compose time ensures pixel-perfect consistency across all generated screenshots.
- **assets/fonts/** — Bundled Inter fonts (SIL OFL): `InterDisplay-Black.otf` for headlines (compose.py), `Inter-Regular.otf` for the showcase URL (showcase.py), and `LICENSE-Inter.txt`.

## Running compose.py

```bash
uv run compose.py \
  --bg "#E31837" \
  --verb "TRACK" \
  --desc "TRADING CARD PRICES" \
  --screenshot path/to/simulator.png \
  --output output.png \
  --accent  # optional: adds dark arc behind device
```

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

- **Two-stage generation**: compose.py creates a deterministic scaffold first (text + frame + screenshot), then Nano Banana Pro enhances it. This avoids the inconsistencies of generating from scratch.
- **compose.py outputs exact App Store Connect dimensions** (1290×2796 for iPhone 6.7") — no post-processing crop needed.
- **Device frame is a template image** (`assets/device_frame.png`) — not drawn at compose time. Regenerate with `uv run generate_frame.py` if the frame design needs updating.
- **Verb text auto-sizes** — shrinks from 172px down to 100px to fit multi-word verbs (e.g. "TURN YOURSELF") within the canvas width.
- **SKILL.md always generates 3 versions in parallel** for each benefit so the user can pick the best one.
- **The crop/resize step in SKILL.md is mandatory** after every `enhance.py` call — raw Nano Banana output is never the correct dimensions for App Store Connect.
- **No MCP dependency**: enhancement calls Google's Gemini API directly via `enhance.py` (google-genai SDK). The previous `@houtini/gemini-mcp` integration was removed — only `GEMINI_API_KEY` is required.
- **Memory is central to the workflow** — benefits, screenshot assessments, pairings, brand colour, and generation state are all persisted so users can resume across conversations.
