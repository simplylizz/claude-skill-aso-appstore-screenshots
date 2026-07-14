# iPad Extension (Optional, After iPhone Approved)

This phase is **opt-in** and only runs after the iPhone set is complete and approved. Skip it entirely unless the user explicitly opts in.

Throughout this file, `SKILL_DIR` is the skill's base directory — the path shown when the skill loads ("Base directory for this skill: ..."), falling back to the conventional default `$HOME/.claude/skills/aso-appstore-screenshots` if it is not shown. Keep the `SKILL_DIR="..."` variable pattern in the command blocks.

## Prerequisites

Before starting:

1. **iPhone finals must exist** — `screenshots/final/0N-*.jpg` for every confirmed benefit. If they don't, tell the user to finish iPhone first and stop.
2. **Benefits and brand colour are reused** from memory — do NOT re-run Benefit Discovery. Same app, same benefits.
3. **Image backend** — reuse the backend the iPhone set was generated with (the `Image backend:` line in `aso_generated_screenshots.md`); pass it as `--backend` on every `enhance.py` call. Do not switch backends between the iPhone and iPad sets without warning the user (different models render differently — the sets won't match). Its prerequisite must still hold: gemini needs `GEMINI_API_KEY` or `GOOGLE_API_KEY`; codex needs the `codex` CLI installed and signed in, no key.

## App Store Connect iPad Dimensions

Apple's iPad portrait sizes:

| Display | Portrait | Landscape |
|---------|----------|-----------|
| iPad 13" Pro (default) | 2064 x 2752px | 2752 x 2064px |
| iPad 12.9" | 2048 x 2732px | 2732 x 2048px |
| iPad 11" | 1668 x 2388px | 2388 x 1668px |

Default to **2064 x 2752px** (iPad 13" Pro). Ask the user which size(s) they need if unclear.

**Aspect note**: Every iPad `enhance.py` call passes `--aspect-ratio "3:4"` (0.75), which **exactly matches** iPad 13" Pro's target of 2064×2752 (0.750). So iPad needs **only a resize — no center-crop step**. This is the main pipeline difference vs iPhone (which passes `--aspect-ratio "9:16"` and then side-crops from 0.5625 down to Apple's narrower 0.461, because that aspect doesn't match the target).

## Step 1: Collect iPad Simulator Screenshots

Ask the user for iPad simulator screenshots — these are **different captures** than the iPhone ones (different aspect ratio, often different layout). They can provide:
- A directory (e.g., `./simulator-screenshots/ipad/`)
- Individual file paths
- Glob patterns

Use the Read tool to view each one. Apply the same rating logic (Great / Usable / Retake) and the same retake coaching from the iPhone Screenshot Pairing phase.

## Step 2: Pair iPad Screenshots with the Same Benefits

The benefits are fixed (already approved during iPhone). Pair each benefit to the best **iPad** screenshot. Present pairings the same way as the iPhone phase. Do not change benefit wording.

If a benefit has no suitable iPad screenshot, pause and ask the user to capture one. Don't proceed with placeholders.

## Step 3: Save iPad Pairings to Memory

Save iPad raw screenshot paths + pairings to memory. Use the iPad pairings file (`aso_ipad_pairings.md`) so iPad state is independent of iPhone state. Cross-link with `[[aso_benefits]]` and `[[aso_screenshot_pairings]]`.

## Step 4: Generate iPad Scaffolds with `compose_ipad.py`

The skill ships a dedicated iPad compositor and frame template:
- `compose_ipad.py` — outputs 2064×2752 PNGs with pre-tuned iPad typography (verb 200-300px, desc 140px) and a safe headline-to-device gap
- `assets/device_frame_ipad.png` — pre-rendered iPad frame (thin uniform bezels, camera dot at top, no Dynamic Island)

**IMPORTANT — Batch all 3 scaffolds into a single Bash call** (same parallelization pattern as iPhone). The three invocations below are illustrative — run **one per confirmed benefit** (3-5 total), not exactly three:

```bash
SKILL_DIR="$HOME/.claude/skills/aso-appstore-screenshots" && \
mkdir -p screenshots/ipad/01-[benefit-slug] screenshots/ipad/02-[benefit-slug] screenshots/ipad/03-[benefit-slug] && \
uv run "$SKILL_DIR/compose_ipad.py" \
  --bg "[HEX CODE]" --verb "[VERB 1]" --desc "[DESC 1]" \
  --screenshot [path/to/ipad-screenshot-1.png] \
  --output screenshots/ipad/01-[benefit-slug]/scaffold.png && \
uv run "$SKILL_DIR/compose_ipad.py" \
  --bg "[HEX CODE]" --verb "[VERB 2]" --desc "[DESC 2]" \
  --screenshot [path/to/ipad-screenshot-2.png] \
  --output screenshots/ipad/02-[benefit-slug]/scaffold.png && \
uv run "$SKILL_DIR/compose_ipad.py" \
  --bg "[HEX CODE]" --verb "[VERB 3]" --desc "[DESC 3]" \
  --screenshot [path/to/ipad-screenshot-3.png] \
  --output screenshots/ipad/03-[benefit-slug]/scaffold.png
```

Like the iPhone scaffolds, these are intermediates — don't show them to the user. But before firing the paid enhance calls, **Read each scaffold image yourself and verify**: headline wording correct, text does not overlap the device frame, correct background colour. Fix any that fail (re-run `compose_ipad.py`) before spending money on enhancement.

## Step 5: Enhance with Nano Banana Pro

**Version count matches the iPhone policy — it depends on whether an iPad style template exists yet:**
- **The FIRST iPad screenshot** (no approved iPad style template yet): generate **3 versions in parallel** so the user can pick the best one. That approved pick becomes the iPad style template.
- **Every SUBSEQUENT iPad screenshot (2..N)**: the scaffold pins the layout and the approved iPad style template pins the device rendering, background, and typography, so generate **ONE version** (a single enhance call with scaffold + iPad style template), post-process it, self-check it, and present that one. Only if the user **rejects it or asks for alternatives** do you fan out with 2-3 parallel alternative calls, rewriting the PRIMARY breakout / SECONDARY elements descriptions from their feedback (not re-rolling the identical prompt).

When iPad generation begins, tell the user roughly how many paid image calls the iPad set will take — **3 for the first benefit plus 1 for each subsequent benefit** (e.g. at least 5 calls for 3 benefits), plus any iteration rounds.

The flow mirrors the iPhone enhancement. Every iPad call passes `--aspect-ratio "3:4"`. Two key differences from iPhone:

1. **Do NOT pass the iPhone style template as a reference image.** The iPhone finals are the wrong aspect and wrong device — they will confuse Gemini. The iPad set has its **own** style template (the first approved iPad screenshot, set during the first iPad benefit).
2. **iPad-specific prompt language** — call out the iPad device frame explicitly, and avoid prompt phrasing that triggers known regressions (see "iPad gotchas" below).

For the first iPad screenshot, emit 3 parallel `Bash` calls in a single message, one per version, varying only `--output` (`v1.jpg`, `v2.jpg`, `v3.jpg`). For a subsequent iPad screenshot, emit a single `enhance.py` call producing just `v1.jpg`:

```bash
SKILL_DIR="$HOME/.claude/skills/aso-appstore-screenshots"
uv run "$SKILL_DIR/enhance.py" \
  --prompt-file screenshots/ipad/01-[benefit-slug]/prompt.txt \
  --aspect-ratio "3:4" \
  --image screenshots/ipad/01-[benefit-slug]/scaffold.png \
  [--image screenshots/final-ipad/01-[first-benefit-slug].jpg]  # only for subsequent screenshots
  --output screenshots/ipad/01-[benefit-slug]/v1.jpg
```

### First iPad screenshot (no iPad style template yet)

Pass only the scaffold as `--image`. Use the **iPad first-screenshot prompt template** below:

```
This is a SCAFFOLD for an iPad App Store screenshot — a rough layout showing the correct headline text, iPad device frame position, and app screenshot placement. Your job is to transform this into a polished, professional App Store marketing screenshot for the iPad.

KEEP EXACTLY AS-IS:
- The headline text (wording, position, and approximate size)
- The app screenshot shown on the iPad screen — including any tabs, pills, navigation chrome, and UI labels exactly as they appear
- The background colour (solid flat #[HEX])

ENHANCE AND POLISH:
- Replace the placeholder device frame with a photorealistic iPad Pro 13" mockup — uniform thin bezels on all four sides (NOT iPhone-style asymmetric bezels), no Dynamic Island, no notch, optional tiny front camera dot at the top centre. Keep the same size and position as the scaffold.
- The output must be iPad portrait aspect (near 3:4, not the 9:19.5 phone shape). Do not crop or letterbox to phone dimensions.
- OPTIONALLY add a PRIMARY breakout element — but ONLY if there is an obvious, visually compelling UI panel on the app screen that directly relates to the benefit headline. If nothing clearly reinforces the headline, skip the breakout entirely. When used, it MUST be an entire UI panel or grouped section (NOT individual small elements like a single button or icon). The panel must stay at the SAME vertical position and orientation as on screen — do NOT rotate or angle it. The panel must be SCALED UP significantly — rendered much larger than it appears on the iPad screen — so that it extends dramatically beyond BOTH left and right edges of the device frame, clearly overlapping the bezel on both sides, expanding to nearly the full width of the screenshot canvas. Do NOT keep the panel at its original on-screen size. The panel itself must be enlarged. It should appear to float in front of the device at this larger scale — add a soft drop shadow beneath it to create depth. The panel MUST come from the app screenshot — same colours, same style, same content. Do NOT invent new elements.
[PRIMARY BREAKOUT — describe the specific iPad UI panel to pop out, or "No breakout — the app screen speaks for itself."]
- Optionally add 1-2 small secondary elements that reinforce the benefit. Do not invent fake category headers, fake subtitles, or fake AI banners.
[SECONDARY ELEMENTS (optional) — 0-2 small supporting elements, or "None needed"]
- Background must be a clean solid brand colour. No glows, gradients, radial patterns, or light effects.

No watermarks, no extra text, no app store UI chrome. Output must be iPad portrait aspect.
```

### Subsequent iPad screenshots (after the first is approved)

Pass **two `--image` flags** — order matters:
1. `--image screenshots/ipad/0N-[benefit-slug]/scaffold.png` — the scaffold (FIRST image)
2. `--image screenshots/final-ipad/01-[first-benefit-slug].jpg` — the first approved **iPad** screenshot (SECOND image, style template)

Use the **iPad subsequent-screenshot prompt template**:

```
You are creating the next screenshot in an iPad App Store screenshot SET. It must look like it belongs to the same series as the style reference.

TWO REFERENCE IMAGES:
- FIRST image: The SCAFFOLD — use this as the definitive guide for layout: headline text wording/position, iPad device frame placement, and the app screenshot on screen. This defines WHAT this screenshot shows.
- SECOND image: The STYLE TEMPLATE — this is an already-approved iPad screenshot from the same set. Match its visual style EXACTLY: same iPad device frame rendering (this is critical — the tablet must look identical), same text treatment, same background style/accents, same level of polish, same overall aesthetic. This defines HOW this screenshot should look. When in doubt, copy the style template more closely rather than less.

REQUIREMENTS:
- CRITICAL: The device frame MUST match the style template EXACTLY — same photorealistic iPad Pro 13" rendering with uniform thin bezels on all four sides (NOT iPhone-style asymmetric bezels), no Dynamic Island, no notch, optional tiny front camera dot at the top centre, same size, same position, same shadows, same reflections, same edge treatment. Do NOT reinvent or reimagine the device frame. Reproduce it as closely as possible from the style template, only changing the screen contents.
- Match the style template's text rendering style (same font treatment, same crispness, same visual weight)
- Match the style template's background — clean, solid brand colour. No glows, gradients, radial patterns, or light effects.
- Use the scaffold's layout for positioning (text, device, screenshot placement)
- Keep the app screenshot exactly as captured. Do NOT add any horizontal banner, header bar, or full-width strip with the text "AI". Do NOT invent an iPhone-style bottom tab bar — reproduce the app's real iPad navigation (top pill, sidebar, or whatever the captured screen shows) exactly as it appears. Do NOT invent fake category headers, fake subtitles, or filler content to occupy empty space — legitimate empty space stays empty.
- OPTIONALLY add a PRIMARY breakout element — but ONLY if there is an obvious, visually compelling UI panel on the app screen that directly relates to the benefit headline. If nothing clearly reinforces the headline, skip the breakout entirely. When used, it MUST be an entire UI panel or grouped section (NOT individual small elements like a single button or icon). The panel must stay at the SAME vertical position and orientation as on screen — do NOT rotate or angle it. The panel must be SCALED UP significantly — rendered much larger than it appears on the iPad screen — so that it extends dramatically beyond BOTH left and right edges of the device frame, clearly overlapping the bezel on both sides, expanding to nearly the full width of the screenshot canvas. Do NOT keep the panel at its original on-screen size. The panel itself must be enlarged. It should appear to float in front of the device at this larger scale — add a soft drop shadow beneath it to create depth. The panel MUST come from the app screenshot — same colours, same style, same content. Do NOT invent new elements.
[PRIMARY BREAKOUT — if a relevant panel is obvious, describe the specific iPad UI panel visible on screen to pop out with a drop shadow, extending beyond both device frame edges. Otherwise write "No breakout — the app screen speaks for itself."]
- Optionally add 1-2 secondary elements that reinforce the benefit and message of the screenshot — the kind of enhancements a professional graphic designer would add for impact. These are NOT from the app UI; they are creative additions that help clearly communicate what the screenshot is trying to portray to the user browsing the App Store. They should carry the message and support ASO conversion, but never at the cost of the overall design aesthetic. They must not compete with the primary breakout for attention.
[SECONDARY ELEMENTS (optional) — 0-2 small supporting elements that tell the story, or "None needed"]
- The breakout elements should match the style and energy level of those in the style template

The result must look like it was designed alongside the style template as part of the same professional set. When placed side-by-side in the App Store, they should be visually cohesive — same quality, same aesthetic, same design language, just different content.

No watermarks, no extra text, no app store UI chrome. Output must be iPad portrait aspect.
```

## Step 6: Resize to App Store Dimensions (No Center-Crop)

⚠️ Run this immediately after the `enhance.py` call(s) complete, before showing the user anything.

**Single Bash call for every version produced this round** (one permission prompt). List exactly the versions produced — all three (`v1 v2 v3`) after a first-screenshot or fan-out round, or just `v1.jpg` after a single-version subsequent generation:

```bash
TARGET_W=2064 && TARGET_H=2752 && \
for INPUT in screenshots/ipad/01-[benefit-slug]/v1.jpg screenshots/ipad/01-[benefit-slug]/v2.jpg screenshots/ipad/01-[benefit-slug]/v3.jpg; do
  OUTPUT="${INPUT%.jpg}-resized.jpg"
  cp "$INPUT" "$OUTPUT"
  sips -z $TARGET_H $TARGET_W "$OUTPUT"
  echo "--- $OUTPUT ---"
  sips -g pixelWidth -g pixelHeight "$OUTPUT"
done
```

Why no crop step: the `--aspect-ratio "3:4"` request makes Gemini output at 0.75, and the iPad 13" Pro target is 0.750 — a straight resize is correct; cropping would needlessly trim pixels.

Target dimensions per iPad size:
- iPad 13" Pro (default): `TARGET_W=2064 TARGET_H=2752`
- iPad 12.9": `TARGET_W=2048 TARGET_H=2732`
- iPad 11": `TARGET_W=1668 TARGET_H=2388` — ⚠️ this target is 0.699, not 0.75, so a straight resize would distort by ~7%. For the 11" size only, first center-crop the 3:4 output to the target ratio (use the iPhone-style crop loop from the main skill's Step 3, which computes `CROP_W` from the target ratio and is aspect-agnostic), then resize. The raw `v*.jpg` files can be re-processed at any time without a new paid call.

## Step 7: Review, Iterate, and Approve

**Before presenting anything, Read every resized output produced this round yourself and self-check each** (all three after a first-screenshot / fan-out round, or the single `v1-resized.jpg` after a subsequent-screenshot generation): headline text intact and correctly worded, iPad device frame matches the style template (or looks like a clean photorealistic iPad for the first), background flat and the correct brand colour, and none of the gotchas below present. Regenerate any obviously broken version — capped at **ONE automatic retry** per version before showing the user what you have.

Show the user the **resized** version(s) and ask them to pick or request changes — 3 labelled versions for the first iPad screenshot, or the single version for a subsequent one.

**If the user rejects the version(s) or asks for alternatives:** do NOT reuse any rejected version as an anchor. Rewrite the PRIMARY breakout and SECONDARY elements descriptions and re-run the **initial-style call** (for the first iPad screenshot: scaffold-only call, 1 image; for subsequent: 2-image call, scaffold + iPad style template). For a subsequent screenshot, this is where you fan out to 2-3 parallel alternative calls (varying only `--output`).

**Single-version iteration:** for a small targeted tweak to a version the user already likes, run just **1** enhance call.

Iteration reference images (each `enhance.py` call passes `--aspect-ratio "3:4"`):

- **Iterating on a SUBSEQUENT iPad screenshot** (an approved `screenshots/final-ipad/01-*.jpg` exists): pass **three `--image` flags** — scaffold, the iPad style template (`screenshots/final-ipad/01-*.jpg`), and the version the user liked best (`vN-resized.jpg`). The prompt references SCAFFOLD (layout), STYLE TEMPLATE (device frame + visual style), and APPROVED DESIGN DIRECTION (creative direction), plus the user's requested changes.
- **Iterating on the FIRST iPad screenshot** (nothing in `screenshots/final-ipad/` yet — no style template): pass **two `--image` flags only** — the scaffold and the version the user liked best. Drop the STYLE TEMPLATE paragraph from the iteration prompt entirely. If the user liked NONE of the 3, re-run the initial **scaffold-only call** (1 image) with a revised breakout/secondary description instead of anchoring on a rejected version.

After each iteration round, **immediately run the Step 6 resize loop** before showing the user. Repeat until the user is happy.

## Step 8: Copy Approved Version to `final-ipad/`

```bash
mkdir -p screenshots/final-ipad
cp "screenshots/ipad/01-[benefit-slug]/v2-resized.jpg" "screenshots/final-ipad/01-[benefit-slug].jpg"
```

The first approved iPad final becomes the iPad style template for all subsequent iPad screenshots.

## Step 9: iPad Showcase

After ALL iPad screenshots are approved, generate an iPad showcase image. Same `showcase.py` script (it accepts any number of screenshots) — point it at ALL the iPad finals via a glob:

```bash
SKILL_DIR="$HOME/.claude/skills/aso-appstore-screenshots"
uv run "$SKILL_DIR/showcase.py" \
  --screenshots screenshots/final-ipad/*.jpg \
  --github "[URL — reuse whatever the user chose for the iPhone showcase]" \
  --output screenshots/showcase-ipad.png
```

Reuse whatever link choice the user made for the iPhone showcase — the same URL, or **omit the `--github` flag entirely** if they chose no link.

## iPad Output Structure

```
screenshots/
  ipad/                              ← working iPad versions
    01-[benefit-slug]/
      scaffold.png
      v1.jpg, v2.jpg, v3.jpg
      v1-resized.jpg, ...
    02-[benefit-slug]/
      ...
  final-ipad/                        ← approved iPad screenshots, ready to upload
    01-[benefit-slug].jpg
    02-[benefit-slug].jpg
    ...
  showcase-ipad.png                  ← iPad showcase
```

Kept separate from the iPhone `screenshots/01-*/` and `screenshots/final/` folders so the two sets don't collide.

## iPad Gotchas (KNOWN, DO NOT REPEAT)

These are mistakes that have happened in real iPad runs. Read this section before writing any iPad prompts.

- **No "AI banner" prompts.** Phrases like _"optionally add a subtle 'AI' pictogram or scanning-line motif on the row"_ get interpreted by Gemini as a full-width horizontal `AI` banner above the breakout, which looks meaningless. When the benefit is AI-related, convey it via the **headline** and the **visual content** (e.g. four near-identical thumbnails for "find similar photos"). Use at most a single tiny gold sparkle or crown accent. Explicitly include a guardrail in the prompt: _"Do NOT add any horizontal banner, header bar, or full-width strip with the text 'AI'."_
- **No iPhone tab bars on iPad screens.** If the app's actual iPad UI uses a top pill / sidebar / iPad-native navigation (e.g. a "Home / Settings" pill at the top), the prompt must say so explicitly. Otherwise Gemini tends to "fix" the layout by inventing an iPhone-style bottom tab bar that doesn't exist in the real app.
- **Don't let Gemini fill dead space.** Some iPad home screens have legitimate empty space below the main content. Gemini's instinct is to "fill" with fake category headers or invented subtitles. The prompt must reinforce: _"Keep the app screenshot exactly as captured — do not invent extra UI elements, fake category subtitles, or filler content to occupy empty space."_
- **Typography is pre-tuned in `compose_ipad.py`.** The current constants (verb 200-300px, desc 140px, DEVICE_Y=860, text_top=180) give a safe headline-to-device gap. Do not edit these unless the user reports a specific overlap or padding issue — earlier values (verb 360, DEVICE_Y=760) caused ~110px overlap of headline onto the device frame.
- **First-screenshot anchor matters.** The first approved iPad screenshot becomes the style template for the entire iPad set. If it has a regression (phantom tab bar, fake subtitles, AI banner), every subsequent screenshot inherits it. Re-generate the first one until it's clean before moving on.

## Save iPad State to Memory

Update generation memory **incrementally** as each iPad screenshot is approved (mirror the iPhone pattern). Track separately in `aso_generated_screenshots.md`:

- iPad target display size (e.g., iPad 13" Pro 2064×2752)
- **iPad style template** (REQUIRED): `iPad style template: <final path> (generated from version vN)` — the approved iPad final all subsequent iPad screenshots are styled against. Update this line whenever the iPad template screenshot is regenerated.
- For each iPad screenshot: benefit, working folder, approved version, final path, which template file/version it was generated against, iPad raw screenshot used, gotchas hit / avoided

Record the iPad style template explicitly for the same reason as iPhone: resume must NOT guess it from `final-ipad/01` — the first iPad final may have been re-generated since the later iPad screenshots were styled against it.

This keeps iPad resumable across conversations the same way iPhone is.

## When a Step Fails

- **A single-version subsequent generation fails**: retry that one call once. If it still fails, surface the `enhance.py` stderr (`finish_reason` / safety details) and stop.
- **One of several parallel enhance calls fails** (first-screenshot 3× or a fan-out round): retry that one call once. If it still fails, proceed with the surviving versions and tell the user.
- **All parallel calls in a round fail**: surface the `enhance.py` stderr to the user (it contains the `finish_reason` / safety details) and stop.

## Offer iPad Localization

After the iPad **English** showcase is shown and the user is happy with the iPad set, **explicitly offer** to localize the iPad set (only now — iPad localization is not offered before the iPad English set is approved):

```
Your iPad set is complete. Want me to also localize it into other languages?

This translates each iPad headline per locale. If your app's UI supports the language,
you capture localized iPad simulator screenshots and each shot is rebuilt around the
real localized UI; otherwise only the headline is swapped and the on-screen UI stays
English.

Reply "yes" to start, or "no" / "later" to stop here. Memory persists, so you can always
come back and localize later.
```

If the user accepts, Read `references/localization.md` (relative to the skill directory) and follow it, targeting the iPad set (`--aspect-ratio "3:4"`, resize-only post-processing, outputs under `screenshots/final-ipad/<locale>/`).
