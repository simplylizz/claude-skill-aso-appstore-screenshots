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

Backends:
  --backend gemini (default)  Calls Google's Nano Banana Pro via the google-genai
                              SDK. Requires GEMINI_API_KEY (or GOOGLE_API_KEY).
  --backend codex             Shells out to the OpenAI "codex" CLI in
                              non-interactive mode (uses your ChatGPT/OpenAI
                              subscription instead of a Gemini API key). Best
                              effort: the output file is validated as a readable
                              image afterwards.

Usage:
  uv run enhance.py \
    --prompt-file prompt.txt \
    --image screenshots/01-foo/scaffold.png \
    --aspect-ratio 9:16 \
    --output screenshots/01-foo/v1.jpg

Flags:
  --prompt / --prompt-file  The edit prompt (one of the two).
  --image                   Reference image path; repeatable, order preserved
                            (matches "FIRST image" / "SECOND image" in prompts).
  --output                  Where to write the result (required). The output
                            file extension decides the saved format.
  --aspect-ratio            Optional aspect-ratio preset for the gemini backend
                            (e.g. "9:16", "3:4"). Omitted => model default.
  --model                   Gemini model id (default: $GEMINI_MODEL or the
                            built-in default). Ignored by the codex backend.
  --backend                 gemini (default) or codex. Env: ENHANCE_BACKEND.
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from PIL import Image

# Nano Banana Pro (Gemini 3 Pro Image), GA. The former "gemini-3-pro-image-preview"
# was shut down on 2026-06-25.
DEFAULT_MODEL = "gemini-3-pro-image"

# Per-request HTTP timeout for the Gemini call. HttpOptions.timeout is in ms.
REQUEST_TIMEOUT_MS = 300_000

# Bounded retry policy for retryable transport failures.
MAX_RETRIES = 2
INITIAL_BACKOFF_S = 2.0
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
RETRYABLE_KEYWORDS = (
    "timeout",
    "timed out",
    "deadline",
    "temporarily",
    "unavailable",
    "connection",
    "reset by peer",
)

# Map output extension -> Pillow save format.
EXT_TO_FORMAT = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
}

CODEX_TIMEOUT_S = 600


