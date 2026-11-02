# iPhone Duo Extension (Optional, After iPhone Approved)

This phase is **opt-in** and only runs after the iPhone set is complete and approved. Skip it entirely unless the user explicitly opts in. It is independent of the iPad phase: either can come first, and neither needs the other.

It reuses everything the iPhone set already established: the same benefits, the same brand colour, and the same `screenshots/design/set.css` design language. There is **no re-discovery**. The only new work is capturing iPhone Duo **cover** raws (a squat 0.687 aspect, with a system vertical bar down the trailing edge) and rendering the pages on the Duo canvas.

Throughout this file, `SKILL_DIR` is the skill's base directory: the path shown when the skill loads ("Base directory for this skill: ..."), falling back to the conventional default `$HOME/.claude/skills/aso-appstore-screenshots` if it is not shown. Keep the `SKILL_DIR="..."` variable pattern in the command blocks.

## Why offer it: the mandate and the badge

Facts below were checked on 2026-11-02 against Apple's [screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications) and [Prepare for iPhone Duo](https://developer.apple.com/iphone-duo/prepare/). Re-check both pages if this file is more than a few months old.

- **Required from April 2027** for any app built with the **iOS 27.1 SDK or later**. Before then it is optional.
- **Submitting iPhone Duo screenshots** is what puts the **"optimized for iPhone Duo"** badge on the product page.
- App Store Connect display type **`APP_IPHONE_DUO`**. With the `asc` CLI it is `--device-type IPHONE_DUO`. That mapping passed `asc`'s type validation in a dry run, but **no real upload had been made at the time of writing**, so treat the first upload as the real test and check the result in App Store Connect.

## Prerequisites

Before starting:

1. **iPhone finals must exist**: `screenshots/final/0N-*.png` for every confirmed benefit, plus the iPhone design system at `screenshots/design/set.css`. If they don't, tell the user to finish iPhone first and stop.
2. **Benefits and brand colour are reused** from memory. Do NOT re-run Benefit Discovery.
3. **`agent-browser` must be installed.** Run the existence check once before any design work:

   ```bash
   command -v agent-browser >/dev/null && echo "agent-browser: available" || echo "agent-browser: MISSING"
   ```

   If it's missing, show `npm install -g agent-browser` and stop. There is no separate smoke render: the first real Duo render verifies Chromium for free.
4. **An iPhone Duo simulator**: device type `com.apple.CoreSimulator.SimDeviceType.iPhone-Duo`, which needs an **iOS 27.1 or later** simulator runtime. If `xcrun simctl list devicetypes | grep -i duo` shows nothing, the user needs a newer Xcode/runtime before this phase can run.

