#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pillow",
# ]
# ///
"""
App Store Screenshot Composer — iPhone 6.9" variant.
Composites headline text, device frame template, and app screenshot
into a pixel-perfect 1290×2796 App Store Connect image.

The device frame is positioned dynamically based on text height: when the
headline wraps to several lines the device slides down so it never overlaps
the text (it already bleeds off the bottom edge by design).

All drawing/compositing lives in compose_common; this file holds only the
iPhone layout/typography constants and the CLI.
"""

import argparse
import os

from compose_common import ComposeConfig, compose

CFG = ComposeConfig(
    canvas_w=1290,
    canvas_h=2796,
    # Device template constants (must match generate_frame.py)
    device_w=1030,
    bezel=15,
    screen_corner_r=62,
    # Layout
    device_y=720,
    min_text_device_gap=40,
    text_top=200,
    # Typography
    verb_size_max=256,
    verb_size_min=150,
    desc_size=124,
    verb_desc_gap=20,
    desc_line_gap=24,
    max_text_w_frac=0.92,
    max_verb_w_frac=0.92,
    frame_path=os.path.join(
        os.path.dirname(__file__), "assets", "device_frame.png"
    ),
)


def main():
    p = argparse.ArgumentParser(description="Compose iPhone App Store screenshot")
    p.add_argument("--bg", required=True, help="Background hex colour (#E31837)")
    p.add_argument("--verb", required=True, help="Action verb (TRACK)")
    p.add_argument("--desc", required=True, help="Benefit descriptor (TRADING CARD PRICES)")
    p.add_argument("--screenshot", required=True, help="Simulator screenshot path")
    p.add_argument("--output", required=True, help="Output file path")
    args = p.parse_args()

    compose(CFG, args.bg, args.verb, args.desc, args.screenshot, args.output)


if __name__ == "__main__":
    main()
