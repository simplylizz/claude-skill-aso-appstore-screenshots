# Optional genai pieces (opt-in, per-piece, never full-canvas)

This reference owns the full genai-piece flow. It is loaded **only when the user actually opts into a piece** — the happy path (authoring + rendering) never needs it, never needs an API key, and stays $0.

The generative image model (`enhance.py`, kept from the old pipeline) is a narrow tool for **isolated pieces** the deterministic pipeline can't produce well. It NEVER touches the full canvas. Use cases:

- An irregular/non-rectangular extraction a CSS crop can't handle, or content bleeding behind an element.
- A decorative piece the user explicitly wants invented.
- **A hero-shot breakout that the CSS crop can't do justice** — when the composition wants a bigger or crisper panel than the raw raster allows at an acceptable zoom (its magnified text goes mushy), or a non-rectangular panel extraction. Re-render that ONE panel large on a flat key colour via `enhance.py`, cut it out with `cutout.py`, and composite it as the breakout `<img>`. That is ~1 paid call for a single shot, with artifacts confined to that one piece. **Offer this when a hero shot's CSS breakout looks weak** — don't reach for it by default; most breakouts should stay pure CSS crops.

Throughout, `SKILL_DIR` is the skill's base directory — the path shown when the skill loads ("Base directory for this skill: ..."), falling back to `$HOME/.claude/skills/aso-appstore-screenshots`.

## The flow

1. **Resolve the backend** (this is the only place backend selection runs). Order:
   - `ENHANCE_BACKEND` env var set → use it for this run (don't overwrite a saved default).
   - Else a saved `Image backend:` line in `aso_generated_screenshots.md` → use it.
   - Else detect availability:
     ```bash
     { test -n "$GEMINI_API_KEY" || test -n "$GOOGLE_API_KEY"; } && echo "gemini: available" || echo "gemini: no key"
     command -v codex >/dev/null && echo "codex: available" || echo "codex: not installed"
     ```
     Exactly one available → use it and save it as the default. Both available → ask once, recommend `gemini`, save the answer. Neither → tell the user a genai piece needs a Gemini key (`https://aistudio.google.com/apikey`, then `export GEMINI_API_KEY="..."`) or the OpenAI `codex` CLI (`npm install -g @openai/codex`, signed in), and skip the genai piece — the rest of the pipeline is unaffected.
2. **Generate the piece in isolation** on a flat, known background colour (so it can be cut out cleanly), passing `--backend gemini`/`--backend codex`:
   ```bash
   uv run "$SKILL_DIR/enhance.py" --backend gemini \
     --prompt-file piece-prompt.txt --image reference.png \
     --output screenshots/design/assets/piece-raw.png
   ```
   A piece **based on real app UI** (the hero-breakout case) must pass the source raw via `--image` — `enhance.py` accepts prompt-only runs (and warns on stderr when no `--image` is given), but a from-scratch invention of app UI resembles nothing in the app. Pick the background colour **far from any colour in the subject** (a subject with green in it should not sit on green). `cutout.py` keys by RGB distance, so a background near the subject's own colours leaves fringes or eats into the subject — a strong contrasting key like magenta `#FF00FF` for a mostly-warm subject keys cleanly.
3. **Composite it as an `<img>` layer** in the page — never as the whole background. Two supported paths:
   - **Cut it out** with the kept Pillow helper, then place the transparent PNG:
     ```bash
     uv run "$SKILL_DIR/cutout.py" --input screenshots/design/assets/piece-raw.png \
       --color "#FF00FF" --tolerance 30 --feather 4 \
       --output screenshots/design/assets/piece.png
     ```
     `cutout.py`'s real flags are `--input`, `--color` (hex, 3- or 6-digit), `--tolerance`, `--feather`, `--output`. Both `--tolerance` and `--feather` are in **Euclidean-RGB distance units** (0..~441): pixels within `--tolerance` of `--color` go fully transparent, and a `--feather` band just above tolerance ramps alpha for a soft edge. The defaults (tolerance 30, feather 4) are a reasonable start — widen `--tolerance` if a plate still shows (the script warns when the key never fully matched, or only grazed the feather band), but not so far it bites the subject. The default `--feather 4` gives a near-hard edge on a high-contrast subject/background boundary; bump `--feather` (e.g. 20-60) for a softer, more blended edge.
   - **Or frame it intentionally** — display the rectangle inside a visible rounded card with a shadow, making the plate a design element.
4. Re-render the page and run the QA loop. The artifact is now one small, rejectable element — if it's bad, drop it; the rest of the screenshot is untouched.

## Failure handling

A genai piece fails (safety block, quota, transient error) → retry that one call once; if it still fails, surface `enhance.py`'s stderr and drop the piece. The screenshot renders fine without it.