def die(msg: str, code: int = 1) -> None:
    print(f"enhance.py: {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg: str) -> None:
    print(f"enhance.py: warning: {msg}", file=sys.stderr)


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


def validate_image_paths(paths: list[str]) -> list[Path]:
    """Validate every --image path exists and is a readable image; return Paths."""
    if not paths:
        die("at least one --image is required")
    resolved: list[Path] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            die(f"image not found: {path}")
        try:
            with Image.open(path) as img:
                img.load()
        except Exception as e:
            die(f"failed to read image {path}: {e}")
        resolved.append(path)
    return resolved


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


def is_retryable(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    if not isinstance(code, int):
        code = getattr(exc, "status_code", None)
    if isinstance(code, int) and code in RETRYABLE_STATUS:
        return True
    haystack = f"{type(exc).__name__} {exc}".lower()
    return any(kw in haystack for kw in RETRYABLE_KEYWORDS)


def save_image_bytes(image_bytes: bytes, output: Path) -> None:
    """Decode returned bytes with Pillow and save in the format implied by the
    output extension. Falls back to writing raw bytes if Pillow can't parse."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception as e:
        warn(f"could not decode returned image with Pillow ({e}); writing raw bytes to {output}")
        output.write_bytes(image_bytes)
        return

    ext = output.suffix.lower().lstrip(".")
    save_format = EXT_TO_FORMAT.get(ext) or (img.format or "PNG")
    if save_format == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    try:
        img.save(output, format=save_format)
    except Exception as e:
        warn(f"Pillow could not save as {save_format} ({e}); writing raw bytes to {output}")
        output.write_bytes(image_bytes)


def generate_with_retry(client, model: str, contents: list, config) -> object:
    backoff = INITIAL_BACKOFF_S
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as e:  # noqa: BLE001 - we re-raise below
            last_exc = e
            if attempt < MAX_RETRIES and is_retryable(e):
                warn(
                    f"retryable Gemini error on attempt {attempt + 1}/{MAX_RETRIES + 1} "
                    f"({type(e).__name__}: {e}); retrying in {backoff:.0f}s"
                )
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
    # Unreachable, but keep type checkers happy.
    assert last_exc is not None
    raise last_exc


def run_gemini(args: argparse.Namespace, prompt: str, image_paths: list[Path], output: Path) -> None:
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        die(
            "Neither GEMINI_API_KEY nor GOOGLE_API_KEY is set. Export one (e.g. in ~/.zshrc or your shell's env) "
            "and re-run. Get a key at https://aistudio.google.com/apikey. "
            "(Or use --backend codex to route through the OpenAI codex CLI instead.)"
        )

    images = [Image.open(p) for p in image_paths]
    for img in images:
        img.load()

    client = genai.Client(http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS))
    contents: list = [prompt, *images]

    image_config = None
    if args.aspect_ratio:
        image_config = types.ImageConfig(aspect_ratio=args.aspect_ratio)

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=image_config,
    )

    try:
        response = generate_with_retry(client, args.model, contents, config)
    except genai_errors.APIError as e:
        die(f"Gemini API call failed (code={getattr(e, 'code', '?')}): {e}")
    except Exception as e:  # noqa: BLE001
        die(f"Gemini API call failed: {e}")

    image_bytes = extract_image_bytes(response)
    if not image_bytes:
        die(f"no image returned by model. details: {describe_failure(response)}")

    save_image_bytes(image_bytes, output)
    print(str(output))


def run_codex(args: argparse.Namespace, prompt: str, image_paths: list[Path], output: Path) -> None:
    codex = shutil.which("codex")
    if not codex:
        die(
            "codex CLI not found on PATH. Install it (e.g. `npm install -g @openai/codex`) "
            "and sign in with your ChatGPT account, or use --backend gemini."
        )

    abs_out = output.resolve()
    abs_imgs = [str(p.resolve()) for p in image_paths]

    instruction_lines = [
        "You have an image generation/editing tool available via your ChatGPT "
        "subscription (gpt-image). Using the provided reference image(s), produce a "
        "single edited/enhanced image and SAVE IT AS A FILE to this exact absolute path:",
        str(abs_out),
        "",
    ]
    if abs_imgs:
        instruction_lines.append("Reference images (in order):")
        instruction_lines.extend(f"{i + 1}. {p}" for i, p in enumerate(abs_imgs))
        instruction_lines.append("")
    if args.aspect_ratio:
        instruction_lines.append(f"Target aspect ratio: {args.aspect_ratio}.")
        instruction_lines.append("")
    instruction_lines.append("Editing instructions:")
    instruction_lines.append(prompt)
    instruction_lines.append("")
    instruction_lines.append(
        f"Write ONLY the final image to {abs_out}. Overwrite it if it already exists. "
        "Do not create any other files."
    )
    instruction = "\n".join(instruction_lines)

    cmd = [codex, "exec", "--sandbox", "workspace-write", "--skip-git-repo-check"]
    for p in abs_imgs:
        cmd += ["--image", p]
    cmd += ["--", instruction]

    # Remove any stale output so existence == success.
    if abs_out.exists():
        try:
            abs_out.unlink()
        except OSError:
            pass

    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=CODEX_TIMEOUT_S,
            cwd=str(abs_out.parent),
        )
    except FileNotFoundError:
        die("codex CLI not found on PATH. Install it and re-run, or use --backend gemini.")
    except subprocess.TimeoutExpired:
        die(f"codex exec timed out after {CODEX_TIMEOUT_S}s")

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-1000:]
        die(f"codex exec failed (exit {proc.returncode}): {tail}")

    if not abs_out.is_file():
        tail = (proc.stdout or proc.stderr or "").strip()[-1000:]
        die(f"codex ran but did not write an image to {abs_out}. Output tail: {tail}")

    try:
        with Image.open(abs_out) as img:
            img.load()
    except Exception as e:
        die(f"codex wrote {abs_out} but it is not a readable image: {e}")

    print(str(output))


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
        "--aspect-ratio",
        dest="aspect_ratio",
        help=(
            "Aspect-ratio preset for the gemini backend, e.g. 9:16, 3:4, 1:1, 16:9. "
            "Omit to use the model default."
        ),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        help=f"Gemini model id (default: ${{GEMINI_MODEL}} or {DEFAULT_MODEL}). Ignored by --backend codex.",
    )
    env_backend = os.environ.get("ENHANCE_BACKEND", "gemini").strip().lower()
    parser.add_argument(
        "--backend",
        choices=["gemini", "codex"],
        default=env_backend,
        help="Generation backend: gemini (default, google-genai SDK) or codex (OpenAI codex CLI). Env: ENHANCE_BACKEND.",
    )
    args = parser.parse_args()

    # argparse does not validate defaults against choices, so an invalid
    # ENHANCE_BACKEND would otherwise silently fall through to gemini.
    if args.backend not in ("gemini", "codex"):
        die(f"invalid backend {args.backend!r} (from ENHANCE_BACKEND) — expected 'gemini' or 'codex'")

    prompt = load_prompt(args)
    image_paths = validate_image_paths(args.image)
    output = ensure_output_writable(args.output)

    if args.backend == "codex":
        run_codex(args, prompt, image_paths, output)
    else:
        run_gemini(args, prompt, image_paths, output)


if __name__ == "__main__":
    main()
