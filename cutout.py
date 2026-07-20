#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pillow",
#   "numpy",
# ]
# ///
"""
Chroma-key a flat background colour out of a genai-generated piece.

Image models output opaque rectangles on a flat background and won't reproduce a
commanded hex exactly, so pasting one straight into an HTML page shows a visible
plate. This helper keys out that background: pixels within `--tolerance` of the
commanded colour become fully transparent, and a `--feather` band just above the
tolerance ramps alpha smoothly for a soft anti-aliased edge. Output is an RGBA
PNG ready to composite as an `<img>` layer.

Usage:
    uv run cutout.py \\
      --input piece.png \\
      --color "#00FF00" \\
      --tolerance 30 \\
      --feather 4 \\
      --output piece-cut.png

Colour distance is Euclidean in RGB. `--tolerance` and `--feather` are measured
in that same distance space (0..~441, the max RGB distance being sqrt(3)*255).
"""

import argparse
import math
import os
import string
import sys

import numpy as np
from PIL import Image

# Max possible Euclidean distance between two RGB colours: sqrt(3) * 255.
_MAX_DIST = math.sqrt(3) * 255


def die(msg):
    """Print a one-line error prefixed with the script name, then exit 1."""
    prog = os.path.basename(sys.argv[0]) or "cutout"
    print(f"{prog}: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg):
    """Print a non-fatal warning to stderr, prefixed with the script name."""
    prog = os.path.basename(sys.argv[0]) or "cutout"
    print(f"{prog}: warning: {msg}", file=sys.stderr)


def parse_hex_color(s):
    """Validate and parse a hex colour into an (r, g, b) tuple.

    Accepts an optional leading '#', 6-digit hex (00FF00), or 3-digit shorthand
    (0F0 -> 00FF00). Anything else is a fatal error.
    """
    h = s.strip().lstrip("#")
    if len(h) == 3 and all(c in string.hexdigits for c in h):
        h = "".join(c * 2 for c in h)
    if len(h) == 6 and all(c in string.hexdigits for c in h):
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    die(
        f"invalid --color {s!r}: expected 6-digit hex like #00FF00 "
        "(or 3-digit shorthand like #0F0)"
    )


def cutout(img, key, tolerance, feather):
    """Chroma-key `key` out of `img`.

    For each pixel, compute its Euclidean RGB distance `d` to `key`:
      d <= tolerance                -> fully transparent (alpha 0)
      tolerance < d <= tol+feather  -> linear ramp from 0 up to opaque
      d > tolerance + feather       -> unchanged alpha (fully opaque subject)

    Existing alpha is preserved where a pixel stays opaque (min() with the
    computed alpha), so an already-transparent input never gets re-opaqued.

    Returns (result_image, input_alpha, output_alpha) — the alpha planes are
    returned so the caller's sanity checks don't have to re-convert/re-scan
    the full image.
    """
    img = img.convert("RGBA")
    kr, kg, kb = key

    arr = np.asarray(img)  # (h, w, 4), uint8
    # Squared distances stay <= 3*255^2 (~195k), exactly representable in
    # float32 — cheaper than float64, and the sqrt is only needed inside the
    # (tiny) feather band, not over the whole image.
    rgb = arr[..., :3].astype(np.float32)
    existing_a = arr[..., 3]

    # Squared Euclidean RGB distance to the key colour, per pixel.
    d2 = (rgb[..., 0] - kr) ** 2 + (rgb[..., 1] - kg) ** 2 + (rgb[..., 2] - kb) ** 2

    # Default: fully opaque subject (d > tolerance + feather).
    new_a = np.full(d2.shape, 255, dtype=np.uint8)
    # d <= tolerance => fully transparent.
    new_a[d2 <= tolerance**2] = 0
    # tolerance < d <= tolerance + feather => linear ramp (only if feathering).
    # feather == 0 => hard edge (step at the tolerance boundary), no ramp band.
    if feather > 0:
        ramp = (d2 > tolerance**2) & (d2 <= (tolerance + feather) ** 2)
        d_ramp = np.sqrt(d2[ramp])
        # 0 < ramp value <= 255, so uint8 is safe after rounding.
        # round() matches Python's round-half-to-even (np.rint does the same).
        ramp_a = np.rint(255 * (d_ramp - tolerance) / feather).astype(np.uint8)
        new_a[ramp] = ramp_a

    # Never re-opaque an already-transparent pixel: keep the smaller alpha.
    out_a = np.minimum(existing_a, new_a)

    out = arr.copy()
    out[..., 3] = out_a
    return Image.fromarray(out, "RGBA"), existing_a, out_a


def main():
    ap = argparse.ArgumentParser(
        description="Chroma-key a flat background colour out of an image, "
        "writing a transparent RGBA PNG."
    )
    ap.add_argument("--input", required=True, help="Path to the source image.")
    ap.add_argument(
        "--color",
        required=True,
        help="Background colour to key out, as hex (e.g. #00FF00 or #0F0).",
    )
    ap.add_argument(
        "--tolerance",
        type=float,
        default=30.0,
        help="RGB-distance radius fully keyed to transparent (default 30).",
    )
    ap.add_argument(
        "--feather",
        type=float,
        default=4.0,
        help="RGB-distance band above tolerance that ramps alpha for a soft "
        "edge (default 4; 0 = hard edge).",
    )
    ap.add_argument(
        "--output", required=True, help="Path to write the RGBA PNG."
    )
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        die(f"input not found: {args.input}")

    key = parse_hex_color(args.color)

    if args.tolerance < 0:
        die(f"--tolerance must be >= 0 (got {args.tolerance})")
    if args.feather < 0:
        die(f"--feather must be >= 0 (got {args.feather})")
    if args.tolerance > _MAX_DIST:
        warn(
            f"--tolerance {args.tolerance} exceeds the max RGB distance "
            f"({_MAX_DIST:.0f}); every pixel will be keyed transparent"
        )

    try:
        img = Image.open(args.input)
        img.load()
    except Exception as e:
        die(f"could not read input image {args.input!r}: {e}")

    result, in_alpha, alpha = cutout(img, key, args.tolerance, args.feather)

    # Sanity-check the keying result. Still writes the file — the caller's QA
    # loop decides — but a warning flags an obviously wrong --color/--tolerance.
    # "Key matched" is judged against the INPUT alpha, so pre-existing
    # transparency in the input can't mask a no-match. The two failure shapes:
    #   - nothing went FULLY transparent -> the key colour never truly matched
    #     (a feather-band-only graze still leaves a half-opaque plate);
    #   - everything lost opacity -> the tolerance ate the subject.
    keyed_full = bool(((alpha == 0) & (in_alpha > 0)).any())
    keyed_partial = bool((alpha < in_alpha).any())
    has_opaque = bool((alpha == 255).any())
    if not keyed_full:
        if keyed_partial:
            warn(
                "the key only grazed the feather band — no pixel went fully "
                "transparent, so a half-opaque background plate remains. The "
                "background sits just outside --tolerance: raise it (or check "
                "--color)."
            )
        else:
            warn(
                "no pixel was keyed at all — the key colour never matched. "
                "Check --color matches the piece's background, or raise "
                "--tolerance."
            )
    elif not has_opaque:
        warn(
            "every pixel is (partly) transparent — the tolerance likely ate the "
            "subject too. Lower --tolerance, or check --color isn't a colour the "
            "subject also uses."
        )

    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir and not os.path.isdir(out_dir):
        die(f"output directory does not exist: {out_dir}")

    try:
        result.save(args.output, "PNG")
    except Exception as e:
        die(f"could not write output {args.output!r}: {e}")

    print(f"✓ {args.output} ({result.width}×{result.height}, RGBA)")


if __name__ == "__main__":
    main()
