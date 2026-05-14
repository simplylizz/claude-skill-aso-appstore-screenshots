# ASO App Store Screenshots

A Claude Code skill that generates high-converting App Store screenshots for your iOS app. It analyzes your codebase, identifies core benefits, and creates professional screenshot images using AI.

> Fork of [adamlyttleapps/claude-skill-aso-appstore-screenshots](https://github.com/adamlyttleapps/claude-skill-aso-appstore-screenshots) — swaps the `gemini-mcp` dependency for a direct `google-genai` SDK call via the bundled `enhance.py` wrapper.

## What It Does

1. **Benefit Discovery** — Analyzes your app's codebase to identify the 3-5 core benefits that drive downloads
2. **Screenshot Pairing** — Reviews your simulator screenshots, rates them, and pairs each with the best benefit
3. **Generation** — Creates polished App Store screenshots using a two-stage process: deterministic scaffolding (compose.py) + AI enhancement (Nano Banana Pro via the bundled `enhance.py` wrapper)
4. **Showcase** — Generates a preview image with all screenshots side-by-side

## Installation

### 1. Add the skill to Claude Code

```bash
claude install-skill github.com/simplylizz/claude-skill-aso-appstore-screenshots
```

### 2. Install `uv`

The Python scripts are run via [`uv`](https://docs.astral.sh/uv/), which auto-installs their dependencies (Pillow, google-genai) into an ephemeral environment on first run — no `pip install` needed.

```bash
brew install uv
# or: curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Set `GEMINI_API_KEY` (for AI enhancement)

The generation phase calls Google's Nano Banana Pro model directly via the `google-genai` SDK (no MCP server required). Grab a key from [Google AI Studio](https://aistudio.google.com/apikey) and export it:

```bash
export GEMINI_API_KEY="..."
# add the line above to ~/.zshrc (or ~/.bashrc) so it persists
```

Optional: override the model id with `GEMINI_MODEL` (default `gemini-3-pro-image-preview`).

## Usage

From within your app's project directory, run:

```
/aso-appstore-screenshots
```

The skill will guide you through each phase interactively. Progress is saved to Claude Code's memory system, so you can resume across conversations.

## How It Works

### Scaffold → Enhance Pipeline

Rather than generating screenshots from scratch (which produces inconsistent results), the skill uses a two-stage approach:

1. **compose.py** creates a deterministic scaffold with exact text positioning, device frame, and your simulator screenshot composited inside
2. **enhance.py** sends the scaffold to Google's **Nano Banana Pro** model — adding a photorealistic device frame, breakout elements, and visual polish

This ensures consistent layout across all screenshots while letting AI handle the creative enhancement.

### Output

Screenshots are saved to a `screenshots/` directory in your project:

```
screenshots/
  01-benefit-slug/          ← working versions
    scaffold.png            ← deterministic compose.py output
    v1.png, v2.png, v3.png  ← AI-enhanced versions
    v1-resized.png, ...     ← cropped to App Store dimensions
  final/                    ← approved screenshots, ready to upload
    01-benefit-slug.png
    02-benefit-slug.png
  showcase.png              ← preview image with all screenshots
```

The `final/` folder contains App Store-ready screenshots at exact Apple dimensions (default: 1290×2796px for iPhone 6.7").

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill prompt — defines the multi-phase workflow |
| `compose.py` | Deterministic scaffold generator (Pillow-based) |
| `enhance.py` | Nano Banana Pro image-edit wrapper (`google-genai` SDK) |
| `generate_frame.py` | Generates the device frame template |
| `showcase.py` | Generates the side-by-side showcase image |
| `assets/device_frame.png` | Pre-rendered iPhone device frame template |
| `assets/fonts/` | Bundled Inter fonts (SIL OFL) used by compose.py and showcase.py |

## License

MIT
