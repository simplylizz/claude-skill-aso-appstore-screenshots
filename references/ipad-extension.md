# iPad Extension (Optional, After iPhone Approved)

This phase is **opt-in** and only runs after the iPhone set is complete and approved. Skip it entirely unless the user explicitly opts in.

It reuses everything the iPhone set already established — the same benefits, the same brand colour, and the same `screenshots/design/set.css` design language. There is **no re-discovery**: same app, same benefits, same visual identity. The only genuinely new work is capturing iPad simulator raws (different aspect, often different layout) and rendering the pages at the iPad canvas size.

Throughout this file, `SKILL_DIR` is the skill's base directory — the path shown when the skill loads ("Base directory for this skill: ..."), falling back to the conventional default `$HOME/.claude/skills/aso-appstore-screenshots` if it is not shown. Keep the `SKILL_DIR="..."` variable pattern in the command blocks.

## Prerequisites

Before starting:

1. **iPhone finals must exist** — `screenshots/final/0N-*.png` for every confirmed benefit, and the iPhone design system at `screenshots/design/set.css`. If they don't, tell the user to finish iPhone first and stop.
2. **Benefits and brand colour are reused** from memory — do NOT re-run Benefit Discovery. Same app, same benefits, same brand colour.
3. **`agent-browser` must be installed.** Run the existence check once before any design work:

   ```bash
   command -v agent-browser >/dev/null && echo "agent-browser: available" || echo "agent-browser: MISSING"
   ```

   If it's missing, show `npm install -g agent-browser` and stop. There is no separate smoke render — the first real iPad render verifies Chromium for free, and the QA loop (Read the PNG + `sips` dimension check) catches any breakage.

