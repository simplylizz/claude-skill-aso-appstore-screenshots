# Localization (Optional, After a Set Is Approved)

This phase translates an already-approved screenshot set into other languages by replacing only the headline text on each final and regenerating it. Everything else — device frame, app screenshot content, background, breakouts — stays exactly as-is.

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

## Step 2: Draft and Confirm Translations (BEFORE Any Paid Calls)

For each locale, draft a translation of every benefit headline — both the **verb line** and the **descriptor line** separately, preserving the ACTION VERB + DESCRIPTOR structure.

Present **all** translations in a single table for the user to confirm **before any paid image calls**:

```
Benefit 1 — EN: TRACK / TRADING CARD PRICES
  de-DE: VERFOLGE / SAMMELKARTEN-PREISE
  fr-FR: SUIVEZ / LES PRIX DES CARTES
Benefit 2 — EN: SEARCH / ANY CARD
  de-DE: ...
```

**Headline length matters.** If a translation is much longer than the English (common for German/French), warn the user and suggest a tighter variant — long headlines shrink to fit the safe area and can look weak. Get explicit confirmation of the final wording per locale before generating.

Save the confirmed locale list and translation table to memory now (see Step 6) so this survives an interruption.

## Step 3: Generate Localized Screenshots (One enhance Call per Screenshot per Locale)

For each locale, for each screenshot: make **ONE `enhance.py` call**. The input image is the **approved English final** for that screenshot. The prompt instructs Gemini to swap only the headline text:

```
Take this finished App Store screenshot and produce a localized version. Replace ONLY the
headline text with the following translation, keeping the exact same font, weight, size,
colour, alignment, and position as the original headline:

  Line 1 (verb): [TRANSLATED VERB]
  Line 2 (descriptor): [TRANSLATED DESCRIPTOR]

Keep EVERYTHING ELSE exactly as-is: the device frame and its rendering, the app screenshot
shown on the screen, the background colour, and any breakout or secondary elements. Do not
move, restyle, re-render, or re-imagine anything except the headline wording. Do not add or
remove any elements. No watermarks, no extra text, no app store UI chrome.
```

Pass `--aspect-ratio "9:16"` for iPhone / `--aspect-ratio "3:4"` for iPad. Example (iPhone):

```bash
SKILL_DIR="$HOME/.claude/skills/aso-appstore-screenshots"
mkdir -p screenshots/final/de-DE   # create the locale directory first (enhance.py requires the output dir to exist)
uv run "$SKILL_DIR/enhance.py" \
  --prompt-file screenshots/final/de-DE/01-[benefit-slug].prompt.txt \
  --aspect-ratio "9:16" \
  --image screenshots/final/01-[benefit-slug].jpg \
  --output screenshots/final/de-DE/01-[benefit-slug].raw.jpg
```

Then run the **same post-processing as the parent pipeline**:
- **iPhone**: side-crop + resize (the Step 3 crop/resize loop from SKILL.md — `TARGET_W=1290 TARGET_H=2796` by default).
- **iPad**: resize only (the Step 6 resize loop from `references/ipad-extension.md` — `TARGET_W=2064 TARGET_H=2752` by default).

Write the post-processed result to the final localized path (Step 5) and Read it to verify the headline is correct and everything else is unchanged.

## Step 4: Cost Checkpoint — One Locale First

Do **ONE locale end-to-end first** (all its screenshots), show the user the results, and get approval that the translation placement and quality look right. Only then batch the remaining locales. This avoids spending on every locale before confirming the approach works. Tell the user the paid-call count up front: roughly N screenshots × M locales enhance calls.

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

## Step 6: Save Localization State to Memory

Save per-locale status **incrementally** to the localization state file (`aso_localization.md`). Track:

- **Locales confirmed** — the mapped list from Step 1
- **Translations table** — per benefit, per locale, the confirmed verb + descriptor
- **Which set** is being localized (iPhone / iPad) and the source finals path
- **Per-locale, per-screenshot status** — pending / generated / approved, and the output path

Update after each locale (and ideally each screenshot) so an interrupted run resumes from the last completed locale rather than restarting.

RECALL awareness: the main skill's RECALL checklist includes a localization line and its status summary shows localization progress. On resume, verify the localized output paths recorded here still exist on disk; treat missing files as that locale needing redo.
