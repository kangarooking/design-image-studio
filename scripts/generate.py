#!/usr/bin/env python3
"""
Volcengine Seedream Image Generation Script
============================================
Features:
  - Text-to-image, image-to-image, multi-image fusion, sequential generation
  - Automatic retry with exponential backoff and jitter
  - Model fallback on repeated failures
  - Cost estimation, budget limiting, and usage logging
  - Streaming support for sequential images

Usage:
  python generate.py --prompt "A sunset over mountains" --model auto --size 2K
  python generate.py --prompt "Edit background" --image photo.png --size 2K
  python generate.py --prompt "Storyboard" --sequential --max-images 4
"""

import argparse
import base64
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Configuration ─────────────────────────────────────────────

MODELS = {
    "doubao-seedream-5-0-260128": {
        "name": "Seedream 5.0",
        "tier": "high",
        "resolutions": ["2K", "3K"],
        "formats": ["png", "jpeg"],
        "cost_per_image": {"1K": 0.04, "2K": 0.06, "3K": 0.10, "4K": 0.14},
    },
    "doubao-seedream-5-0-lite-260128": {
        "name": "Seedream 5.0 lite",
        "tier": "mid",
        "resolutions": ["2K", "3K"],
        "formats": ["png", "jpeg"],
        "cost_per_image": {"1K": 0.02, "2K": 0.04, "3K": 0.06, "4K": 0.08},
    },
    "doubao-seedream-4-5-251128": {
        "name": "Seedream 4.5",
        "tier": "high",
        "resolutions": ["2K", "4K"],
        "formats": ["jpeg"],
        "cost_per_image": {"1K": 0.04, "2K": 0.06, "3K": 0.08, "4K": 0.12},
    },
    "doubao-seedream-4-0-250828": {
        "name": "Seedream 4.0",
        "tier": "low",
        "resolutions": ["1K", "2K", "4K"],
        "formats": ["jpeg"],
        "cost_per_image": {"1K": 0.02, "2K": 0.03, "3K": 0.05, "4K": 0.08},
    },
}

# Resolution presets → approximate pixel counts
RESOLUTION_MAP = {
    "1K": 921600,
    "2K": 3686400,
    "3K": 9437184,
    "4K": 16777216,
}

COST_LOG_DEFAULT = os.path.expanduser("~/.volcengine-image-costs.json")

# ── Cost Management ───────────────────────────────────────────

def resolve_resolution(size_arg: str, model_id: str) -> str:
    """Resolve size argument to a resolution tier for cost estimation."""
    if size_arg in RESOLUTION_MAP:
        return size_arg
    # Parse pixel dimensions like "2048x2048"
    if "x" in size_arg.lower():
        parts = size_arg.lower().split("x")
        try:
            pixels = int(parts[0]) * int(parts[1])
            return min(
                RESOLUTION_MAP,
                key=lambda tier: abs(RESOLUTION_MAP[tier] - pixels),
            )
        except (ValueError, IndexError):
            pass
    return "2K"  # default


def estimate_cost(model_id: str, size: str, num_images: int = 1) -> float:
    """Estimate cost in CNY for a generation request."""
    model_info = MODELS.get(model_id, {})
    cost_table = model_info.get("cost_per_image", {})
    resolution = resolve_resolution(size, model_id)
    per_image = cost_table.get(resolution, 0.04)  # default estimate
    return per_image * num_images


def check_budget(cost: float, budget_limit: Optional[float], cost_log_path: str) -> bool:
    """Check if this generation would exceed the budget limit."""
    if budget_limit is None:
        return True

    cumulative = 0.0
    if os.path.exists(cost_log_path):
        try:
            with open(cost_log_path, "r") as f:
                log = json.load(f)
                cumulative = sum(e.get("cost", 0) for e in log.get("entries", []))
        except (json.JSONDecodeError, IOError):
            pass

    if cumulative + cost > budget_limit:
        print(f"⚠ Budget limit: cumulative ¥{cumulative:.4f} + estimated ¥{cost:.4f} "
              f"> limit ¥{budget_limit:.4f}", file=sys.stderr)
        return False
    return True


