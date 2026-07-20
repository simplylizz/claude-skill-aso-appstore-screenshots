# Localization (Optional, After a Set Is Approved)

This phase produces localized versions of an already-approved screenshot set by **translating headlines and re-rendering the pages** — there are **zero paid image calls**. N locales × M shots takes minutes and costs $0.

There is **one flow**. For each locale you translate the marketing headlines, set `<html lang>` on the pages, and re-render. The only per-locale variable is the **raws source**:

- **App UI is localized** → the user captures real simulator screenshots of the app running in that language (every label, decimal comma "9,8 GB", and date is genuine iOS rendering), and the localized pages point at those localized raws.
- **App UI is not localized** (or the user can't capture raws) → keep the **English raws**; only the headline is translated. The on-screen UI intentionally stays English.

Either way, the headline is real vendored-font text rendered by the browser — never an AI repaint — so there is no style-locking, no "styled against" bookkeeping, and no per-shot enhance budget.

It applies to whichever set the user chose to localize:
- **iPhone** — offered after the iPhone English showcase is approved. Design dir `screenshots/design/`, viewport `1290 2796`, English finals at `screenshots/final/`, localized outputs at `screenshots/final/<locale>/`.
- **iPad** — offered only after the iPad English set is approved (see the offer at the end of `references/ipad-extension.md`). Design dir `screenshots/design/ipad/`, viewport `2064 2752`, English finals at `screenshots/final/ipad/`, localized outputs at `screenshots/final/ipad/<locale>/`.

Throughout, `SKILL_DIR` is the skill's base directory — the path shown when the skill loads ("Base directory for this skill: ..."), falling back to `$HOME/.claude/skills/aso-appstore-screenshots`.

## Prerequisites

`agent-browser` must be installed (it already is if the English set was rendered this pipeline). Confirm once:

```bash
command -v agent-browser >/dev/null && echo "agent-browser: available" || echo "agent-browser: MISSING"
```

If missing, show `npm install -g agent-browser` and stop. No image-model key is needed — localization is pure translate + re-render.

## Step 1: Choose and Confirm Locales

Ask the user which languages they want to target. Map each to its App Store Connect locale code **and** the HTML `lang` attribute you'll set on the pages, for example:

| Language | App Store Connect code | HTML `lang` |
|----------|------------------------|-------------|
| English (US) | en-US | en |
| German | de-DE | de |
| French | fr-FR | fr |
| Spanish (Spain) | es-ES | es |
| Portuguese (Brazil) | pt-BR | pt-BR |
| Japanese | ja | ja |
| Korean | ko | ko |
| Simplified Chinese | zh-Hans | zh-Hans |
| Traditional Chinese | zh-Hant | zh-Hant |

Present the mapped list back to the user and confirm it before doing anything else. The English set already at `final/` (or `final/ipad/`) stays as-is and is not re-rendered.

## Step 2: Per-Locale UI Support Check (Picks the Raws Source)

Ask ONE question, per locale, before anything else:

```
Does your app's UI actually run in these languages? Most apps localize UI these days,
so I'll assume "yes" unless you say otherwise — but partial localization is common
(third-party data sources, server-driven strings, etc.).

For each locale, answer: fully localized / not localized.
```

- **Fully localized** → capture localized raws for that locale (Step 4A).
- **Not localized** → reuse the **English raws** with a translated headline, and state this up front: the on-screen UI will remain English under the localized headline, and Apple/users will see that mismatch. That's honest and expected; do not fake UI translations.

Mixed sets are fine (e.g. de-DE with localized raws, th-TH with English raws). Record the per-locale raws source in memory (Step 6).

If the user is unsure for a locale, have them switch the app to that language once in the simulator and look — it takes a minute and prevents localizing a whole locale on the wrong assumption.

## Step 3: Draft and Confirm Translations (Per-Locale Table)

Translate the **marketing headlines** — this is copy the skill authors, distinct from the app's own UI strings. For each locale, translate every benefit headline, keeping the **verb line** and **descriptor line** separate so the ACTION VERB + DESCRIPTOR structure survives.

Present **all** translations in a single table for the user to confirm before rendering anything:

```
Benefit 1 — EN: TRACK / TRADING CARD PRICES
  de-DE: VERFOLGE / SAMMELKARTEN-PREISE
  fr-FR: SUIVEZ / LES PRIX DES CARTES
Benefit 2 — EN: SEARCH / ANY CARD
  de-DE: ...
```

**Headline length matters.** German and French descriptors run long. The type scale lives in `set.css` as custom properties, uniform *within a device+locale set* (not one point size across all languages) — so if one locale's headline overflows or crowds the ≥ ~6% edge margin, fix it with a **locale-scoped override in the same shared `set.css`**, not a per-shot override and not a `set.css` fork. Append a `body:lang(<locale>)` block **after** the `body.iphone` / `body.ipad` device token blocks so it wins the cascade over the device block (a `html:lang()` selector would lose to the device block's direct declaration on `body`):

