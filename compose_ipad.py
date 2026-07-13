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

The device frame is positioned dynamically based on text height: when the
headline wraps to several lines the device slides down so it never overlaps
the text (it already bleeds off the bottom edge by design).

All drawing/compositing lives in compose_common; this file holds only the
iPad layout/typography constants and the CLI. These values are pre-tuned for
iPad's larger canvas and avoid the headline-overlapping-device regression seen
in earlier runs.
"""

import argparse
import os

from compose_common import ComposeConfig, compose

CFG = ComposeConfig(
    canvas_w=2064,
    canvas_h=2752,
    # Device template constants (must match generate_frame_ipad.py)
    device_w=1720,
    bezel=36,
    screen_corner_r=36,
    # Layout
    device_y=860,
    min_text_device_gap=40,
    text_top=180,
    # Typography
    verb_size_max=300,
    verb_size_min=200,
    desc_size=140,
    verb_desc_gap=24,
    desc_line_gap=24,
    max_text_w_frac=0.88,
    max_verb_w_frac=0.88,
    frame_path=os.path.join(
        os.path.dirname(__file__), "assets", "device_frame_ipad.png"
    ),
)


def main():
    p = argparse.ArgumentParser(description="Compose iPad App Store screenshot")
    p.add_argument("--bg", required=True, help="Background hex colour (#2563EB)")
    p.add_argument("--verb", required=True, help="Action verb (FREE UP)")
    p.add_argument("--desc", required=True, help="Benefit descriptor (GIGABYTES OF STORAGE)")
    p.add_argument("--screenshot", required=True, help="iPad simulator screenshot path")
    p.add_argument("--output", required=True, help="Output file path")
    args = p.parse_args()

    compose(CFG, args.bg, args.verb, args.desc, args.screenshot, args.output)


if __name__ == "__main__":
    main()
