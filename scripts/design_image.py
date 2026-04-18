#!/usr/bin/env python3
"""
Design-aware wrapper for Volcengine image generation.

Turns a loose creative brief into:
1. a structured design brief
2. a design-directed image prompt
3. a direct Volcengine generation call
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


TASK_KEYWORDS = {
    "poster": ["海报", "poster", "封面", "主视觉", "campaign", "kv"],
    "product": ["商品", "产品", "电商", "product", "hero shot", "广告图", "首图"],
    "ppt": ["ppt", "幻灯片", "演示", "deck", "slide", "配图", "章节页"],
    "infographic": ["信息图", "infographic", "流程图", "结构图", "总结图", "overview"],
    "teaching": ["教学", "演示图", "讲解", "培训", "课件", "步骤图", "demo"],
}

DEFAULT_ASPECT = {
    "poster": "3:4",
    "product": "1:1",
    "ppt": "16:9",
    "infographic": "4:3",
    "teaching": "16:9",
}

QUALITY_MODEL = {
    "draft": "doubao-seedream-4-0-250828",
    "final": "doubao-seedream-5-0-lite-260128",
    "premium": "doubao-seedream-4-5-251128",
}

ASPECT_SIZES = {
    "1:1": {"2K": "2048x2048", "3K": "3072x3072"},
    "3:4": {"2K": "1728x2304", "3K": "2592x3456"},
    "4:3": {"2K": "2304x1728", "3K": "3456x2592"},
    "16:9": {"2K": "2848x1600", "3K": "4096x2304"},
    "9:16": {"2K": "1600x2848", "3K": "2304x4096"},
    "3:2": {"2K": "2496x1664", "3K": "3744x2496"},
    "2:3": {"2K": "1664x2496", "3K": "2496x3744"},
    "4:5": {"2K": "1840x2304", "3K": "2760x3456"},
}

TASK_GUIDANCE = {
    "poster": {
        "goal": "create a striking poster-like key visual with an obvious focal hierarchy",
        "composition": "one dominant hero element, clean typography-safe space, disciplined background complexity",
        "constraints": "leave a clean negative-space region for headline placement, avoid generic floating decoration",
    },
    "product": {
        "goal": "create a commercial product visual that highlights material, shape, and desirability",
        "composition": "hero product dominant in frame, supportive props only, premium commercial lighting",
        "constraints": "preserve product proportions and finish, keep the product as the undisputed focal point",
    },
    "ppt": {
        "goal": "create a presentation-friendly visual that reads quickly on slides",
        "composition": "broad readable shapes, moderate detail, obvious text-safe area for title and subtitle",
        "constraints": "do not overcrowd the slide, avoid poster-level density, avoid tiny text in the image",
    },
    "infographic": {
        "goal": "create a structured infographic-like visual that communicates grouping and flow",
        "composition": "modular blocks, clear directional logic, large symbolic elements, low text density",
        "constraints": "avoid dense small labels and fake chart text, focus on structure rather than precise data rendering",
    },
    "teaching": {
        "goal": "create a teaching-oriented explanatory visual that makes sequence and logic easy to understand",
        "composition": "clear stage-by-stage logic, obvious progression, limited distraction, large readable forms",
        "constraints": "prioritize clarity over cinematic spectacle, keep labels minimal and large",
    },
}


def detect_task(brief: str) -> str:
    text = brief.lower()
    scores = {}
    for task, keywords in TASK_KEYWORDS.items():
        scores[task] = sum(1 for keyword in keywords if keyword.lower() in text)
    best_task = max(scores, key=scores.get)
    return best_task if scores[best_task] > 0 else "poster"


def normalize_task(task: str, brief: str) -> str:
    return detect_task(brief) if task == "auto" else task


def choose_model(quality: str) -> str:
    return QUALITY_MODEL[quality]


def choose_size(task: str, aspect: str, quality: str) -> str:
    tier = "2K" if quality == "draft" or task in {"ppt", "infographic", "teaching"} else "3K"
    return ASPECT_SIZES.get(aspect, ASPECT_SIZES[DEFAULT_ASPECT[task]])[tier]


def make_design_brief(args: argparse.Namespace, task: str) -> dict:
    guidance = TASK_GUIDANCE[task]
    return {
        "task": task,
        "goal": args.goal or guidance["goal"],
        "brief": args.brief.strip(),
        "audience": args.audience or "broad professional audience",
        "usage": args.usage or task,
        "brand": args.brand or "no explicit brand provided; build a coherent visual system",
        "style": args.style or "high-end contemporary design direction",
        "mood": args.mood or "clear, intentional, polished",
        "aspect": args.aspect,
        "composition": args.composition or guidance["composition"],
        "constraints": args.constraints or guidance["constraints"],
        "avoid": args.avoid or (
            "generic AI clutter, messy floating elements, unreadable tiny text, weak focal hierarchy"
        ),
    }


def build_prompt(brief: dict) -> str:
    parts = [
        f"Create a {brief['task']} image for {brief['usage']} aimed at {brief['audience']}.",
        f"Primary brief: {brief['brief']}.",
        f"Visual goal: {brief['goal']}.",
        f"Brand/context: {brief['brand']}.",
        f"Style direction: {brief['style']}.",
        f"Mood and energy: {brief['mood']}.",
        f"Composition: {brief['composition']}.",
        f"Aspect ratio: {brief['aspect']}.",
        f"Important constraints: {brief['constraints']}.",
        f"Avoid: {brief['avoid']}.",
        "Emphasize clean hierarchy, intentional negative space, and a polished professional finish.",
    ]
    return " ".join(parts)


def run_generation(
    args: argparse.Namespace,
    prompt: str,
    task: str,
    model: str,
    size: str,
) -> int:
    skill_root = Path(__file__).resolve().parent
    generate_script = skill_root / "generate.py"

    command = [
        sys.executable,
        str(generate_script),
        "--prompt",
        prompt,
        "--model",
        model,
        "--size",
        size,
        "--response-format",
        args.response_format,
        "--output-format",
        args.output_format,
    ]

    if args.output:
        command.extend(["--output", args.output])
    if args.output_dir:
        command.extend(["--output-dir", args.output_dir])
    if args.budget_limit is not None:
        command.extend(["--budget-limit", str(args.budget_limit)])
    if args.dry_run:
        command.append("--dry-run")
    if args.web_search:
        command.append("--web-search")
    if args.fast_mode:
        command.append("--fast-mode")
    if args.watermark:
        command.append("--watermark")
    if args.fallback_model:
        command.extend(["--fallback-model", args.fallback_model])
    if args.image:
        command.extend(["--image", *args.image])

    if task in {"teaching", "infographic"} and args.sequential:
        command.append("--sequential")
        command.extend(["--max-images", str(args.max_images)])

    print("\n[command]")
    print(" ".join(shlex.quote(part) for part in command))
    sys.stdout.flush()
    result = subprocess.run(command, check=False)
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turn a design brief into a prompt and directly generate the image."
    )
    parser.add_argument("--task", default="auto", choices=["auto", "poster", "product", "ppt", "infographic", "teaching"])
    parser.add_argument("--brief", required=True, help="User brief or request")
    parser.add_argument("--audience", default=None, help="Target audience")
    parser.add_argument("--usage", default=None, help="Where the image will be used")
    parser.add_argument("--brand", default=None, help="Brand tone or reference context")
    parser.add_argument("--style", default=None, help="Preferred visual style")
    parser.add_argument("--mood", default=None, help="Preferred mood")
    parser.add_argument("--goal", default=None, help="Specific communication goal")
    parser.add_argument("--composition", default=None, help="Composition override")
    parser.add_argument("--constraints", default=None, help="Must-have constraints")
    parser.add_argument("--avoid", default=None, help="Things to avoid")
    parser.add_argument("--aspect", default=None, help="Aspect ratio such as 1:1, 3:4, 16:9")
    parser.add_argument("--quality", default="final", choices=["draft", "final", "premium"])
    parser.add_argument("--image", nargs="+", default=None, help="Reference image path(s) or URL(s)")
    parser.add_argument("--output", "-o", default=None, help="Output filename")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--output-format", default="png", choices=["png", "jpeg"])
    parser.add_argument("--response-format", default="b64_json", choices=["url", "b64_json"])
    parser.add_argument("--prompt-only", action="store_true", help="Only print the design brief and final prompt")
    parser.add_argument("--budget-limit", type=float, default=None, help="Optional spend guard in CNY")
    parser.add_argument("--fallback-model", default=None, help="Fallback model id")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost without generating")
    parser.add_argument("--web-search", action="store_true", help="Enable web search if the selected model supports it")
    parser.add_argument("--fast-mode", action="store_true", help="Enable fast mode for compatible models")
    parser.add_argument("--watermark", action="store_true", help="Enable output watermark")
    parser.add_argument("--sequential", action="store_true", help="Generate sequential images for explanatory series")
    parser.add_argument("--max-images", type=int, default=4, help="Max images for sequential generation")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task = normalize_task(args.task, args.brief)
    args.aspect = args.aspect or DEFAULT_ASPECT[task]
    model = choose_model(args.quality)
    size = choose_size(task, args.aspect, args.quality)

    design_brief = make_design_brief(args, task)
    prompt = build_prompt(design_brief)

    print("[design_brief]")
    print(json.dumps(design_brief, ensure_ascii=False, indent=2))
    print("\n[prompt]")
    print(prompt)
    print(f"\n[settings]\nmodel={model}\nsize={size}\naspect={args.aspect}")
    sys.stdout.flush()

    if args.prompt_only:
        return 0

    return run_generation(args, prompt, task, model, size)


if __name__ == "__main__":
    raise SystemExit(main())
