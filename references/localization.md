# Localization (Optional, After a Set Is Approved)

This phase produces localized versions of an already-approved screenshot set. There are **two flows**, chosen per locale in Step 2:

- **Flow A — Localized raw capture (primary).** The app's UI supports the target language, so the user captures real simulator screenshots of the app running in that language. Every label, number format (decimal comma "9,8 GB"), and date is genuine iOS rendering — the AI never translates UI. The AI only repaints the decorative shell (device frame, background, breakout styling) around the faithful raw.
- **Flow B — Headline swap (fallback).** The app's UI does NOT support the target language (or the user can't capture raws). Only the marketing headline is replaced on the approved English final; the on-screen UI intentionally stays English.

Flow A gives strictly better screenshots and costs the **same number of paid calls** — its only extra cost is the user's capture effort. Default to Flow A whenever the app supports the language.

It applies to whichever set the user chose to localize:
- **iPhone** — offered after the iPhone English showcase is approved. Uses `--aspect-ratio "9:16"`, side-crop + resize post-processing, English finals at `screenshots/final/`, localized outputs at `screenshots/final/<locale>/`.
- **iPad** — offered only after the iPad English set is approved (see the offer at the end of `references/ipad-extension.md`). Uses `--aspect-ratio "3:4"`, resize-only post-processing, English finals at `screenshots/final-ipad/`, localized outputs at `screenshots/final-ipad/<locale>/`.

Throughout, `SKILL_DIR` is the skill's base directory — the path shown when the skill loads ("Base directory for this skill: ..."), falling back to `$HOME/.claude/skills/aso-appstore-screenshots`. Use the same image backend the set being localized was generated with (the `Image backend:` line in `aso_generated_screenshots.md`) and pass it as `--backend` on every `enhance.py` call — localized screenshots must match their English originals, and a different backend renders differently. Verify its prerequisite before any paid call: gemini needs `GEMINI_API_KEY` or `GOOGLE_API_KEY`; codex needs the `codex` CLI installed and signed in, no key.

## Step 1: Choose and Confirm Locales

Ask the user which languages they want to target. Map each to its App Store Connect locale code, for example:

| Language | App Store Connect code |
|----------|------------------------|
| English (US) | en-US |
| German | de-DE |
| French | fr-FR |
| Spanish (Spain) | es-ES |
| Spanish (Mexico) | es-MX |
| Portuguese (Brazil) | pt-BR |
| Japanese | ja |
| Simplified Chinese | zh-Hans |

Present the mapped list back to the user and confirm it before doing anything else. The English set already at `final/` (or `final-ipad/`) stays as-is and is not re-generated.

## Step 2: Per-Locale UI Support Check (Picks the Flow)

Ask ONE question, per locale, before anything else:

```
Does your app's UI actually run in these languages? Most apps localize UI these days,
so I'll assume "yes" unless you say otherwise — but partial localization is common
(third-party data sources, server-driven strings, etc.).

For each locale, answer: fully localized / not localized.
```

- **Fully localized** → **Flow A** for that locale.
- **Not localized** → **Flow B** for that locale, with this warning stated up front: the on-screen UI will remain English under the localized headline, and Apple/users will see that mismatch. If the model spontaneously "translates" UI text anyway, that output must be rejected — invented translations that don't match the shipped app are worse than honest English.

Mixed sets are fine (e.g. de-DE via Flow A, th-TH via Flow B). Record the per-locale flow choice in memory (Step 7).

If the user is unsure for a locale, have them switch the app to that language once in the simulator and look — it takes a minute and prevents generating a whole locale on the wrong assumption.

## Step 3: Draft and Confirm Translations (BEFORE Any Paid Calls)

