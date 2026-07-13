#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pillow",
# ]
# ///
"""
Generate iPad device frame template PNG.
Output: assets/device_frame_ipad.png — standalone device image (not positioned on canvas).
compose_ipad.py positions this dynamically based on text height.
"""

import os

from PIL import Image, ImageDraw, ImageChops

# ── Device dimensions ───────────────────────────────────────────────
# Width is ~83% of 2064 canvas, matching reference screenshots.
# iPad Pro 13" device aspect (~0.765 portrait) — uniform thin bezels.
DEVICE_W = 1720
DEVICE_H = 2300           # tall enough to bleed off any canvas
DEVICE_CORNER_R = 70
BEZEL = 36
SCREEN_CORNER_R = 36
CAMERA_DOT_R = 8          # tiny front camera dot at top centre

SCREEN_W = DEVICE_W - 2 * BEZEL
SCREEN_H = DEVICE_H - 2 * BEZEL


def generate():
    frame = Image.new("RGBA", (DEVICE_W, DEVICE_H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)

    # ── Device body (dark grey outer, darker inner) ─────────────────
    fd.rounded_rectangle(
        [0, 0, DEVICE_W - 1, DEVICE_H - 1],
        radius=DEVICE_CORNER_R,
        fill=(30, 30, 30, 255),
    )
    fd.rounded_rectangle(
        [1, 1, DEVICE_W - 2, DEVICE_H - 2],
        radius=DEVICE_CORNER_R - 1,
        fill=(20, 20, 20, 255),
    )

    # ── Screen cutout (transparent) ─────────────────────────────────
    screen_x = BEZEL
    screen_y = BEZEL

    cutout = Image.new("L", (DEVICE_W, DEVICE_H), 255)
    ImageDraw.Draw(cutout).rounded_rectangle(
        [screen_x, screen_y, screen_x + SCREEN_W, screen_y + SCREEN_H],
        radius=SCREEN_CORNER_R,
        fill=0,
    )
    frame.putalpha(ImageChops.multiply(frame.getchannel("A"), cutout))

    # ── Front camera dot (top centre on bezel) ──────────────────────
    cam_x = DEVICE_W // 2
    cam_y = BEZEL // 2
    ImageDraw.Draw(frame).ellipse(
        [cam_x - CAMERA_DOT_R, cam_y - CAMERA_DOT_R,
         cam_x + CAMERA_DOT_R, cam_y + CAMERA_DOT_R],
        fill=(10, 10, 10, 255),
    )

    # ── Side buttons (subtle, iPad-style: power top-right, volume top-left) ──
    btn_color = (25, 25, 25, 255)
    fd2 = ImageDraw.Draw(frame)

    # Buttons are drawn just INSIDE the top edge (the template height is fixed
    # because compose paste math depends on it, so they can't protrude).
    # Power button (top-right edge)
    fd2.rounded_rectangle(
        [DEVICE_W - 220, 0, DEVICE_W - 120, 4],
        radius=2, fill=btn_color,
    )
    # Volume buttons (top-left edge, two)
    fd2.rounded_rectangle(
        [120, 0, 220, 4],
        radius=2, fill=btn_color,
    )
    fd2.rounded_rectangle(
        [240, 0, 340, 4],
        radius=2, fill=btn_color,
    )

    out = os.path.join(os.path.dirname(__file__), "assets", "device_frame_ipad.png")
    frame.save(out, "PNG")
    print(f"✓ {out} ({DEVICE_W}×{DEVICE_H})")
    print(f"  BEZEL={BEZEL}, SCREEN_W={SCREEN_W}, SCREEN_H={SCREEN_H}")
    print(f"  SCREEN_CORNER_R={SCREEN_CORNER_R}")


if __name__ == "__main__":
    generate()