def log_cost(model_id: str, size: str, prompt_len: int, cost: float,
             success: bool, error: str, cost_log_path: str):
    """Append a cost entry to the JSON log."""
    log = {"entries": []}
    if os.path.exists(cost_log_path):
        try:
            with open(cost_log_path, "r") as f:
                log = json.load(f)
        except (json.JSONDecodeError, IOError):
            log = {"entries": []}

    log["entries"].append({
        "timestamp": datetime.now().isoformat(),
        "model": model_id,
        "resolution": size,
        "prompt_length": prompt_len,
        "estimated_cost_cny": round(cost, 4),
        "success": success,
        "error": error,
    })

    os.makedirs(os.path.dirname(cost_log_path) or ".", exist_ok=True)
    with open(cost_log_path, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


# ── Retry Logic ───────────────────────────────────────────────

class RetryExhausted(Exception):
    """All retry attempts failed."""
    pass


class BudgetExceeded(Exception):
    """Generation would exceed budget."""
    pass


def classify_error(status_code: int, error_msg: str) -> str:
    """Classify an API error to determine retry strategy.

    Returns one of:
      - "retry"        → transient, safe to retry
      - "auth"         → authentication error, must stop
      - "bad_request"  → invalid params, must fix
      - "content_policy" → safety filter, must revise prompt
      - "unknown"      → unclassified
    """
    if status_code in (401, 403):
        return "auth"
    if status_code == 400:
        if "content" in error_msg.lower() or "safety" in error_msg.lower():
            return "content_policy"
        return "bad_request"
    if status_code == 429:
        return "retry"
    if status_code >= 500:
        return "retry"
    if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
        return "retry"
    return "unknown"


def retry_with_backoff(func, max_retries=3, initial_delay=1.0,
                        multiplier=2.0, on_fallback=None):
    """Execute func with exponential backoff + jitter on retriable errors.

    Args:
        func: Callable that performs the API call. Should raise on failure.
        max_retries: Maximum retry attempts.
        initial_delay: First retry delay in seconds.
        multiplier: Backoff multiplier between retries.
        on_fallback: Optional callable(model_id) to switch to a fallback model.

    Returns:
        The result of func().

    Raises:
        RetryExhausted: All retries failed.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_error = e

            # Extract status code from various SDK exception formats
            status_code = getattr(e, "status_code", None) or 0
            error_msg = str(e)

            error_type = classify_error(status_code, error_msg)

            # Non-retriable errors: fail immediately
            if error_type == "auth":
                print(f"✘ Authentication error: {error_msg}", file=sys.stderr)
                raise
            if error_type == "bad_request":
                print(f"✘ Bad request: {error_msg}", file=sys.stderr)
                raise
            if error_type == "content_policy":
                print(f"✘ Content policy violation: {error_msg}", file=sys.stderr)
                print("  Suggestion: Revise your prompt to avoid sensitive content.",
                      file=sys.stderr)
                raise

            # Retriable: attempt retry or fallback
            if attempt < max_retries:
                delay = initial_delay * (multiplier ** attempt)
                jitter = random.uniform(0, delay * 0.3)
                total_delay = delay + jitter

                print(f"⟳ Attempt {attempt + 1}/{max_retries} failed "
                      f"({error_type}): {error_msg[:100]}", file=sys.stderr)
                print(f"  Retrying in {total_delay:.1f}s...", file=sys.stderr)

                # On last retry attempt, try fallback model if provided
                if attempt == max_retries - 1 and on_fallback:
                    fallback_msg = on_fallback()
                    if fallback_msg:
                        print(f"  ↓ Falling back to: {fallback_msg}", file=sys.stderr)

                time.sleep(total_delay)
            else:
                print(f"✘ All {max_retries} retries exhausted.", file=sys.stderr)

    raise RetryExhausted(f"Failed after {max_retries} retries. Last error: {last_error}")


# ── Image Helpers ─────────────────────────────────────────────

def image_to_data_uri(image_path: str) -> str:
    """Convert a local image file to a data URI for the API."""
    ext = Path(image_path).suffix.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/{ext};base64,{b64}"


def download_image(url: str, output_path: str):
    """Download an image from URL to local file."""
    import urllib.request
    urllib.request.urlretrieve(url, output_path)


# ── Main Generation Logic ────────────────────────────────────

def select_model(model_arg: str) -> str:
    """Resolve 'auto' or shorthand to a full model ID."""
    if model_arg == "auto":
        return "doubao-seedream-5-0-lite-260128"  # best value default

    # Allow short names
    aliases = {
        "5.0": "doubao-seedream-5-0-260128",
        "5.0-lite": "doubao-seedream-5-0-lite-260128",
        "4.5": "doubao-seedream-4-5-251128",
        "4.0": "doubao-seedream-4-0-250828",
    }
    return aliases.get(model_arg, model_arg)


def run_generation(args):
    """Execute the image generation with all features."""
    # ── Resolve model ──
    model_id = select_model(args.model)
    fallback_model = select_model(args.fallback_model) if args.fallback_model else None

    if model_id not in MODELS:
        print(f"✘ Unknown model: {model_id}", file=sys.stderr)
        print(f"  Available: {', '.join(MODELS.keys())}", file=sys.stderr)
        sys.exit(1)

    # ── Resolve images ──
    images = None
    if args.image:
        images = []
        for img_path in args.image:
            if img_path.startswith(("http://", "https://")):
                images.append(img_path)
            elif os.path.isfile(img_path):
                images.append(image_to_data_uri(img_path))
            else:
                print(f"✘ Image not found: {img_path}", file=sys.stderr)
                sys.exit(1)

    # ── Estimate cost ──
    num_images = args.max_images if args.sequential else 1
    estimated_cost = estimate_cost(model_id, args.size, num_images)

    print(f"Model: {MODELS[model_id]['name']} ({model_id})")
    print(f"Resolution: {args.size}")
    print(f"Images: {num_images}")
    print(f"Estimated cost: ¥{estimated_cost:.4f}")

    if args.dry_run:
        print("\n[Dry run] No API call made.")
        return

    # ── Budget check ──
    if not check_budget(estimated_cost, args.budget_limit, args.cost_log):
        print("✘ Aborted: would exceed budget limit.", file=sys.stderr)
        sys.exit(1)

    # ── Prepare API client ──
    try:
        from volcenginesdkarkruntime import Ark
    except ImportError:
        print("✘ volcengine-python-sdk not installed.", file=sys.stderr)
        print("  Run: pip install 'volcengine-python-sdk[ark]'", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        print("✘ ARK_API_KEY environment variable not set.", file=sys.stderr)
        print("  Get your key at: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey",
              file=sys.stderr)
        sys.exit(1)

    client = Ark(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=api_key,
    )

    # ── Build request kwargs ──
    gen_kwargs = {
        "model": model_id,
        "prompt": args.prompt,
        "size": args.size,
        "output_format": args.output_format,
        "response_format": args.response_format,
        "watermark": args.watermark,
    }

    if images:
        gen_kwargs["image"] = images if len(images) > 1 else images[0]

    if args.sequential:
        from volcenginesdkarkruntime.types.images.images import (
            SequentialImageGenerationOptions,
        )
        gen_kwargs["sequential_image_generation"] = "auto"
        gen_kwargs["sequential_image_generation_options"] = (
            SequentialImageGenerationOptions(max_images=args.max_images)
        )

    if args.web_search:
        gen_kwargs["tools"] = [{"type": "web_search"}]

    if args.fast_mode:
        gen_kwargs["optimize_prompt_options"] = {"mode": "fast"}

    # ── Execute with retry ──
    current_model = model_id

    def do_call():
        gen_kwargs["model"] = current_model
        return client.images.generate(**gen_kwargs)

    def try_fallback():
        nonlocal current_model
        if fallback_model and fallback_model != current_model:
            current_model = fallback_model
            return MODELS[fallback_model]["name"]
        return None

    try:
        result = retry_with_backoff(
            do_call,
            max_retries=args.max_retries,
            initial_delay=args.retry_delay,
            multiplier=args.retry_multiplier,
            on_fallback=try_fallback if fallback_model else None,
        )
    except RetryExhausted as e:
        log_cost(model_id, args.size, len(args.prompt), estimated_cost,
                 False, str(e), args.cost_log)
        print(f"\n✘ Generation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        log_cost(model_id, args.size, len(args.prompt), estimated_cost,
                 False, str(e), args.cost_log)
        print(f"\n✘ Generation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Process results ──
    output_dir = args.output_dir or "."
    os.makedirs(output_dir, exist_ok=True)

    saved_files = []
    for i, img_data in enumerate(result.data):
        if args.response_format == "url" and hasattr(img_data, "url") and img_data.url:
            if args.output:
                filename = args.output if num_images == 1 else f"{Path(args.output).stem}_{i+1}{Path(args.output).suffix}"
            else:
                ext = "png" if args.output_format == "png" else "jpg"
                filename = f"generated_{int(time.time())}_{i+1}.{ext}"
            filepath = os.path.join(output_dir, filename)
            download_image(img_data.url, filepath)
            saved_files.append(filepath)
            print(f"  ✓ Saved: {filepath}")
        elif args.response_format == "b64_json" and hasattr(img_data, "b64_json"):
            if args.output:
                filename = args.output if num_images == 1 else f"{Path(args.output).stem}_{i+1}{Path(args.output).suffix}"
            else:
                ext = "png" if args.output_format == "png" else "jpg"
                filename = f"generated_{int(time.time())}_{i+1}.{ext}"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(img_data.b64_json))
            saved_files.append(filepath)
            print(f"  ✓ Saved: {filepath}")

    # ── Log cost ──
    actual_cost = estimated_cost  # Use estimate (API doesn't return exact cost)
    log_cost(current_model, args.size, len(args.prompt), actual_cost,
             True, "", args.cost_log)

    total = sum(e.get("estimated_cost_cny", 0) for e in
                json.load(open(args.cost_log)).get("entries", [])) \
            if os.path.exists(args.cost_log) else actual_cost

    print(f"\n  Cost this request: ~¥{actual_cost:.4f}")
    print(f"  Files saved: {len(saved_files)}")

    return saved_files


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate images via Volcengine Seedream API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Required ──
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation")

    # ── Model & Output ──
    parser.add_argument("--model", default="auto",
                        help="Model: auto, 5.0, 5.0-lite, 4.5, 4.0, or full model ID")
    parser.add_argument("--fallback-model", default=None,
                        help="Fallback model if primary fails after retries")
    parser.add_argument("--size", default="2K",
                        help="Resolution: 1K/2K/3K/4K or WxH (e.g. 2048x2048)")
    parser.add_argument("--output", "-o", default=None, help="Output filename")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--output-format", default="png",
                        choices=["png", "jpeg"], help="Output image format")
    parser.add_argument("--response-format", default="url",
                        choices=["url", "b64_json"], help="API response format")

    # ── Input Images ──
    parser.add_argument("--image", nargs="+", default=None,
                        help="Input image path(s) or URL(s) for image-to-image")

    # ── Sequential Generation ──
    parser.add_argument("--sequential", action="store_true",
                        help="Enable sequential image generation")
    parser.add_argument("--max-images", type=int, default=4,
                        help="Max images for sequential generation (default: 4)")

    # ── Advanced Features ──
    parser.add_argument("--web-search", action="store_true",
                        help="Enable web search (5.0 lite only)")
    parser.add_argument("--fast-mode", action="store_true",
                        help="Use fast prompt optimization (4.0 only)")
    parser.add_argument("--watermark", action="store_true",
                        help="Add AI-generated watermark")

    # ── Retry & Error Handling ──
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Max retry attempts (default: 3)")
    parser.add_argument("--retry-delay", type=float, default=1.0,
                        help="Initial retry delay in seconds (default: 1)")
    parser.add_argument("--retry-multiplier", type=float, default=2.0,
                        help="Backoff multiplier (default: 2)")

    # ── Cost Management ──
    parser.add_argument("--budget-limit", type=float, default=None,
                        help="Max cumulative spend in CNY")
    parser.add_argument("--cost-log", default=COST_LOG_DEFAULT,
                        help=f"Cost log JSON path (default: {COST_LOG_DEFAULT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Estimate cost without calling API")

    args = parser.parse_args()

    run_generation(args)


if __name__ == "__main__":
    main()