Both flows need translated **marketing headlines** (this is copy the skill authors — distinct from the app's own UI strings). For each locale, draft a translation of every benefit headline — both the **verb line** and the **descriptor line** separately, preserving the ACTION VERB + DESCRIPTOR structure.

Present **all** translations in a single table for the user to confirm **before any paid image calls**:

```
Benefit 1 — EN: TRACK / TRADING CARD PRICES
  de-DE: VERFOLGE / SAMMELKARTEN-PREISE
  fr-FR: SUIVEZ / LES PRIX DES CARTES
Benefit 2 — EN: SEARCH / ANY CARD
  de-DE: ...
```

**Headline length matters.** If a translation is much longer than the English (common for German/French), warn the user and suggest a tighter variant — long headlines shrink to fit the safe area and can look weak. Get explicit confirmation of the final wording per locale before generating.

**CJK locales (ja / ko / zh-Hans / zh-Hant):** the compose scripts render CJK headlines directly — `compose_common.py` falls back to a heavy-weight system CJK font when the headline contains CJK characters (bundled Inter has no CJK glyphs). No AI repainting of headlines is needed. Still visually QC the CJK scaffolds before enhancing: confirm the glyphs render (no tofu boxes) and line breaks look sane.

Save the confirmed locale list and translation table to memory now (see Step 7) so this survives an interruption.

## Flow A: Localized Raw Capture (Primary)

### A1: Capture Real Localized Raws

The user must capture the **same screens as the approved English pairings** (from `aso_screenshot_pairings.md` / `aso_ipad_pairings.md`), with the app running in the target language. Give them this recipe (per locale — a dedicated simulator clone keeps the base device clean):

```bash
# One-time per locale: clone a simulator and switch it to the target language
xcrun simctl clone "<base device name or UDID>" "ASO-de-DE"
xcrun simctl boot "ASO-de-DE"
xcrun simctl spawn "ASO-de-DE" defaults write .GlobalPreferences AppleLanguages -array "de-DE"
xcrun simctl spawn "ASO-de-DE" defaults write .GlobalPreferences AppleLocale -string "de_DE"
xcrun simctl shutdown "ASO-de-DE" && xcrun simctl boot "ASO-de-DE"

# Clean status bar (same as the English set)
xcrun simctl status_bar "ASO-de-DE" override --time "9:41" --batteryState charged --batteryLevel 100 --cellularBars 4 --wifiBars 3

# Install + launch the app, navigate to each paired screen, capture:
xcrun simctl io "ASO-de-DE" screenshot raw-de-DE-01.png
```

(Quick alternative when a full device-locale switch is overkill: launch just the app localized via `xcrun simctl launch "<device>" <bundle-id> -AppleLanguages "(de)" -AppleLocale "de_DE"` — but the clone approach is more faithful for system-rendered dates/formats.)

**Offer to generate a small capture-helper script** in the user's project that automates the clone/locale/boot/status-bar part for all confirmed locales — in-app navigation stays manual. If the user already has UI-test-driven screenshot automation (fastlane snapshot etc.), suggest reusing it with per-locale runs instead.

Ask for the raws organised per locale (e.g. `simulator-screenshots/de-DE/`), mirroring however the English raws were provided.

### A2: Verify the Raws (Free — Before Any Paid Call)

Read every localized raw and check:
- It shows the **same screen** as its English counterpart (same pairing → same benefit).
- The UI is actually in the target language — no half-English screens (a common sign of partial localization; if found, that locale may need to drop to Flow B or the user fixes the app first).
- Locale formatting is genuine and preserved (decimal commas, date formats, digit grouping).
- Status bar is clean and consistent with the English set.

Flag problems now, exactly like the English Screenshot Pairing phase — a Retake here costs nothing; a bad raw enhanced is a wasted paid call.

### A3: Compose Per-Locale Scaffolds

For each locale, run the same compose script as the parent set (`compose.py` for iPhone, `compose_ipad.py` for iPad) with the **translated verb/desc**, the **localized raw**, and the **same brand colour**. Batch all scaffolds for a locale into a single Bash call (same `&&`-chaining pattern as the main skill), starting the chain with `mkdir -p` for every working directory — both the compose scripts and `enhance.py` require the output directory to exist. Output to `screenshots/<locale>/0N-[benefit-slug]/scaffold.png` (iPhone) or `screenshots/ipad/<locale>/0N-[benefit-slug]/scaffold.png` (iPad).

Read each scaffold and verify (headline wording, no text/device overlap, correct background) before spending money — same rule as the main pipeline.

### A4: Enhance — ONE Style-Locked Call per Screenshot

One `enhance.py` call per screenshot (no 3× fan-out — the style is already decided; iterate only on rejection). Style-locking works per locale:

- **Screenshot 01 of a locale**: pass the scaffold (FIRST image) + the **approved English final 01** (SECOND image, style template).
- **Screenshots 02..N of a locale**: pass the scaffold (FIRST image) + **that locale's own generated, self-checked 01** (SECOND image) — so each locale's set is internally consistent. During a batch run the locale's 01 is not user-approved yet (the user reviews the whole locale at once in Step 4); if the user later rejects the locale's 01, regenerate 01 first and then re-run 02..N against the new 01 — never keep screenshots styled against a rejected one.

Prompt template:

```
You are localizing an App Store screenshot set into [LANGUAGE]. Create the [locale] version of this screenshot.

TWO REFERENCE IMAGES:
- FIRST image: The SCAFFOLD — the localized headline text and the REAL localized app screenshot on the device screen. The headline wording and everything shown on the device screen are already correct and FINAL.
- SECOND image: The STYLE TEMPLATE — an approved screenshot from this set. Match its visual style EXACTLY: same device frame rendering, same text treatment, same background, same breakout styling, same level of polish.

REQUIREMENTS:
- Do NOT change ANYTHING inside the device screen. The app screenshot is a genuine capture of the app running in [LANGUAGE] — every label, number format, and date is intentionally correct for that locale. Do NOT "fix" or convert decimal commas, digit grouping, or date formats toward English conventions. Do NOT translate, retouch, or re-render any on-screen text.
- Keep the headline text exactly as written in the scaffold — same wording, position, and approximate size.
- If the style template has a breakout element: recreate the SAME breakout treatment using the corresponding panel from THIS screenshot's localized screen content (the breakout must show the [LANGUAGE] content, not the template's English content). If the template has no breakout, add none.
- Match the style template's background exactly — clean, solid brand colour. No glows, gradients, or patterns.

No watermarks, no extra text, no app store UI chrome.
```

Pass `--aspect-ratio "9:16"` (iPhone) or `--aspect-ratio "3:4"` (iPad) and the set's `--backend` on every call.

### A5: Post-Process and Self-Check

Run the **same post-processing as the parent pipeline** immediately, before showing anything:
- **iPhone**: side-crop + resize (the Step 3 crop/resize loop from SKILL.md — `TARGET_W=1290 TARGET_H=2796` by default).
- **iPad**: resize only (the resize loop from `references/ipad-extension.md` — `TARGET_W=2064 TARGET_H=2752` by default).

Then Read each result and self-check: headline intact and correctly worded, device-screen content pixel-faithful to the raw (spot-check the locale formatting the prompt guarded), style matches the template. One automatic retry per screenshot on obvious breakage, then show the user what you have.

## Flow B: Headline Swap (Fallback — App UI Not Localized)

For each screenshot: **ONE `enhance.py` call**. The input image is the **approved English final**. The prompt swaps only the headline:

```
Take this finished App Store screenshot and produce a localized version. Replace ONLY the
headline text with the following translation, keeping the exact same font, weight, size,
colour, alignment, and position as the original headline:

  Line 1 (verb): [TRANSLATED VERB]
  Line 2 (descriptor): [TRANSLATED DESCRIPTOR]

Keep EVERYTHING ELSE exactly as-is: the device frame and its rendering, the app screenshot
shown on the screen, the background colour, and any breakout or secondary elements. The
on-screen app UI must remain in English — do NOT translate, alter, or re-render any text
inside the device screen or in breakout elements. Do not move, restyle, or re-imagine
anything except the headline wording. Do not add or remove any elements. No watermarks,
no extra text, no app store UI chrome.
```

Create the locale output directory before the first call (`enhance.py` dies if it doesn't exist), e.g.:

```bash
mkdir -p screenshots/final/de-DE
uv run "$SKILL_DIR/enhance.py" \
  --prompt-file screenshots/final/de-DE/01-[benefit-slug].prompt.txt \
  --aspect-ratio "9:16" \
  --image screenshots/final/01-[benefit-slug].jpg \
  --output screenshots/final/de-DE/01-[benefit-slug].raw.jpg
```

Pass `--aspect-ratio` and `--backend` as in Flow A, then run the same post-processing.

**QC every Flow B output for spontaneous UI translation**: image models sometimes "helpfully" translate on-screen text despite instructions. Those translations are invented and will not match the shipped app — reject such outputs and retry with the guard reinforced.

## Step 4: Cost Checkpoint — One Locale First

Do **ONE locale end-to-end first** (all its screenshots — including capture, for Flow A), show the user the results, and get approval that the approach, translation placement, and quality look right. Only then batch the remaining locales. Tell the user the paid-call count up front: roughly N screenshots × M locales enhance calls (both flows cost the same per screenshot; Flow A adds capture effort, not API cost).

## Step 5: Output Convention

```
screenshots/
  final/                      ← English iPhone set (unchanged)
    01-[benefit-slug].jpg
  final/de-DE/                ← localized iPhone set
    01-[benefit-slug].jpg
  final/fr-FR/
    01-[benefit-slug].jpg
  final-ipad/                 ← English iPad set (unchanged)
    01-[benefit-slug].jpg
  final-ipad/de-DE/           ← localized iPad set
    01-[benefit-slug].jpg
```

The English set stays at the `final/` (or `final-ipad/`) root. Each locale gets its own subdirectory named by App Store Connect locale code. Tell the user which locale directory maps to which App Store Connect localization slot.

## Step 6: Approve per Locale

Show each locale's post-processed set to the user, iterate on rejects (single calls, style-locked as in A4), and copy approved outputs to the locale's `final/<locale>/` directory (`mkdir -p` it first).

## Step 7: Save Localization State to Memory

Save per-locale status **incrementally** to the localization state file (`aso_localization.md`). Track:

- **Locales confirmed** — the mapped list from Step 1
- **Per-locale flow** — Flow A (localized raws) or Flow B (headline swap), and why
- **Translations table** — per benefit, per locale, the confirmed verb + descriptor
- **Which set** is being localized (iPhone / iPad) and the source finals path
- **Per-locale raw paths** (Flow A) — where the localized simulator captures live
- **Per-locale, per-screenshot status** — pending / generated / approved, and the output path

Update after each locale (and ideally each screenshot) so an interrupted run resumes from the last completed locale rather than restarting.

RECALL awareness: the main skill's RECALL checklist includes a localization line and its status summary shows localization progress. On resume, verify the localized output paths recorded here still exist on disk; treat missing files as that locale needing redo.