```css
body:lang(de) { --verb-size: 150px; --desc-size: 76px; }
```

English and every other locale are untouched — only `:lang(de)` pages pick up the smaller scale. The alternative fix is agreeing a tighter wording with the user. **Never** add a per-shot size override — that breaks the "same size on every screenshot" invariant. Get explicit confirmation of the final wording per locale before rendering.

Save the confirmed locale list, raws source, and translation table to memory now (Step 6) so this survives an interruption.

## Step 4A: Capture Localized Raws (Localized-UI Locales Only)

Skip this for locales reusing English raws. For localized-UI locales, the user captures the **same screens as the approved English pairings** (from `aso_screenshot_pairings.md` / `aso_ipad_pairings.md`), with the app running in the target language. Give them this recipe (per locale — a dedicated simulator clone keeps the base device clean):

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

**Verify the raws (free — before rendering):** Read every localized raw and check it shows the **same screen** as its English counterpart, the UI is actually in the target language (no half-English screens — a sign of partial localization; that locale may need to fall back to English raws or the user fixes the app first), locale formatting is genuine (decimal commas, date formats, digit grouping), and the status bar is clean and consistent with the English set. A Retake here costs nothing.

**Preflight the dimensions:** run `sips -g pixelWidth -g pixelHeight` on every localized raw. They must be identical portrait dimensions and match the English raws' dimensions (iPhone 1290×2796 / iPad 2064×2752, or whatever uniform non-canonical size the English set used with its `--raw-w` / `--screen-scale`). A mixed or mismatched size means a recapture, not a per-shot fudge.

**Vendor the localized raws:** copy the verified captures into a per-locale design raw dir — `screenshots/design/raw/<locale>/` (iPad: `screenshots/design/ipad/raw/<locale>/`) — with URL-safe kebab-case names, and have the locale pages reference these vendored copies relatively. Do this so final renders load only in-repo assets and the locale page's `src` is a stable relative path.

## Step 4B: Vendor CJK Webfonts (ja / ko / zh Only)

The bundled Inter has no CJK glyphs, and an unqualified system fallback can resolve to a mid-weight face (violating the heavy/black headline look) — and without a `lang` attribute Chromium can render Japanese kanji with Chinese glyph forms (Han unification). So for any Japanese, Korean, or Chinese locale, vendor a matching **heavy CJK webfont** into the shared design assets before rendering:

- Japanese → **Noto Sans JP Black** — static file `NotoSansJP-Black.otf` (weight 900)
- Korean → **Noto Sans KR Black** — static file `NotoSansKR-Black.otf` (weight 900)
- Simplified Chinese → **Noto Sans SC Black** — static file `NotoSansSC-Black.otf` (weight 900); Traditional Chinese → **Noto Sans TC Black** — static file `NotoSansTC-Black.otf` (weight 900)

