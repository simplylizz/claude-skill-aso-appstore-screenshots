#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pillow",
# ]
# ///
"""
Shared compositing logic for the App Store screenshot composers.

`compose.py` (iPhone) and `compose_ipad.py` (iPad) are thin CLI wrappers that
hold only their device-specific constants in a `ComposeConfig` and delegate all
drawing/compositing to this module. Kept dependency-free beyond Pillow so it
imports cleanly under `uv run /path/to/compose.py` from any working directory
(the invoked script's own directory is on sys.path, so sibling import works).
"""

import functools
import os
import string
import sys
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

# Default headline font, resolved relative to this file (== repo root / assets).
# Bundled Inter is Latin-only — it has NO CJK glyphs, so CJK headlines fall back
# to a heavy-weight system font (see `font_for` / `_resolve_cjk_face` below).
FONT_PATH = os.path.join(
    os.path.dirname(__file__), "assets", "fonts", "InterDisplay-Black.otf"
)

# ── CJK detection + system-font fallback ────────────────────────────────
# Inter (the bundled headline font) covers only Latin, so ja/ko/zh headlines
# would render as tofu. When a headline line contains CJK characters we swap in
# a heavy-weight CJK-capable macOS system font for that line. Latin-only text is
# untouched — behaviour there is byte-for-byte identical to before.


def _is_cjk_letter(cp):
    return (
        0x3400 <= cp <= 0x4DBF   # CJK Unified Ideographs Extension A
        or 0x4E00 <= cp <= 0x9FFF   # CJK Unified Ideographs (Han)
        or 0xF900 <= cp <= 0xFAFF   # CJK Compatibility Ideographs
        or 0x3040 <= cp <= 0x309F   # Hiragana
        or 0x30A0 <= cp <= 0x30FF   # Katakana
        or 0x31F0 <= cp <= 0x31FF   # Katakana Phonetic Extensions
        or 0xFF66 <= cp <= 0xFF9D   # Halfwidth Katakana
        or 0xAC00 <= cp <= 0xD7A3   # Hangul Syllables
        or 0x1100 <= cp <= 0x11FF   # Hangul Jamo
        or 0x3130 <= cp <= 0x318F   # Hangul Compatibility Jamo
        or 0xA960 <= cp <= 0xA97F   # Hangul Jamo Extended-A
        or 0xD7B0 <= cp <= 0xD7FF   # Hangul Jamo Extended-B
    )


def contains_cjk(text):
    """True if the text contains CJK *letters* (Han / kana / hangul) that Inter
    cannot render. Deliberately excludes shared CJK punctuation and fullwidth
    forms: a Latin headline with a stray fullwidth '！' must keep Latin
    word-wrapping and the Inter face."""
    return any(_is_cjk_letter(ord(c)) for c in text)


def _cjk_script(text):
    """Classify text into a script family ('ko' / 'ja' / 'zh') for font choice.

    Hangul and kana are unambiguous; a Han-only string defaults to 'zh' (the
    shared ideographs render correctly in a Chinese face regardless — callers
    that know better pass an explicit script, see `font_for`). Returns None
    when the text has no CJK letters at all.
    """
    if any(
        0xAC00 <= ord(c) <= 0xD7A3
        or 0x1100 <= ord(c) <= 0x11FF
        or 0x3130 <= ord(c) <= 0x318F
        or 0xA960 <= ord(c) <= 0xA97F
        or 0xD7B0 <= ord(c) <= 0xD7FF
        for c in text
    ):
        return "ko"
    if any(
        0x3040 <= ord(c) <= 0x309F
        or 0x30A0 <= ord(c) <= 0x30FF
        or 0x31F0 <= ord(c) <= 0x31FF
        or 0xFF66 <= ord(c) <= 0xFF9D
        for c in text
    ):
        return "ja"
    if any(
        0x3400 <= ord(c) <= 0x4DBF
        or 0x4E00 <= ord(c) <= 0x9FFF
        or 0xF900 <= ord(c) <= 0xFAFF
        for c in text
    ):
        return "zh"
    return None


