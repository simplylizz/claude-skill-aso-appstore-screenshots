# ASO App Store Screenshots

A Claude Code skill that generates high-converting App Store screenshots for your iOS app. It analyzes your codebase, identifies core benefits, and creates professional screenshot images using AI.

> Fork of [adamlyttleapps/claude-skill-aso-appstore-screenshots](https://github.com/adamlyttleapps/claude-skill-aso-appstore-screenshots) — swaps the `gemini-mcp` dependency for a direct `google-genai` SDK call via the bundled `enhance.py` wrapper.

## What It Does

1. **Benefit Discovery** — Analyzes your app's codebase to identify the 3-5 core benefits that drive downloads
2. **Screenshot Pairing** — Reviews your simulator screenshots, rates them, and pairs each with the best benefit
3. **iPhone Generation** — Creates polished iPhone App Store screenshots using a two-stage process: deterministic scaffolding (`compose.py`) + AI enhancement (Nano Banana Pro via the bundled `enhance.py` wrapper)
4. **Showcase** — Generates a preview image with all iPhone screenshots side-by-side
5. **iPad Extension (optional)** — After the iPhone set is approved, the skill asks whether you want to also generate a matching iPad set at 2064×2752 using `compose_ipad.py` + the same `enhance.py` wrapper. If you say yes, it reuses your benefits and brand colour and just needs iPad simulator screenshots; if you decline, it stops. This phase is defined in `references/ipad-extension.md`, which the skill loads on demand.
6. **Localization (optional)** — Once a device's English set is approved, the skill can offer to translate the headlines and regenerate the screenshots per locale (one `enhance.py` call each, reusing the approved English screenshot as the style template). This phase is defined in `references/localization.md`, loaded on demand.

## Installation

### 1. Add the skill to Claude Code

Clone the repo into your Claude Code skills directory:

```bash
git clone https://github.com/simplylizz/claude-skill-aso-appstore-screenshots \
  ~/.claude/skills/aso-appstore-screenshots
```

Claude Code discovers skills placed under `~/.claude/skills/`, so the
`/aso-appstore-screenshots` command becomes available in every project. To
update later, `git pull` inside that directory.

### 2. Install `uv`

The Python scripts are run via [`uv`](https://docs.astral.sh/uv/), which auto-installs their dependencies (Pillow, google-genai) into an ephemeral environment on first run — no `pip install` needed.

```bash
brew install uv
# or: curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Set `GEMINI_API_KEY` (for AI enhancement)

The generation phase calls Google's Nano Banana Pro model directly via the `google-genai` SDK (no MCP server required). Grab a key from [Google AI Studio](https://aistudio.google.com/apikey) and export it:

```bash
export GEMINI_API_KEY="..."   # GOOGLE_API_KEY is also accepted
# add the line above to ~/.zshrc (or ~/.bashrc) so it persists
```

`enhance.py` reads either `GEMINI_API_KEY` or `GOOGLE_API_KEY`. Optional: override the model id with `GEMINI_MODEL` (default `gemini-3-pro-image`).

#### Alternative: the `codex` backend (no Gemini key)

If you'd rather use your ChatGPT/OpenAI subscription than a Gemini API key, `enhance.py` has a second backend that shells out to the OpenAI [`codex`](https://developers.openai.com/codex) CLI in non-interactive mode:

```bash
export ENHANCE_BACKEND=codex   # or pass --backend codex per call
```

Prerequisite: install the codex CLI (`npm install -g @openai/codex`) and sign in with your ChatGPT account. The default `gemini` backend needs no extra tooling. This backend is best-effort — it validates that codex actually wrote a readable image before continuing.

You don't have to set anything up front: the skill resolves the backend automatically — `ENHANCE_BACKEND` if set, else your remembered default, else whatever is available (it asks only if both backends are usable), and it remembers your choice for future runs. It also refuses to silently switch backends mid-set, since the two models render differently and the screenshots wouldn't match.

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

`enhance.py` takes a `--prompt`/`--prompt-file`, one or more ordered `--image` references, an `--output`, and an optional `--aspect-ratio` (e.g. `9:16` for iPhone, `3:4` for iPad) that is requested from the model directly. iPhone results are then side-cropped to Apple's narrower ~0.461 ratio; iPad results only need resizing.

### Output

Screenshots are saved to a `screenshots/` directory in your project:

```
screenshots/
  01-benefit-slug/          ← working iPhone versions
    scaffold.png            ← deterministic compose.py output
    v1.jpg, v2.jpg, v3.jpg  ← AI-enhanced versions
    v1-resized.jpg, ...     ← cropped to iPhone App Store dimensions
  final/                    ← approved iPhone screenshots, ready to upload
    01-benefit-slug.jpg
    02-benefit-slug.jpg
  showcase.png              ← iPhone showcase

  # Only if you opt into the iPad extension:
  ipad/                     ← working iPad versions
    01-benefit-slug/
      scaffold.png
      v1.jpg, v2.jpg, v3.jpg
      v1-resized.jpg, ...   ← resized to iPad App Store dimensions
  final-ipad/               ← approved iPad screenshots, ready to upload
    01-benefit-slug.jpg
  showcase-ipad.png         ← iPad showcase
```

The `final/` and `final-ipad/` folders contain App Store-ready screenshots at exact Apple dimensions (iPhone default 1290×2796, a 6.9"-class accepted size; iPad 13" Pro default 2064×2752). Localized runs are written under `final/<locale>/` (and the iPad equivalent).

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill prompt — defines the multi-phase workflow (iPhone, then optional iPad / localization) |
| `references/ipad-extension.md` | The opt-in iPad phase, loaded by SKILL.md after the iPhone set is approved |
| `references/localization.md` | The opt-in localization phase, loaded by SKILL.md after a device's English set is approved |
| `compose_common.py` | Shared Pillow compositing routine, config, and helpers used by both compose scripts |
| `compose.py` | Deterministic iPhone scaffold generator (thin wrapper over `compose_common`, 1290×2796) |
| `compose_ipad.py` | Deterministic iPad scaffold generator (thin wrapper over `compose_common`, 2064×2752) |
| `enhance.py` | Nano Banana Pro / codex image-edit wrapper (`google-genai` SDK), shared by both pipelines |
| `generate_frame.py` | Generates the iPhone device frame template |
| `generate_frame_ipad.py` | Generates the iPad device frame template |
| `showcase.py` | Generates the side-by-side showcase image from all finals (works for iPhone or iPad) |
| `assets/device_frame.png` | Pre-rendered iPhone device frame template |
| `assets/device_frame_ipad.png` | Pre-rendered iPad device frame template |
| `assets/fonts/` | Bundled Inter fonts (SIL OFL) used by the compose and showcase scripts |

## License

MIT
