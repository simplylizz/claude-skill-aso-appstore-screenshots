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

import os
import string
import sys
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

# Default headline font, resolved relative to this file (== repo root / assets).
FONT_PATH = os.path.join(
    os.path.dirname(__file__), "assets", "fonts", "InterDisplay-Black.otf"
)


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


def word_wrap(draw, text, font, max_w):
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


def fit_font(cfg, text, max_w, size_max, size_min):
    """Return the largest font size where text fits within max_w."""
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for size in range(size_max, size_min - 1, -4):
        font = ImageFont.truetype(cfg.font_path, size)
        bbox = dummy.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return font
    return ImageFont.truetype(cfg.font_path, size_min)


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
    verb_font = fit_font(
        cfg, verb.upper(), cfg.max_verb_w, cfg.verb_size_max, cfg.verb_size_min
    )
    desc_font = ImageFont.truetype(cfg.font_path, cfg.desc_size)

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