# Per-script candidate faces, tried in order. Each entry is
# (ttc_path, family_substring, [weight_substrings_in_preference_order]).
# We scan the .ttc's font indexes at runtime and pick the index whose
# getname() family matches `family_substring` and whose subfamily best matches
# the weight preference — so this survives PingFang being present or absent and
# doesn't hardcode a possibly-wrong index. All matching is case-insensitive.
_CJK_CANDIDATES = {
    "ja": [
        ("/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc", "hiragino sans", ["w8", "w7", "w9", "w6"]),
        ("/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc", "hiragino sans", ["w7", "w6"]),
        ("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", "hiragino sans", ["w6"]),
    ],
    "zh": [
        ("/System/Library/Fonts/PingFang.ttc", "pingfang sc", ["heavy", "semibold", "bold", "medium", "regular"]),
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", "hiragino sans gb", ["w6", "w3"]),
        ("/System/Library/Fonts/STHeiti Medium.ttc", "heiti sc", ["medium"]),
        ("/System/Library/Fonts/Supplemental/Songti.ttc", "songti sc", ["black", "bold"]),
    ],
    "ko": [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "apple sd gothic neo", ["heavy", "extrabold", "bold", "semibold"]),
    ],
}


@functools.lru_cache(maxsize=None)
def _resolve_cjk_face(script):
    """Return (ttc_path, index) for the best heavy face for `script`, or None."""
    for path, fam_kw, weight_prefs in _CJK_CANDIDATES.get(script, []):
        if not os.path.isfile(path):
            continue
        best = None  # (weight_rank, index)
        for idx in range(0, 40):
            try:
                f = ImageFont.truetype(path, 40, index=idx)
            except Exception:
                break  # ran past the last face in the collection
            try:
                fam, sub = f.getname()
            except Exception:
                continue
            fam_l = (fam or "").lower()
            # Skip the hidden ".…Interface"/"." system variants.
            if fam_l.startswith(".") or fam_kw not in fam_l:
                continue
            sub_l = (sub or "").lower()
            rank = next(
                (i for i, w in enumerate(weight_prefs) if w in sub_l),
                len(weight_prefs),
            )
            if best is None or rank < best[0]:
                best = (rank, idx)
        if best is not None:
            return (path, best[1])
    return None


@functools.lru_cache(maxsize=None)
def _cjk_font(script, size):
    face = _resolve_cjk_face(script)
    if face is None:
        return None
    path, idx = face
    try:
        return ImageFont.truetype(path, size, index=idx)
    except Exception:
        return None


@functools.lru_cache(maxsize=None)
def _warn_missing_cjk(script, sample):
    warn(
        f"no CJK-capable system font found for {script!r} text ({sample!r}); "
        "it will render as tofu (blank boxes). Install a CJK font "
        "(e.g. via macOS Font Book, or a Noto CJK font) and retry."
    )


def font_for(cfg, text, size, script=None):
    """Return an ImageFont at `size` suited to `text`.

    Latin-only text uses the bundled Inter headline font (unchanged). Text
    containing CJK letters uses a heavy-weight CJK system font resolved for
    its script; if none is found, falls back to Inter and warns once.

    `script` optionally pins the script family ('ja'/'ko'/'zh') instead of
    classifying `text` on its own. compose() classifies the verb and desc
    TOGETHER and passes the result here, so both headline lines share one
    face — otherwise a Han-only verb in a Japanese headline (e.g. 整理) would
    classify as 'zh' by itself and render in the Chinese face while the kana
    desc gets the Japanese one.
    """
    if contains_cjk(text):
        s = script or _cjk_script(text)
        if s:
            f = _cjk_font(s, size)
            if f is not None:
                return f
            _warn_missing_cjk(s, text[:20])
    return ImageFont.truetype(cfg.font_path, size)


