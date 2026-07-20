# ASO App Store Screenshots

A Claude Code skill that generates high-converting App Store screenshots for your iOS app. It analyzes your codebase, identifies core benefits, and renders professional screenshot images deterministically from HTML/CSS.

> Fork of [adamlyttleapps/claude-skill-aso-appstore-screenshots](https://github.com/adamlyttleapps/claude-skill-aso-appstore-screenshots). The upstream skill scaffolds with Pillow and repaints the whole canvas with a paid image model; this fork is **HTML-first** — Claude authors a per-app HTML/CSS design system, a headless browser renders it at exact App Store dimensions, and a generative image model is demoted to an optional, per-piece tool. Every render costs $0 and is reproducible for a given renderer version (structurally identical, not byte-identical across Chromium versions).

## What It Does

1. **Benefit Discovery** — Analyzes your app's codebase to identify the 3-5 core benefits that drive downloads
2. **Screenshot Pairing** — Reviews your simulator screenshots, rates them, and pairs each with the best benefit
3. **iPhone Generation** — Creates polished iPhone App Store screenshots by authoring an HTML/CSS design system (`screenshots/design/set.css` + one HTML page per shot) and rendering each page to a PNG at the exact App Store size with a headless browser. The first shot renders 2-3 free design directions for you to pick from; your pick locks `set.css` as the shared design system for the whole set, so every subsequent shot is consistent by construction. Renders and iteration are $0 — there's no paid image call in the happy path.
4. **Showcase** — Generates a preview image with all iPhone screenshots side-by-side
5. **iPad Extension (optional)** — After the iPhone set is approved, the skill asks whether you want a matching iPad set at 2064×2752. If you say yes, it reuses your benefits, brand colour, and the iPhone set's design language, adds an iPad design system at `screenshots/design/ipad/`, and just needs iPad simulator screenshots; if you decline, it stops. This phase is defined in `references/ipad-extension.md`, which the skill loads on demand.
6. **Localization (optional)** — Once a device's English set is approved, the skill can produce localized sets. It translates the marketing headlines per locale, sets `<html lang>` on each page, and re-renders — **zero paid calls**. If your app's UI is localized you capture localized simulator screenshots (the skill gives you an `xcrun simctl` recipe) so the on-screen UI is genuine; otherwise the on-screen UI stays English under the translated headline. CJK locales (Japanese/Korean/Chinese) vendor a matching heavy webfont (Noto Sans JP/KR/SC Black) so headlines render in the right heavy face. Outputs land in `screenshots/final/<locale>/` (iPad: `screenshots/final/ipad/<locale>/`). This phase is defined in `references/localization.md`, loaded on demand.

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

The bundled Python helpers (`showcase.py`, and the optional `enhance.py` / `cutout.py`) run via [`uv`](https://docs.astral.sh/uv/), which auto-installs their dependencies (Pillow, google-genai) into an ephemeral environment on first run — no `pip install` needed.

```bash
brew install uv
# or: curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install `agent-browser` (the renderer)

Screenshots are rendered by [agent-browser](https://github.com/vercel-labs/agent-browser), a headless-Chromium CLI. This is the one hard prerequisite for generation:

```bash
npm install -g agent-browser
```

The first render downloads Chromium automatically. If it's not installed, the skill tells you this and stops before doing any design work — your benefits and pairings are saved.

### 4. (Optional) An image backend — only for opt-in genai pieces

The happy path renders every screenshot deterministically from HTML and needs **no** image-model access. A generative image model is used only if you explicitly ask for an isolated decorative piece the deterministic pipeline can't produce (an irregular extraction, invented artwork). Only then does `enhance.py` need one of:

- **Gemini** — grab a key from [Google AI Studio](https://aistudio.google.com/apikey) and export it:

  ```bash
  export GEMINI_API_KEY="..."   # GOOGLE_API_KEY is also accepted
  ```

  `enhance.py` reads either variable. Optional: override the model id with `GEMINI_MODEL` (default `gemini-3-pro-image`).

- **codex** — or route through the OpenAI [`codex`](https://developers.openai.com/codex) CLI instead of a Gemini key:

  ```bash
  export ENHANCE_BACKEND=codex   # or pass --backend codex per call
  ```

  Prerequisite: install the codex CLI (`npm install -g @openai/codex`) and sign in with your ChatGPT account.

You don't have to set anything up front — the skill resolves the backend only when a genai piece is actually requested (`ENHANCE_BACKEND` → a remembered default → whatever is available, asking only if both are usable). Neither key is needed to render, showcase, or localize a set.

## Usage

From within your app's project directory, run:

```
/aso-appstore-screenshots
```

The skill will guide you through each phase interactively. Progress is saved to Claude Code's memory system, so you can resume across conversations.

## How It Works

### HTML-first render pipeline

Rather than repainting a whole canvas with an image model (inconsistent, costly), the skill treats the LLM as the designer and a browser as the renderer:

1. **Author** — Claude copies the shipped base template (`assets/html/`) into your project as `screenshots/design/`, adapting `base.css` into a per-app `set.css` (brand colour, uniform type scale, CSS-drawn device frame) and writing one HTML page per benefit. Everything the pages need — fonts, any icon SVGs — is vendored into `screenshots/design/assets/`, so a final render loads **zero** external resources.
2. **Render** — `agent-browser` opens each page at the exact App Store viewport (e.g. `1290 2796`), waits for `body.ready`, and screenshots it. The readiness gate is **fail-closed**: `body.ready` fires only once fonts resolved, every image decoded, the headline font checks out, and the design system's custom properties resolve — a broken or missing asset does NOT pass; the page adds `body.render-error` with a `data-render-error` reason instead, and a `wait "body.ready"` timeout is the signal to read that reason. The viewport **is** the output size — no crop, resize, or aspect-ratio step; the render is natively the exact dimension.
3. **QA loop** — Claude reads each PNG, checks the headline wording/margins, frame integrity, flat background, breakout alignment, and exact pixel dimensions (`sips`), and fixes anything in CSS/HTML before re-rendering. Every iteration is $0.

The uniform type scale and the CSS device frame live in `set.css`, so "same size, same frame on every screenshot" survives per-shot HTML by construction.

### Optional genai pieces

If (and only if) a shot genuinely needs an invented or irregular element, `enhance.py` generates it in isolation on a flat known-colour background, `cutout.py` chroma-keys that background out to a transparent PNG, and the result is composited into the page as a single `<img>` layer — never the whole canvas. The artifact is one small, rejectable element, not a poisoned render.

### Output

Design source and finals are saved under `screenshots/` in your project:

```
screenshots/
  design/                     ← per-app design system + pages (diffable, re-renderable)
    set.css                   ← the set's shared design system (colours, type scale, frame)
    01-benefit-slug.html      ← one page per benefit
    02-benefit-slug.html
    raw/                      ← vendored simulator raws, kebab-case (pages point here)
    assets/                   ← vendored: Inter fonts, any brand font, icon SVGs, genai pieces
    preview/                  ← disposable working renders (candidates, re-renders); never uploaded
  final/                      ← approved, App Store-ready PNGs — the only folder you upload
    01-benefit-slug.png
    02-benefit-slug.png
  showcase.png                ← iPhone showcase

  # Only if you opt into the iPad extension:
  design/ipad/                ← iPad design system (its own set.css + iPad frame variant)
    set.css
    assets/
    01-benefit-slug.html
  final/ipad/                 ← approved iPad screenshots, ready to upload
    01-benefit-slug.png
  showcase-ipad.png           ← iPad showcase

  # Only if you opt into localization (one subdirectory per locale):
  design/de-DE/               ← localized iPhone pages (translated headlines)
  design/ipad/de-DE/          ← localized iPad pages
  final/de-DE/                ← localized iPhone set, ready to upload
  final/ipad/de-DE/           ← localized iPad set, ready to upload
```

Finals are PNGs at exactly the target Apple dimensions (iPhone default 1290×2796, a 6.9"-class accepted size; iPad 13" Pro default 2064×2752) — the render is natively exact, so there are no resized copies. The English set stays at the `final/` (or `final/ipad/`) root; each localized set goes in a subdirectory named by its App Store Connect locale code.

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill prompt — defines the multi-phase workflow (iPhone, then optional iPad / localization) |
| `references/ipad-extension.md` | The opt-in iPad phase, loaded by SKILL.md after the iPhone set is approved |
| `references/localization.md` | The opt-in localization phase, loaded by SKILL.md after a device's English set is approved |
| `assets/html/` | The shipped base template: `base.css` (design system), `iphone.html` / `ipad.html` (example pages), placeholder raws, and a `README.md` documenting the slots, custom properties, and render sequence |
| `assets/fonts/` | Bundled Inter fonts (SIL OFL) — `InterDisplay-Black.otf` for headlines (loaded via `@font-face`, vendored per project) and `Inter-Regular.otf` for the showcase URL |
| `showcase.py` | Generates the side-by-side showcase image from all finals (self-contained; works for iPhone or iPad) |
| `enhance.py` | Optional per-piece image-generation wrapper (`google-genai` SDK or the OpenAI `codex` CLI) — used only for isolated genai pieces, never the full canvas |
| `cutout.py` | Optional chroma-key helper that turns a genai piece's flat background transparent so it can be composited as an `<img>` layer |

## License

MIT