Fetch the exact static (non-variable) weight-900 file per target script from an official source — the `notofonts/noto-cjk` GitHub releases (the *Sans* release ships the per-language `NotoSansXX-Black.otf` statics) or the fonts.google.com "Download family" bundle (unzip and take the `Black` static, not the variable font). Do **not** wire in a variable `.ttf` and assume it exposes 900. Copy the file into `screenshots/design/assets/` — the one shared font tree; the iPad `set.css` reaches it with `../assets/…` urls, so both device sets pick it up from a single copy — so final renders load **zero external resources**, and **verify the downloaded file actually provides weight 900 for the target script before rendering** (open it / check the family + weight, or just render one shot and Read it — a mid-weight substitute reads as not-black). The fail-closed readiness check now compares the `.verb` computed family against `document.fonts.check`, so a missing or silently-fallback CJK face trips `body.render-error` at render time rather than passing as tofu — but confirm the weight yourself, since a present-but-wrong-weight face still passes the check. Then add a **set-wide** rule to the set's `set.css` — a `@font-face` for each vendored CJK face plus a `:lang()`-scoped headline-font override so a page that declares `<html lang="ja">` picks up the Japanese face while Latin pages keep Inter:

```css
@font-face {
  font-family: "Noto Sans JP";
  src: url("assets/NotoSansJP-Black.otf") format("opentype"); /* iPad set.css: ../assets/… */
  font-weight: 900;
}
:lang(ja) .headline { font-family: "Noto Sans JP", "Inter Display", sans-serif; }
```

Keep this in `set.css` (centralized, set-wide) — never in a per-shot page. Latin locales are untouched.

## Step 5: Build Per-Locale Pages and Render

For each locale, create a locale page directory beside the English design and render into the locale's finals directory.

1. **Copy the English design pages** into a per-locale subdir — `screenshots/design/<locale>/0N-<benefit-slug>.html` for iPhone, `screenshots/design/ipad/<locale>/0N-<benefit-slug>.html` for iPad. In each copied page:
   - set `<html lang="<locale lang>">` (from the Step 1 table);
   - replace the headline verb/descriptor text with the confirmed translation;
   - point the device `<img class="screen">` at the **vendored localized raw** (`screenshots/design/raw/<locale>/…`) for localized-UI locales, or at the **vendored English raw** for English-UI locales. The locale page sits one directory deeper than the English page, so its raw src gains one `../` — `../raw/<locale>/<name>.png` (English fallback: `../raw/<name>.png`; the iPad tree uses the same relative form under `design/ipad/`) — the same one-level adjustment the `../set.css` link gets below;
   - **update the breakout too, if the page has one.** The breakout holds a **second `<img>` of the same raw** — repoint its `src` to the same vendored raw as `img.screen`. Critically, translated UI moves and resizes panels, so the English `--crop-x/y/w/h` values are **not** valid against a localized raw: re-measure the panel bounds against the localized raw (same Pillow background→panel sampling + 8–12px inset as the English flow), re-derive the crop, and re-run the 1:1 breakout QA **per locale**. If you can't measure a locale-specific crop yet, **drop the breakout for that locale** — never ship an unverified English crop over a localized raw;
   - link the **same shared `set.css`** as the English set (adjust the relative path for the extra subdir, e.g. `../set.css`) — the type scale, frame, background, CJK `:lang()` rule, and any `body:lang(<locale>)` type override (Step 3) all come from there. Do **not** fork `set.css` per locale.
   - keep the readiness include, adjusting its relative path the same way as `set.css`: `<script src="../ready.js"></script>` (the vendored gate sits next to `set.css`, one directory up from the locale pages). It is **fail-closed**: `<body>` gets `class="ready"` only when fonts resolve, every `<img>` decodes (with the raw copies matching the `--raw-w` contract), the computed `.verb` headline face passes `document.fonts.check`, the `set.css` custom properties and background resolve, and the headline fits; on any failure it sets `body.render-error` + `document.body.dataset.renderError`. On a `lang="ja"` page this checks the **CJK** face — and a CJK headline whose computed face is still the Latin one (a forgotten `<html lang>` or missing `:lang()` rule) fails the gate too, instead of passing as tofu.