def die(msg):
    """Print a one-line error prefixed with the invoked script name, then exit 1."""
    prog = os.path.basename(sys.argv[0]) or "compose"
    print(f"{prog}: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg):
    """Print a non-fatal warning to stderr, prefixed with the invoked script name."""
    prog = os.path.basename(sys.argv[0]) or "compose"
    print(f"{prog}: warning: {msg}", file=sys.stderr)


@dataclass(frozen=True)
class ComposeConfig:
    # Canvas (exact App Store Connect dimensions)
    canvas_w: int
    canvas_h: int
    # Device template geometry (must match the frame generator)
    device_w: int
    bezel: int
    screen_corner_r: int
    # Layout
    device_y: int              # minimum device top position
    min_text_device_gap: int   # minimum gap between text bottom and device top
    text_top: int              # where the headline text block starts
    # Typography
    verb_size_max: int
    verb_size_min: int
    desc_size: int
    verb_desc_gap: int
    desc_line_gap: int
    # Max text width as a fraction of canvas width
    max_text_w_frac: float
    max_verb_w_frac: float
    # Absolute path to the device frame template PNG
    frame_path: str
    # Absolute path to the headline font
    font_path: str = FONT_PATH

    @property
    def screen_w(self):
        return self.device_w - 2 * self.bezel

    @property
    def max_text_w(self):
        return int(self.canvas_w * self.max_text_w_frac)

    @property
    def max_verb_w(self):
        return int(self.canvas_w * self.max_verb_w_frac)

    @property
    def target_aspect(self):
        """Nominal device-screen aspect (width / height)."""
        return self.canvas_w / self.canvas_h


def parse_hex_color(s):
    """Validate and parse a hex colour into an (r, g, b) tuple.

    Accepts an optional leading '#', 6-digit hex (E31837), or 3-digit
    shorthand (E31 -> EE3311). Anything else is a fatal error.
    """
    h = s.strip().lstrip("#")
    if len(h) == 3 and all(c in string.hexdigits for c in h):
        h = "".join(c * 2 for c in h)
    if len(h) == 6 and all(c in string.hexdigits for c in h):
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    die(
        f"invalid --bg colour {s!r}: expected 6-digit hex like #E31837 "
        "(or 3-digit shorthand like #E31)"
    )


def _char_wrap(draw, text, font, max_w):
    """Wrap on character boundaries — for CJK, which has no inter-word spaces.

    A whitespace-delimited word_wrap leaves spaceless CJK text as one giant
    line that overflows the canvas; wrapping per character keeps it inside
    max_w. An explicit space still forces a break opportunity.
    """
    lines, cur = [], ""
    for ch in text:
        if ch == " " and not cur:
            continue
        test = cur + ch
        if not cur or draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            lines.append(cur.rstrip())
            cur = "" if ch == " " else ch
    if cur.rstrip():
        lines.append(cur.rstrip())
    return lines


def word_wrap(draw, text, font, max_w):
    # CJK text has no spaces to break on — wrap per character instead.
    if contains_cjk(text):
        return _char_wrap(draw, text, font, max_w)
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_font(cfg, text, max_w, size_max, size_min, script=None):
    """Return the largest font size where text fits within max_w."""
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for size in range(size_max, size_min - 1, -4):
        font = font_for(cfg, text, size, script=script)
        bbox = dummy.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return font
    return font_for(cfg, text, size_min, script=script)


def draw_centered(cfg, draw, y, text, font, max_w=None):
    lines = word_wrap(draw, text, font, max_w) if max_w else [text]
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        # anchor="mt" (middle-top) for pixel-perfect horizontal centering.
        # Adjust y by bbox[1] so the visual top aligns with the intended y.
        draw.text(
            (cfg.canvas_w // 2, y - bbox[1]),
            line,
            fill="white",
            font=font,
            anchor="mt",
        )
        y += h + cfg.desc_line_gap
    return y


def _check_screenshot(cfg, shot):
    """Emit non-fatal warnings if the screenshot looks like the wrong shape."""
    w, h = shot.width, shot.height
    if w > h:
        warn(
            f"screenshot is landscape ({w}×{h}); App Store device screens are "
            "portrait — it will be stretched to fill the screen width"
        )
        return
    aspect = w / h
    target = cfg.target_aspect
    if aspect < target * 0.7 or aspect > target * 1.3:
        warn(
            f"screenshot aspect {aspect:.3f} ({w}×{h}) differs a lot from the "
            f"device screen aspect ~{target:.3f}; it may look distorted"
        )


def compose(cfg, bg_hex, verb, desc, screenshot_path, output_path):
    bg = parse_hex_color(bg_hex)

    if not os.path.isfile(screenshot_path):
        die(f"screenshot not found: {screenshot_path}")

    # ── 1. Canvas ───────────────────────────────────────────────────
    canvas = Image.new("RGBA", (cfg.canvas_w, cfg.canvas_h), (*bg, 255))
    draw = ImageDraw.Draw(canvas)

    # ── 2. Measure the headline block so the device can slide down ──
    # Classify the headline script ONCE from verb+desc combined so both lines
    # share the same CJK face (a Han-only verb would misclassify alone).
    headline_script = _cjk_script(verb + desc)
    verb_font = fit_font(
        cfg, verb.upper(), cfg.max_verb_w, cfg.verb_size_max, cfg.verb_size_min,
        script=headline_script,
    )
    desc_font = font_for(cfg, desc.upper(), cfg.desc_size, script=headline_script)

    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    m_y = cfg.text_top
    m_y = draw_centered(cfg, dummy, m_y, verb.upper(), verb_font)
    m_y += cfg.verb_desc_gap
    text_bottom = draw_centered(
        cfg, dummy, m_y, desc.upper(), desc_font, max_w=cfg.max_text_w
    )

    # Device sits at its default Y, but slides down if the text is tall enough
    # to collide with it. The device already bleeds off the bottom edge by
    # design, so pushing it down never crops anything meaningful.
    device_y = max(cfg.device_y, text_bottom + cfg.min_text_device_gap)

    # ── 3. Draw the headline text ───────────────────────────────────
    y = cfg.text_top
    y = draw_centered(cfg, draw, y, verb.upper(), verb_font)
    y += cfg.verb_desc_gap
    draw_centered(cfg, draw, y, desc.upper(), desc_font, max_w=cfg.max_text_w)

    device_x = (cfg.canvas_w - cfg.device_w) // 2
    screen_x = device_x + cfg.bezel
    screen_y = device_y + cfg.bezel

    # ── 4. Screenshot into the screen area ──────────────────────────
    shot = Image.open(screenshot_path).convert("RGBA")
    _check_screenshot(cfg, shot)

    # Scale to fill screen width
    scale = cfg.screen_w / shot.width
    sc_w = cfg.screen_w
    sc_h = int(shot.height * scale)
    shot = shot.resize((sc_w, sc_h), Image.LANCZOS)

    # Screen extends to the bottom of the canvas + overflow
    screen_h = cfg.canvas_h - screen_y + 500

    scr_mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(scr_mask).rounded_rectangle(
        [screen_x, screen_y, screen_x + cfg.screen_w, screen_y + screen_h],
        radius=cfg.screen_corner_r,
        fill=255,
    )

    scr_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(scr_layer).rounded_rectangle(
        [screen_x, screen_y, screen_x + cfg.screen_w, screen_y + screen_h],
        radius=cfg.screen_corner_r,
        fill=(0, 0, 0, 255),
    )
    scr_layer.paste(shot, (screen_x, screen_y))
    scr_layer.putalpha(scr_mask)
    canvas = Image.alpha_composite(canvas, scr_layer)

    # ── 5. Device frame template ────────────────────────────────────
    frame_template = Image.open(cfg.frame_path).convert("RGBA")
    frame_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    frame_layer.paste(frame_template, (device_x, device_y))
    canvas = Image.alpha_composite(canvas, frame_layer)

    # ── 6. Save ─────────────────────────────────────────────────────
    canvas.convert("RGB").save(output_path, "PNG")
    print(f"✓ {output_path} ({cfg.canvas_w}×{cfg.canvas_h})")
