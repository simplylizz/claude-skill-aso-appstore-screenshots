#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pillow",
# ]
# ///
"""
App Store Screenshot Composer — iPad 13" Pro variant.
Composites headline text, iPad device frame template, and app screenshot
into a pixel-perfect 2064×2752 App Store Connect image.
"""

import argparse
import os
from PIL import Image, ImageDraw, ImageFont

# ── Canvas ──────────────────────────────────────────────────────────
CANVAS_W = 2064
CANVAS_H = 2752

# ── Device template constants (must match generate_frame_ipad.py) ──
DEVICE_W = 1720
BEZEL = 36
SCREEN_W = DEVICE_W - 2 * BEZEL    # 1648
SCREEN_CORNER_R = 36

# ── Layout ──────────────────────────────────────────────────────────
DEVICE_Y = 860                       # device top position (fixed)

# ── Typography ──────────────────────────────────────────────────────
VERB_SIZE_MAX = 300
VERB_SIZE_MIN = 200
DESC_SIZE = 140
VERB_DESC_GAP = 24
DESC_LINE_GAP = 24
MAX_TEXT_W = int(CANVAS_W * 0.88)
MAX_VERB_W = int(CANVAS_W * 0.88)

FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "InterDisplay-Black.otf")
FRAME_PATH = os.path.join(os.path.dirname(__file__), "assets", "device_frame_ipad.png")


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


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


def fit_font(text, max_w, size_max, size_min):
    """Return the largest font size where text fits within max_w."""
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for size in range(size_max, size_min - 1, -4):
        font = ImageFont.truetype(FONT_PATH, size)
        bbox = dummy.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return font
    return ImageFont.truetype(FONT_PATH, size_min)


def draw_centered(draw, y, text, font, max_w=None):
    lines = word_wrap(draw, text, font, max_w) if max_w else [text]
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        draw.text((CANVAS_W // 2, y - bbox[1]), line, fill="white", font=font, anchor="mt")
        y += h + DESC_LINE_GAP
    return y


def compose(bg_hex, verb, desc, screenshot_path, output_path):
    bg = hex_to_rgb(bg_hex)

    # ── 1. Canvas ───────────────────────────────────────────────────
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (*bg, 255))
    draw = ImageDraw.Draw(canvas)

    # ── 2. Typography ──────────────────────────────────────────────
    verb_font = fit_font(verb.upper(), MAX_VERB_W, VERB_SIZE_MAX, VERB_SIZE_MIN)
    desc_font = ImageFont.truetype(FONT_PATH, DESC_SIZE)

    device_y = DEVICE_Y
    text_top = 180

    # ── 3. Draw text ───────────────────────────────────────────────
    y = text_top
    y = draw_centered(draw, y, verb.upper(), verb_font)
    y += VERB_DESC_GAP
    draw_centered(draw, y, desc.upper(), desc_font, max_w=MAX_TEXT_W)

    device_x = (CANVAS_W - DEVICE_W) // 2
    screen_x = device_x + BEZEL
    screen_y = device_y + BEZEL

    # ── 4. Screenshot into screen area ──────────────────────────────
    shot = Image.open(screenshot_path).convert("RGBA")
    scale = SCREEN_W / shot.width
    sc_w = SCREEN_W
    sc_h = int(shot.height * scale)
    shot = shot.resize((sc_w, sc_h), Image.LANCZOS)

    # Screen extends to bottom of canvas + overflow
    screen_h = CANVAS_H - screen_y + 500

    # Screen mask (rounded rect)
    scr_mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(scr_mask).rounded_rectangle(
        [screen_x, screen_y, screen_x + SCREEN_W, screen_y + screen_h],
        radius=SCREEN_CORNER_R,
        fill=255,
    )

    scr_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(scr_layer).rounded_rectangle(
        [screen_x, screen_y, screen_x + SCREEN_W, screen_y + screen_h],
        radius=SCREEN_CORNER_R,
        fill=(0, 0, 0, 255),
    )
    scr_layer.paste(shot, (screen_x, screen_y))
    scr_layer.putalpha(scr_mask)
    canvas = Image.alpha_composite(canvas, scr_layer)

    # ── 5. Device frame template ───────────────────────────────────
    frame_template = Image.open(FRAME_PATH).convert("RGBA")
    frame_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    frame_layer.paste(frame_template, (device_x, device_y))
    canvas = Image.alpha_composite(canvas, frame_layer)

    canvas.convert("RGB").save(output_path, "PNG")
    print(f"✓ {output_path} ({CANVAS_W}×{CANVAS_H})")


def main():
    p = argparse.ArgumentParser(description="Compose iPad App Store screenshot")
    p.add_argument("--bg", required=True, help="Background hex colour (#2563EB)")
    p.add_argument("--verb", required=True, help="Action verb (FREE UP)")
    p.add_argument("--desc", required=True, help="Benefit descriptor (GIGABYTES OF STORAGE)")
    p.add_argument("--screenshot", required=True, help="iPad simulator screenshot path")
    p.add_argument("--output", required=True, help="Output file path")
    args = p.parse_args()

    compose(args.bg, args.verb, args.desc, args.screenshot, args.output)


if __name__ == "__main__":
    main()