2. **Render sequentially** in one agent-browser session (set the viewport once for the whole locale batch — `1290 2796` for iPhone, `2064 2752` for iPad):

   ```bash
   agent-browser set viewport 1290 2796        # or 2064 2752 for iPad
   agent-browser open "file://$PWD/screenshots/design/de-DE/01-<benefit-slug>.html"
   agent-browser wait "body.ready"
   agent-browser screenshot screenshots/design/preview/de-DE-01-<benefit-slug>.png
   # …QA loop passes AND the user approves, then promote:
   cp screenshots/design/preview/de-DE-01-<benefit-slug>.png screenshots/final/de-DE/01-<benefit-slug>.png
   # …repeat for each shot in this locale…
   agent-browser close                         # when the locale batch is done
   ```

   `mkdir -p screenshots/final/de-DE` (or `screenshots/final/ipad/de-DE`) before the first promotion.

   **Staging — every render goes to the working path first; approval promotes it.** One unconditional rule (same as the English sets): every localized render writes to `screenshots/design/preview/` (iPad: `screenshots/design/ipad/preview/`, locale-prefixed names so locales don't collide) and is `cp`-promoted to `screenshots/final/<locale>/` only after the QA loop passes and the user approves. The path never depends on recalled approval state, and a draft can never overwrite an approved localized final.

3. **QA loop per shot** (same as the English pipeline, $0 per iteration): if `agent-browser wait "body.ready"` times out, the fail-closed script has flagged a problem — read `body.render-error` / `document.body.dataset.renderError` for the reason (a tofu/fallback-face CJK failure now trips this, not just the visual read) and fix it before re-rendering. Then Read the PNG and check the **translated** headline is intact and correctly worded, keeps ≥ ~6% margin from every edge (watch long German/French descriptors — fix with the locale-scoped `body:lang()` override per Step 3, never per-shot), the CJK glyphs render with the vendored heavy face (no tofu boxes, mid-weight substitution, or bad line breaks), the frame and background match the English set, any breakout uses the re-measured locale crop and passes its 1:1 check, and — for localized-UI locales — the on-screen content is the genuine localized capture (spot-check a decimal comma / date the app renders). Verify exact dimensions with `sips -g pixelWidth -g pixelHeight` (1290×2796 iPhone / 2064×2752 iPad). Fix in CSS or the page, re-render, re-check. Only clean renders are shown.

**Do ONE locale end-to-end first**, show the user, and confirm the translation placement and quality look right before batching the rest — a quick sanity gate, not a cost gate (there is no cost). Then render the remaining locales the same way.

## Step 6: Output Convention

```
screenshots/
  design/
    set.css                     ← shared design system (owns type scale, frame, CJK :lang + body:lang overrides)
    0N-*.html                   ← English iPhone pages
    de-DE/0N-*.html             ← localized iPhone pages (translated headlines, vendored raws)
    raw/                        ← vendored English raws
      de-DE/                    ← vendored localized raws (URL-safe names, one dir per locale)
    ipad/
      set.css                   ← iPad design system
      0N-*.html                 ← English iPad pages
      de-DE/0N-*.html           ← localized iPad pages
      raw/de-DE/                ← vendored localized iPad raws
    assets/                     ← vendored fonts incl. Noto Sans JP/KR/SC Black for CJK locales
  final/
    0N-*.png                    ← English iPhone set (unchanged)
    de-DE/0N-*.png              ← localized iPhone set
    fr-FR/0N-*.png
    ipad/
      0N-*.png                  ← English iPad set (unchanged)
      de-DE/0N-*.png            ← localized iPad set
```

The English set stays at the `final/` (or `final/ipad/`) root. Each locale gets its own subdirectory named by App Store Connect locale code. Tell the user which locale directory maps to which App Store Connect localization slot.

## Step 7: Save Localization State to Memory

Save per-locale status **incrementally** to the localization state file (`aso_localization.md`). Track:

- **Locales confirmed** — the mapped list from Step 1 (App Store Connect code + HTML `lang`)
- **Translations table** — per benefit, per locale, the confirmed verb + descriptor
- **Which set** is being localized (iPhone / iPad) and the source design dir + finals path
- **Per-locale raws source** — localized simulator raws (and where they live) vs. English fallback raws
- **Per-locale, per-shot render status** — pending / rendered / approved, and the output path

There is no Flow A/B choice and no "styled against" record. Update after each locale (and ideally each shot) so an interrupted run resumes from the last completed locale rather than restarting.

RECALL awareness: the main skill's RECALL checklist includes a localization line and its status summary shows localization progress. On resume, verify the localized output paths recorded here still exist on disk; treat missing files as that locale needing a re-render (free).