No image-model key is required for the iPad set. The gemini/codex backends stay **optional** — resolved only if an opt-in genai piece is actually requested for a specific shot (see SKILL.md's Optional genai pieces → `references/genai-pieces.md`). Rendering itself is $0.

## App Store Connect iPad Dimensions

The only **supported** target is iPad portrait **2064 x 2752px** (iPad 13" Pro). Apple's other portrait sizes:

| Display | Portrait |
|---------|----------|
| iPad 13" Pro (supported) | 2064 x 2752px |
| iPad 12.9" | 2048 x 2732px |
| iPad 11" | 1668 x 2388px |

Landscape is **unsupported** (the frame geometry and layout assume portrait). The iPad pages render natively at 2064×2752 via `agent-browser set viewport 2064 2752` — no crop or resize step; the QA loop only *verifies* the dimensions with `sips -g`. Targeting an 11" or 12.9" size is **not** just a viewport change — it requires adapting the **full iPad `set.css` token set** to the new dimensions. That adaptation is mechanical: follow the proportional-scaling recipe in SKILL.md's App Store Connect Dimensions section (`f = new width ÷ 2064`; scale every px token and `--screen-scale` by `f`, set the canvas vars, keep `--raw-w` at the raws' true width). Default to 2064×2752 and only take on another size if the user explicitly needs it.

## Step 1: Collect iPad Simulator Screenshots

Ask the user for iPad simulator screenshots — these are **different captures** than the iPhone ones (different aspect ratio, often a genuinely different iPad layout: sidebars, split views, top pills instead of bottom tab bars). They can provide:
- A directory (e.g., `./simulator-screenshots/ipad/`)
- Individual file paths
- Glob patterns

Use the Read tool to view each one. Apply the same rating logic (Great / Usable / Retake) and the same retake coaching from the iPhone Screenshot Pairing phase. Watch specifically for iPad pitfalls: half-empty split views, oceans of dead space, and iPhone-scaled UI blown up on a tablet — those read as sloppy at thumbnail size.

**Preflight the dimensions** with `sips -g pixelWidth -g pixelHeight` on every iPad raw: all raws in the set must share **identical portrait dimensions**, expected **2064×2752**. A uniform *non-canonical* size is workable — set `--raw-w` to the actual width and recompute `--screen-scale = intended on-canvas screen width ÷ raw width` in the iPad `set.css` (Step 4). **Mixed** dimensions across the set mean a recapture, not a fudge.

## Step 2: Pair iPad Screenshots with the Same Benefits

The benefits are fixed (already approved during iPhone). Pair each benefit to the best **iPad** screenshot. Present pairings the same way as the iPhone phase. Do not change benefit wording.

If a benefit has no suitable iPad screenshot, pause and ask the user to capture one. Don't proceed with placeholders.

## Step 3: Save iPad Pairings to Memory

Save iPad raw screenshot paths + pairings to memory. Use the iPad pairings file (`aso_ipad_pairings.md`) so iPad state is independent of iPhone state. Cross-link with `[[aso_benefits]]` and `[[aso_screenshot_pairings]]`.

## Step 4: Set Up the iPad Design System

The iPad set gets its own design directory, `screenshots/design/ipad/`, so its pages, its iPad frame CSS, and its type scale never collide with the iPhone set. It **reuses the iPhone set's design language** — same brand colour, same font vendoring, same accent style — so the two sets look like one cohesive family in the App Store.

1. **Start from the shipped iPad base template.** The skill ships `assets/html/ipad.html` (an iPad page skeleton) and `assets/html/base.css` (the reset + frame variables, with an iPad frame variant) in `SKILL_DIR`. Read them, plus the current iPhone `screenshots/design/set.css`, so you carry the iPhone set's colours/type intent into the iPad system.
2. **Create `screenshots/design/ipad/set.css`** by adapting the iPhone `set.css`: keep the brand colour, accent shapes, and overall aesthetic identical, but
   - switch the device-frame custom properties to the **iPad frame variant** (uniform thin bezels on all four sides, a tiny front-camera dot at top centre via a pseudo-element, **no Dynamic Island / no notch**, larger corner radius) — all geometry lives behind CSS custom properties in this one file, so a bezel tweak is a one-file edit shared by every iPad shot;
   - set the canvas variables to **2064 × 2752**;
   - **bump the type scale** for the larger canvas. The verb/descriptor sizes are `set.css` custom properties (e.g. `--verb-size`, `--desc-size`), uniform across the whole iPad set and **never overridden per shot**. iPad headlines can run larger than iPhone (the canvas is much wider); pick sizes that read boldly but keep **≥ ~6% padding from every canvas edge**.
3. **Reuse the iPhone set's vendored fonts — don't duplicate them.** The faces already live at `screenshots/design/assets/` (from iPhone Step 0), and `design/ipad/` nests inside `design/`, so point the iPad `set.css` `@font-face` urls at `../assets/<face>.otf` — still fully in-repo and self-contained (zero external resources), with one font tree that can't drift between the device sets. **Copy the readiness gate** next to the iPad stylesheet so the pages' relative `<script src="ready.js">` resolves, mirroring how each design dir owns its `set.css`: `cp "$SKILL_DIR/assets/html/ready.js" screenshots/design/ipad/`.
4. **Write one page per shot**, named `screenshots/design/ipad/0N-<benefit-slug>.html` (same numbering as the benefits). First **vendor the paired iPad raws** into `screenshots/design/ipad/raw/` with URL-safe kebab-case names (copy them — final renders reference only in-repo assets). Each page is thin: the headline block and the device snippet (an optional breakout nests **inside** `.device`, after `img.screen`). The device markup is the fixed snippet — `<div class="device"><img class="screen" src="…">…optional breakout…</div>` — pointing at the **vendored** iPad raw (`raw/<name>.png`) relatively; **all** frame styling lives in `set.css`, never in the page. Each page links `set.css`, sets an appropriate `<html lang>`, and loads the **fail-closed** readiness gate via `<script src="ready.js"></script>` so `<body>` gets `class="ready"` only once every check passes (fonts, decoded raws matching `--raw-w`, the headline face, resolved stylesheet + background, headline fit) — otherwise it sets `body.render-error` + `document.body.dataset.renderError` with the reasons (see Step 5).

Design by looking at the iPad raw, the brand colour, and the benefit — device position, breakout, and accent shapes are per-shot judgment calls expressed in the HTML/CSS, exactly as on iPhone. The base template gives a high floor; adjust from there.

**Breakout** (optional — "clean beats forced" still applies): the **full doctrine — coverage floors, shift bounds, the card-box containment formula, measured crops, and the 1:1 QA recipe — is canonical in SKILL.md's Breakout flow**; follow it with the iPad `set.css` tokens (its `--screen-scale` / `--bezel` — read the values from the file, don't copy literals into calculations from memory). What changes on iPad:

