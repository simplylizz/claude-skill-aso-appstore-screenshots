#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pillow",
# ]
# ///
"""
Showcase Image Generator
Creates a preview image showing the final App Store screenshots side-by-side
on a white background with an optional GitHub link at the bottom. Accepts any
number of screenshots (the pipeline passes all finals, typically 3-5).
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def die(msg):
    """Print a one-line error prefixed with the script name, then exit 1."""
    prog = os.path.basename(sys.argv[0]) or "showcase"
    print(f"{prog}: {msg}", file=sys.stderr)
    sys.exit(1)

# ── Layout ──────────────────────────────────────────────────────────
PADDING = 60
GAP = 40
BOTTOM_BAR_H = 100
FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "Inter-Regular.otf")
FONT_SIZE_MAX = 48
FONT_SIZE_MIN = 16
TEXT_COLOUR = "#000000"
BG_COLOUR = (255, 255, 255)


def fit_text_font(text, max_w, size_max, size_min):
    """Return the largest font size where text fits within max_w."""
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(size_max, size_min - 1, -2):
        font = ImageFont.truetype(FONT_PATH, size)
        bbox = dummy.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return font
    return ImageFont.truetype(FONT_PATH, size_min)


def create_showcase(screenshots, output_path, github_url=None):
    # Load screenshots (checking each path exists first)
    for p in screenshots:
        if not os.path.isfile(p):
            die(f"screenshot not found: {p}")

    # Scale all to the same height. Open each handle inside a context manager so
    # it is closed once we hold the independent scaled copy. Resize BEFORE the
    # RGBA conversion so the conversion touches ~800px copies, not the full-res
    # finals (converting first allocates a throwaway full-res RGBA per shot).
    target_h = 800
    scaled = []
    aspects = []  # (path, width/height) for the mixed-input check
    for p in screenshots:
        with Image.open(p) as src:
            frame = src if src.mode in ("RGB", "RGBA") else src.convert("RGBA")
            aspects.append((p, frame.width / frame.height))
            ratio = target_h / frame.height
            scaled.append(
                frame.resize(
                    (int(frame.width * ratio), target_h), Image.LANCZOS
                ).convert("RGBA")
            )

    # All inputs are scaled to one height, so mixing device classes/orientations
    # composes a lopsided showcase. Warn (don't abort) if any two aspect ratios
    # differ by more than ~2% — the user may want a mixed preview.
    if aspects:
        ref_path, ref_ratio = aspects[0]
        odd = [p for p, r in aspects if abs(r - ref_ratio) / ref_ratio > 0.02]
        if odd:
            print(
                f"showcase: warning: mixed aspect ratios — {', '.join(odd)} "
                f"differ from {ref_path} by more than 2%; the showcase may look "
                "lopsided (mixing iPhone/iPad or portrait/landscape?)",
                file=sys.stderr,
            )

    # Calculate canvas size
    total_w = sum(s.width for s in scaled) + GAP * (len(scaled) - 1) + PADDING * 2
    total_h = target_h + PADDING * 2 + (BOTTOM_BAR_H if github_url else 0)

    canvas = Image.new("RGB", (total_w, total_h), BG_COLOUR)

    # Place screenshots
    x = PADDING
    for s in scaled:
        canvas.paste(s, (x, PADDING), s if s.mode == "RGBA" else None)
        x += s.width + GAP

    # Add GitHub URL text
    if github_url:
        draw = ImageDraw.Draw(canvas)
        max_text_w = total_w - PADDING * 2
        font = fit_text_font(github_url, max_text_w, FONT_SIZE_MAX, FONT_SIZE_MIN)

        text_y = PADDING + target_h + (BOTTOM_BAR_H // 2)
        draw.text(
            (total_w // 2, text_y),
            github_url,
            fill=TEXT_COLOUR,
            font=font,
            anchor="mm",
        )

    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)
    canvas.save(output_path, "PNG")
    print(f"✓ {output_path} ({total_w}×{total_h})")


def main():
    p = argparse.ArgumentParser(description="Generate showcase image")
    p.add_argument(
        "--screenshots",
        nargs="+",
        required=True,
        help="Paths to the final screenshot images (PNG); pass all finals",
    )
    p.add_argument("--output", required=True, help="Output file path")
    p.add_argument("--github", default=None, help="GitHub URL to display at bottom")
    args = p.parse_args()

    create_showcase(args.screenshots, args.output, args.github)


if __name__ == "__main__":
    main()
