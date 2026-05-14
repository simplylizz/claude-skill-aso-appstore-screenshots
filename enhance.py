#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "google-genai>=1.0",
#   "pillow",
# ]
# ///
"""
Nano Banana Pro image-edit wrapper for the aso-appstore-screenshots skill.

Replaces the previous dependency on the gemini-mcp MCP server with a direct
google-genai SDK call. Accepts one or more reference images plus an edit
prompt, returns a single enhanced image.

Usage:
  uv run enhance.py \
    --prompt-file prompt.txt \
    --image screenshots/01-foo/scaffold.png \
    --output screenshots/01-foo/v1.jpg

Multiple --image flags can be passed; their order is preserved and matches
the order referenced in the prompt (e.g. "FIRST image", "SECOND image").
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

DEFAULT_MODEL = "gemini-3-pro-image-preview"


def die(msg: str, code: int = 1) -> None:
    print(f"enhance.py: {msg}", file=sys.stderr)
    sys.exit(code)


def load_prompt(args: argparse.Namespace) -> str:
    if args.prompt and args.prompt_file:
        die("pass either --prompt or --prompt-file, not both")
    if args.prompt_file:
        path = Path(args.prompt_file)
        if not path.is_file():
            die(f"prompt file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
    else:
        text = (args.prompt or "").strip()
    if not text:
        die("prompt is empty")
    return text


def load_images(paths: list[str]) -> list[Image.Image]:
    if not paths:
        die("at least one --image is required")
    images: list[Image.Image] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            die(f"image not found: {path}")
        try:
            img = Image.open(path)
            img.load()
        except Exception as e:
            die(f"failed to read image {path}: {e}")
        images.append(img)
    return images


def ensure_output_writable(output: str) -> Path:
    path = Path(output)
    parent = path.parent if path.parent != Path("") else Path(".")
    if not parent.exists():
        die(f"output directory does not exist: {parent}")
    return path


def extract_image_bytes(response) -> bytes | None:
    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                return inline.data
    return None


def describe_failure(response) -> str:
    bits: list[str] = []
    feedback = getattr(response, "prompt_feedback", None)
    if feedback:
        bits.append(f"prompt_feedback={feedback}")
    candidates = getattr(response, "candidates", None) or []
    for i, cand in enumerate(candidates):
        finish = getattr(cand, "finish_reason", None)
        safety = getattr(cand, "safety_ratings", None)
        bits.append(f"candidate[{i}] finish_reason={finish} safety={safety}")
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                bits.append(f"candidate[{i}] text={text!r}")
    return "; ".join(bits) if bits else "no candidates returned"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", help="Edit prompt as a string")
    parser.add_argument("--prompt-file", help="Path to a file containing the edit prompt")
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Path to a reference image (repeatable; order is preserved)",
    )
    parser.add_argument("--output", required=True, help="Path to write the enhanced image")
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        help=f"Gemini model id (default: ${{GEMINI_MODEL}} or {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        die(
            "GEMINI_API_KEY is not set. Export it (e.g. in ~/.zshrc or your shell's env) "
            "and re-run. Get a key at https://aistudio.google.com/apikey."
        )

    prompt = load_prompt(args)
    images = load_images(args.image)
    output = ensure_output_writable(args.output)

    client = genai.Client()
    contents: list = [prompt, *images]

    try:
        response = client.models.generate_content(
            model=args.model,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
    except Exception as e:
        die(f"Gemini API call failed: {e}")

    image_bytes = extract_image_bytes(response)
    if not image_bytes:
        die(f"no image returned by model. details: {describe_failure(response)}")

    output.write_bytes(image_bytes)
    print(str(output))


if __name__ == "__main__":
    main()