No image-model key is required. Rendering is $0; the gemini/codex backends stay optional, resolved only if an opt-in genai piece is requested (SKILL.md's Optional genai pieces → `references/genai-pieces.md`).

## App Store Connect iPhone Duo Dimensions

| Display | Portrait | Landscape | Status here |
|---------|----------|-----------|-------------|
| Cover (outer) | **1398 x 2034px** | 2034 x 1398px | **Supported** portrait target (`body.duo`) |
| Inner (unfolded) | 2007 x 2853px | 2853 x 2007px | Not scriptable to capture (see below); a token adaptation if the user supplies raws |

Up to 10 screenshots per size, PNG or JPEG, **no alpha channel**. Browser renders come out opaque (`sips -g hasAlpha` reports `no`), so finals need no flattening; check anyway in QA.

The supported target is the **cover, portrait, 1398×2034**. The pages render natively at that size via `agent-browser set viewport 1398 2034`; there is no crop or resize step, and QA only *verifies* the dimensions with `sips -g`. Landscape is **unsupported**, as on iPhone and iPad. Targeting the inner display is **not** just a viewport change: adapt the full `body.duo` token set with SKILL.md's proportional-scaling recipe (`f = 2007 ÷ 1398`), keep `--raw-w` at the inner raws' true width, and leave `--screen-scale` unscaled (native 2007-wide raws grow with the canvas, so the ratio already holds; the recipe's ×`f` applies only to reused raws), then re-solve it if the inner's slightly taller aspect (0.703 vs 0.687) moved the bottom bleed. Default to the cover and only take on the inner size if the user explicitly asks and can supply inner raws.

## Step 1: Capture iPhone Duo Cover Screenshots

These are **new captures** with a different aspect and a different system chrome. Ask the user to capture the same screens as the approved iPhone pairings on an iPhone Duo simulator, or capture them yourself when you can drive the simulator.

**The Duo simulator has two displays, so a plain `simctl io screenshot` fails** with "Cannot choose between 2 displays". Pass `--display`, and **resolve which one by size, never by a hard-coded number**: the numbering differs between machines (one test machine had the cover at `--display=1` and the inner at `--display=3`). `--display` accepts a port UUID, so pick the port whose default size is the cover's (the enumeration also lists unrelated framebuffer ports, e.g. 7680×4320 and 720×480, which is why the match is on the exact size):

```bash
UDID="<booted iPhone Duo UDID>"   # xcrun simctl list devices booted
COVER=$(xcrun simctl io "$UDID" enumerate | awk '
  /UUID:/ {u=$2}
  /Default width:/ {w=$3}
  /Default height:/ {if (w==1398 && $3==2034) {print u; exit}}')
[ -n "$COVER" ] || { echo "no 1398x2034 display port found"; exit 1; }
xcrun simctl io "$UDID" screenshot --display="$COVER" raw-duo-01.png
```

`recordVideo` takes the same `--display` flag if a preview video is wanted.

**Which display shows the app.** The fold/hinge state cannot be changed from the command line. A booted Duo simulator shows the app on the **cover**, with the inner display dark, so the cover is the practical capture target. Capturing the inner display needs the Simulator app's own unfold control, which is **not scriptable**: if the user wants inner screenshots, they unfold in Simulator by hand and capture with the inner port (resolved the same way, by 2007×2853).

**The cover's vertical bar is part of the raw.** On the cover, the system draws a **vertical bar down the trailing edge** of the screen (about 84pt, ~252px of the 1398px raw). It holds the status bar (the clock and wifi; no battery or cellular glyphs, and no Dynamic Island on screen) and the **app's toolbar items** (back, sort, and similar). It is genuine iOS UI the buyer will see on their device, so:

- **Do not crop it out** and do not scale the raw to hide it. The frame shows the whole raw.
- **Do not draw an island or camera dot**: `body.duo` draws none, because the raw's top edge has no status bar to cover.
- The app's own content occupies the leading ~1146px. Breakout panels come from there; the bar is system chrome, never a breakout panel.

**Rate the captures** with the iPhone phase's Great / Usable / Retake logic, watching for Duo pitfalls: a layout that left a dead column where the iPhone layout had a bottom tab bar, toolbar items that moved into the bar and left the content area bare, or iPhone UI stretched across the wider cover.

**Preflight the dimensions** with `sips -g pixelWidth -g pixelHeight` on every raw: all identical, portrait, expected **1398×2034**. A uniform non-canonical size (for example inner raws) means setting `--raw-w` to the real width and recomputing `--screen-scale` in the Duo `set.css`; **mixed** sizes mean a recapture. A simulator capture may carry an alpha channel even when every pixel is opaque. That is harmless, because the raw is only an input and the final is a browser render.

**Unverified on the Duo**: whether `xcrun simctl status_bar … override` (the clean 9:41 clock used for the iPhone set) applies to the clock in the vertical bar. Check the first capture; if the override didn't take, say so rather than shipping a mismatched clock silently.

## Step 2: Pair Duo Screenshots with the Same Benefits

The benefits are fixed (approved during iPhone). Pair each benefit to the best **Duo** capture and present the pairings the same way as the iPhone phase, without changing benefit wording. If a benefit has no suitable Duo capture, pause and ask for one; don't proceed with placeholders.

## Step 3: Save Duo Pairings to Memory

Save Duo raw paths + pairings to `aso_duo_pairings.md`, so Duo state is independent of iPhone and iPad state. Cross-link with `[[aso_benefits]]` and `[[aso_screenshot_pairings]]`.

## Step 4: Set Up the Duo Design System

The Duo set gets its own design directory, `screenshots/design/duo/`, so its pages, frame tokens and type scale never collide with the iPhone or iPad sets. It **reuses the iPhone set's design language**: same brand colour, same font vendoring, same accent style.

1. **Start from the shipped Duo base template.** Read `$SKILL_DIR/assets/html/duo.html` (a Duo page skeleton) and the `body.duo` block of `$SKILL_DIR/assets/html/base.css`, plus the current iPhone `screenshots/design/set.css`, so you carry the iPhone set's colours and type intent across.
2. **Create `screenshots/design/duo/set.css`** by adapting the iPhone `set.css`: keep the brand colour, accent shapes and overall look identical, but
   - switch to the **`body.duo` token block** (canvas 1398×2034, `--raw-w: 1398px`, thin bezels, **no island or camera dot**, with `body.duo .device::after { display: none; }`). All geometry stays behind custom properties in this one file;
   - keep the type scale **uniform across the Duo set and never overridden per shot**. The shipped values are the iPad scale ×~0.677 (see the next section); keep text **≥ ~6% from every canvas edge**.
3. **Reuse the vendored fonts; don't duplicate them.** They already live at `screenshots/design/assets/`, so point the Duo `set.css` `@font-face` urls at `../assets/<face>.otf`, one font tree shared by every device set. **Copy the readiness gate** next to the Duo stylesheet so the pages' relative `<script src="ready.js">` resolves: `cp "$SKILL_DIR/assets/html/ready.js" screenshots/design/duo/`.
4. **Write one page per shot**, `screenshots/design/duo/0N-<benefit-slug>.html` (same numbering as the benefits). First **vendor the paired Duo raws** into `screenshots/design/duo/raw/` with URL-safe kebab-case names. Each page is the headline block plus the fixed device snippet `<div class="device"><img class="screen" src="raw/<name>.png">…optional breakout…</div>`, links `set.css`, sets `<html lang>`, sets `<body class="duo">`, and loads the **fail-closed** gate with `<script src="ready.js"></script>`.

### Tuning notes for the short canvas

The cover canvas is only 2034px tall: shorter than the iPhone's 2796px and squatter than the iPad's 0.750 aspect is wide. The shipped `body.duo` block was tuned for that:

- **Tokens are the iPad block ×~0.677** (1398 ÷ 2064): verb 160px, descriptor 73px, bezel 20px, radii 62/41px, device gap 95px. `--head-top` is the exception. It is held at **124px (≥ 6% of the canvas height)** rather than the scaled 114px, because the edge-margin invariant is a canvas percentage.
- **`--screen-scale` (0.8211731 shipped) was re-solved for the bleed**, not scaled. With a one-line verb and a one-line descriptor, the headline block ends at y≈373, the frame starts at y≈468, and its bottom lands ~144px (~7%) past the canvas bottom. That matches the ~7% bleed of the iPhone and iPad blocks while still showing ~93% of the raw's height. Read the value from the file rather than this paragraph if they ever disagree.
- **Headline wrap costs more here.** A two-line verb pushes the device down by ~150px, which on a 2034px canvas hides a lot more of the screen than on iPhone. Prefer shorter verbs, or lower `--verb-size` set-wide, over letting the verb wrap. Render the longest headline before locking `set.css`.
- **The breakout read ratio** is `--zoom ÷ --screen-scale` ≈ `--zoom × 1.22` with the shipped scale (`--zoom: 1.2` reads ~1.46×).
- **The content area is narrower than the raw.** With the ~252px bar excluded, a full-content-width panel is ~1014 raw px. At `--zoom: 1.0` its card is ~1014px on the 1398px canvas, and the card sits **left of the canvas centre**, because the panel sits left of the raw's centre. Sub-block crops buy zoom headroom exactly as on iPhone.

**Breakout** (optional; "clean beats forced" still applies): the full doctrine (coverage floors, shift bounds, the card-box containment formula, measured crops, and the 1:1 QA recipe) is **canonical in SKILL.md's Breakout flow**. Follow it with the Duo `set.css` tokens, run the containment pre-check against the **1398×2034** canvas, and keep crops inside the content area, never the vertical bar.

## Step 5: Render + QA Loop (Identical to iPhone, Duo Viewport)

Renders are **strictly sequential** in one agent-browser session. Set the Duo viewport once, then render each shot:

```bash
agent-browser set viewport 1398 2034
agent-browser open "file://$PWD/screenshots/design/duo/01-<benefit-slug>.html"
agent-browser wait "body.ready"
agent-browser screenshot screenshots/design/duo/preview/01-<benefit-slug>.png
# …QA loop passes AND the user approves, then promote:
cp screenshots/design/duo/preview/01-<benefit-slug>.png screenshots/final/duo/01-<benefit-slug>.png
# …repeat for each shot…
agent-browser close        # when the batch is done
```

**Staging.** Every render goes to `screenshots/design/duo/preview/`, and only after the QA loop passes AND the user approves is it `cp`-promoted to `screenshots/final/duo/`, as on iPhone. **Readiness is fail-closed.** A `wait "body.ready"` timeout means the gate rejected the page, so read `document.body.dataset.renderError`. If the *screenshot* step itself hangs (`Page.captureScreenshot`), use SKILL.md's plain-headless-Chrome fallback with `--window-size=1398,2034`; the NOT-READY banner keeps it fail-closed.

After each screenshot, run the **QA loop** ($0 per iteration):

1. **Read the PNG** and check: headline wording intact with ≥ ~6% margin from every edge; frame integrity (clean bezels, **no island or camera dot**); the raw's **vertical bar present and uncropped** down the trailing edge; flat brand background; the device **bleeds off the canvas bottom** (a frame floating with a gap beneath it breaks the layout family); any breakout fully on the canvas, covering its source, and crisp at the doctrine's target scale.
1b. **Breakout at 1:1 (mandatory if present)**: containment first (the card's outer box inside 1398×2034 with ~40px+ top/bottom margin), then a native-resolution crop of the breakout region + ~80px margin, checked for source slivers, background stripes inside the border, and soft text. Fix containment by **changing the panel, not the placement**.
2. **Verify exact dimensions and no alpha**: `sips -g pixelWidth -g pixelHeight -g hasAlpha screenshots/design/duo/preview/01-<benefit-slug>.png` must report **1398 × 2034** and `hasAlpha: no`.
3. Fix anything in CSS (`set.css` for set-wide, the page only for that shot's breakout or `--device-gap`), re-render, re-check. Only clean renders are shown to the user.

### Version policy: same as iPhone

The **first Duo shot** renders 2–3 directions, each as its own page + stylesheet (`01-<slug>.a.html` → `set-a.css`, …) in `screenshots/design/duo/preview/`. The user picks one, it is `cp`'d to `set.css` and locked, and the candidates are deleted. **Every later shot** renders once against the locked `set.css`; iteration is free.

## Step 6: Duo Finals

Approved renders live at **`screenshots/final/duo/0N-<benefit-slug>.png`**, separate from the iPhone finals (`final/0N-*.png`) and iPad finals (`final/ipad/`). Create the directory before the first promotion:

```bash
mkdir -p screenshots/final/duo
```

Tell the user these go in App Store Connect's **iPhone Duo** slot (display type `APP_IPHONE_DUO`; `asc … --device-type IPHONE_DUO`), not in the 6.9" iPhone slot.

## Step 7: Duo Showcase

After ALL Duo screenshots are approved, generate the Duo showcase with the same `showcase.py`:

```bash
# SKILL_DIR = the base directory shown at skill load (see top of this file); below is the fallback
SKILL_DIR="$HOME/.claude/skills/aso-appstore-screenshots"
uv run "$SKILL_DIR/showcase.py" \
  --screenshots screenshots/final/duo/*.png \
  --github "[URL — reuse whatever the user chose for the iPhone showcase]" \
  --output screenshots/showcase-duo.png
```

Reuse the iPhone showcase's link choice, or **omit `--github`** if they chose no link.

## Duo Output Structure

```
screenshots/
  design/
    set.css                          ← iPhone design system (unchanged)
    duo/                             ← iPhone Duo design system (this phase)
      set.css                        ← body.duo frame tokens + type scale, same brand language
                                       (its @font-face urls point at ../assets/ — one shared font tree)
      ready.js                       ← the shared readiness gate, copied next to this set.css
      raw/                           ← vendored Duo cover raws (vertical bar intact)
      preview/                       ← every Duo render stages here; promoted to final on approval
      01-<benefit-slug>.html
      ...
  final/
    0N-*.png                         ← iPhone finals (unchanged)
    duo/                             ← approved iPhone Duo screenshots, ready to upload
      01-<benefit-slug>.png
      ...
  showcase-duo.png                   ← Duo showcase
```

## Save Duo State to Memory

Update generation memory **incrementally** as each Duo shot is approved. Track separately in `aso_generated_screenshots.md`:

- Duo target display size (iPhone Duo cover 1398×2034)
- Duo **design dir**: `screenshots/design/duo/` (with its locked `set.css`)
- The simulator display used for capture (the cover, resolved by size, plus the UDID if the user wants re-captures to match)
- For each Duo shot: benefit, page file, the Duo raw used, breakout crop notes (or "no breakout"), render status (pending / rendered / approved), and final path (`screenshots/final/duo/0N-<slug>.png`)

## What is unverified (say so when it matters)

- **A real upload of `IPHONE_DUO` through `asc`.** Only a dry run passed type validation. Check the first real upload in App Store Connect.
- **Localization fallback across locales.** It is not established whether App Store Connect falls back to the primary locale's Duo screenshots for a localization that has none, as it does for some other display types. Until it's checked, assume each localization needs its own Duo set, or confirm in App Store Connect after uploading the primary one.
- **Inner-display capture.** It needs the Simulator app's manual unfold, so it can't be scripted, and the inner 2007×2853 canvas has no shipped token block.
- **`simctl status_bar` overrides and `simctl clone` on a Duo**, for clean clocks and localized captures (see `references/localization.md`). Check the first capture.

## Offer Duo Localization

After the Duo **English** showcase is shown and the user is happy, **offer** to localize it, the same way the iPad phase does. If they accept, Read `references/localization.md` and follow it, targeting the **Duo** set: design dir `screenshots/design/duo/`, viewport `1398 2034`, localized outputs under `screenshots/final/duo/<locale>/`, capturing localized raws on the cover with `--display` resolved by size.