- **Containment bites hardest here.** The iPad raw is 2752px tall and a big chunk of the device **bleeds off the canvas bottom**, so panels low on the app screen (a bottom filmstrip, a tab bar, a footer toolbar) are **ineligible** — their cards land off-canvas and get sliced by the canvas edge. (Real failure: a filmstrip at raw y≈2260 put the card's centre at canvas y≈2715 — its bottom half was cut off.) Run SKILL.md's containment pre-check against the 2064×2752 canvas before committing to any panel.
- **iPad raws are prone to weak breakouts.** A full-width panel on the ~1660px in-frame device only magnifies ~1.2× — no drama — so when a panel is near-full-screen-width, crop a tight **sub-block** (a stat cluster, a badge + adjacent rows, one row) and magnify THAT. Same target as iPhone: reach for a **≥ ~1.5× read** (`--zoom` ≥ ~1.2); softness is the ceiling, judged in the 1:1 QA read — if the magnified text looks mushy, tighten the sub-block, back off the zoom, or use the opt-in genai hero-breakout path (`references/genai-pieces.md`) for that one shot.

## Step 5: Render + QA Loop (Identical to iPhone, iPad Viewport)

Renders are **strictly sequential** in one agent-browser session (one global viewport, one active page — do not parallelize within a session). Set the iPad viewport once, then render each shot:

```bash
agent-browser set viewport 2064 2752
agent-browser open "file://$PWD/screenshots/design/ipad/01-<benefit-slug>.html"
agent-browser wait "body.ready"
agent-browser screenshot screenshots/design/ipad/preview/01-<benefit-slug>.png
# …QA loop passes AND the user approves, then promote:
cp screenshots/design/ipad/preview/01-<benefit-slug>.png screenshots/final/ipad/01-<benefit-slug>.png
# …repeat for each shot…
agent-browser close        # when the batch is done
```

**Staging — every render goes to `screenshots/design/ipad/preview/`; approval promotes it.** One unconditional rule (same as iPhone): candidates, first renders, and re-renders all write to the working path, and only after the QA loop passes AND the user approves is the preview `cp`-promoted to `screenshots/final/ipad/`. The path never depends on recalled approval state, and a draft can never clobber an approved final.

**Readiness is fail-closed.** If `agent-browser wait "body.ready"` **times out**, the render probably failed the readiness contract, not the wait — inspect `body.render-error` / `document.body.dataset.renderError` for the reasons (missing font, undecoded image, unresolved custom property) and fix before re-rendering.

At the iPad canvas (biggest viewport, photo-heavy raws), `agent-browser screenshot` is also the most likely to hit the `Page.captureScreenshot` timeout — if the *screenshot* step itself hangs, use the plain-headless-Chrome fallback in SKILL.md's Failure handling (set `--window-size=2064,2752`). The fallback captures on a timer rather than waiting on `body.ready`, but it still fails closed: `set.css` paints a full-canvas magenta NOT-READY banner until the gate passes, so a too-early or failed capture is unmissable — if the output shows the banner, raise the virtual-time budget or fix the named `data-render-error` cause. If any shot was produced by the fallback, prefer **re-rendering the whole set with one renderer** before approval so antialiasing and font resolution stay consistent across the set.

After each screenshot, run the **QA loop** — same as iPhone, $0 per iteration:

1. **Read the PNG** and check: headline wording correct and keeping ≥ ~6% margin from every edge; frame integrity (clean bezels, camera dot present, no Dynamic Island); background is the exact brand colour; the breakout is **fully on the canvas** (no card edge sliced by the canvas edge — bezel bleed good, canvas clipping bad) and **covers its source** (a full-panel card fully occludes its panel; a sub-block card covers its own crop's footprint — the rest of the panel is context, not duplication); the breakout scale matches the doctrine (target a ≥ ~1.5× read, i.e. `--zoom` ≥ ~1.2) and the magnified text reads **crisp, not mushy** — if it's soft, tighten the sub-block or back off the zoom.
1b. **If the shot has a breakout, QA it at 1:1 (mandatory).** Check **(a) containment first** — objective and cheap: the card's computed **outer** box (window crop×zoom **plus the 3px border** each side) is inside the 2064×2752 canvas and no card edge is cut by the canvas edge (top/bottom especially). Then, since the full-canvas Read is downscaled ~2.7× and hides 10-30px defects, extract the breakout region **+ ~80px margin at native resolution** (Pillow crop of the render) and Read that for the rest. Require: (a) the card sits fully inside the canvas, (b) no source-panel sliver past any card edge, (c) no background-coloured stripes inside the card border, (d) crisp text. Fix (b)-(d) with the crop, `--shift-x/y`, or `--zoom` and re-render. Fix (a) by **changing the panel, not the placement** — see the containment ladder above.
2. **Verify exact dimensions**: `sips -g pixelWidth -g pixelHeight screenshots/design/ipad/preview/01-<benefit-slug>.png` must report **2064 × 2752** (QA runs on the staged preview — promotion to `final/ipad/` happens only after approval).
3. If anything is off, **fix it in CSS** (in `set.css` for anything set-wide — type scale, frame, background; in the page only for that shot's breakout crop box or device offset), re-render, and re-check. Only clean renders are shown to the user.

### Version policy (first shot vs subsequent) — same as iPhone

- **First iPad shot:** produce **2–3 design directions**, isolated exactly as on iPhone: each candidate is its **own page file linking its own stylesheet** (`01-<slug>.a.html` → `set-a.css`, `.b.html` → `set-b.css`, …, with its own breakout markup — never copied over `set.css`), each rendered to its own PNG **in `screenshots/design/ipad/preview/`** (candidates are working files, not finals). Show them, the user picks one, and that `set.css` is **locked as the iPad set's design system**; promote the chosen render to `screenshots/final/ipad/`. Consistency is by construction — there is no "style template" reference image and no "styled against" bookkeeping.
- **Every subsequent iPad shot:** render **once** against the locked `set.css` (to `preview/`, like everything) and present it; promote to `screenshots/final/ipad/` on approval. Iterate freely if the user wants changes — each re-render is $0. If they want to explore alternatives for a shot, render a couple of variant pages to `preview/`; no fan-out cost, no rejected-anchor rules.

There are no paid-call counts to warn about. Baseline cost is **$0** for the whole iPad set.

## Step 6: iPad Finals

Approved renders live at **`screenshots/final/ipad/0N-<benefit-slug>.png`** — a dedicated iPad subdirectory under `screenshots/final/`, kept separate from the iPhone finals at `screenshots/final/0N-*.png` so the two sets don't collide. There is no post-processing: every render stages in `screenshots/design/ipad/preview/` and becomes final by **`cp`-ing it over** once QA passes and the user approves. Make sure the directory exists first:

```bash
mkdir -p screenshots/final/ipad
```

## Step 7: iPad Showcase

After ALL iPad screenshots are approved, generate an iPad showcase image. The same `showcase.py` script is kept (it accepts any number of screenshots) — point it at ALL the iPad finals:

```bash
# SKILL_DIR = the base directory shown at skill load (see top of this file); below is the fallback
SKILL_DIR="$HOME/.claude/skills/aso-appstore-screenshots"
uv run "$SKILL_DIR/showcase.py" \
  --screenshots screenshots/final/ipad/*.png \
  --github "[URL — reuse whatever the user chose for the iPhone showcase]" \
  --output screenshots/showcase-ipad.png
```

Reuse whatever link choice the user made for the iPhone showcase — the same URL, or **omit the `--github` flag entirely** if they chose no link.

## iPad Output Structure

```
screenshots/
  design/
    set.css                          ← iPhone design system (unchanged)
    0N-*.html                        ← iPhone pages
    ipad/                            ← iPad design system (this phase)
      set.css                        ← iPad frame variables + type scale, same brand language
                                       (its @font-face urls point at ../assets/ — one shared font tree)
      ready.js                       ← the shared readiness gate, copied next to this set.css
      raw/                           ← vendored iPad raws (URL-safe names; pages point here)
      preview/                       ← every iPad render stages here; promoted to final on approval
      01-<benefit-slug>.html
      02-<benefit-slug>.html
      ...
  final/
    0N-*.png                         ← iPhone finals (unchanged)
    ipad/                            ← approved iPad screenshots, ready to upload
      01-<benefit-slug>.png
      02-<benefit-slug>.png
      ...
  showcase-ipad.png                  ← iPad showcase
```

## Save iPad State to Memory

Update generation memory **incrementally** as each iPad screenshot is approved (mirror the iPhone pattern). Track separately in `aso_generated_screenshots.md`:

- iPad target display size (e.g., iPad 13" Pro 2064×2752)
- iPad **design dir**: `screenshots/design/ipad/` (with its locked `set.css`)
- For each iPad shot: benefit, page file (`screenshots/design/ipad/0N-<slug>.html`), the iPad raw used, breakout crop notes (which panel, the crop box, or "no breakout"), render status (pending / rendered / approved), and final path (`screenshots/final/ipad/0N-<slug>.png`)

There is no style-template line and no "styled against" record — the locked `set.css` is the single source of consistency, and it's a file in the repo. This keeps the iPad set resumable across conversations the same way iPhone is.

## Offer iPad Localization

After the iPad **English** showcase is shown and the user is happy with the iPad set, **explicitly offer** to localize it (only now — iPad localization is not offered before the iPad English set is approved):

```
Your iPad set is complete. Want me to also localize it into other languages?

This translates each iPad headline per locale and re-renders the pages — zero paid calls.
If your app's UI supports the language, you capture localized iPad simulator screenshots and
each shot is rebuilt around the real localized UI; otherwise the on-screen UI stays English
under the translated headline.

Reply "yes" to start, or "no" / "later" to stop here. Memory persists, so you can always
come back and localize later.
```

If the user accepts, Read `references/localization.md` (relative to the skill directory) and follow it, targeting the **iPad** set: the iPad design dir (`screenshots/design/ipad/`), viewport `2064 2752`, and localized outputs under `screenshots/final/ipad/<locale>/`.
