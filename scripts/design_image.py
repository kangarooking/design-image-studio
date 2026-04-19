#!/usr/bin/env python3
"""
Design-aware wrapper for Volcengine image generation.

This script acts as a compiler:
1. User brief -> design reasoning
2. Design reasoning -> compiled brief
3. Compiled brief -> final image prompt
4. Final image prompt -> Volcengine generation
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

CORE_SOURCE_SECTIONS = [
    "## Your workflow",
    "## Output creation guidelines",
    "### How to do design work",
    "## Content Guidelines",
    "**Do not add filler content.**",
    "**Create a system up front:**",
    "**Avoid AI slop tropes:**",
]

TASK_SOURCE_SECTIONS = {
    "poster": [
        "### How to do design work",
        "## Content Guidelines",
        "**Do not add filler content.**",
    ],
    "product": [
        "## Output creation guidelines",
        "## Content Guidelines",
        "**Avoid AI slop tropes:**",
    ],
    "ppt": [
        "## Content Guidelines",
        "**Create a system up front:**",
        "**Use appropriate scales:**",
    ],
    "infographic": [
        "## Content Guidelines",
        "**Do not add filler content.**",
        "**Avoid AI slop tropes:**",
    ],
    "teaching": [
        "## Content Guidelines",
        "**Do not add filler content.**",
        "**Use appropriate scales:**",
    ],
}

DIRECTION_PROFILES = {
    "conservative": {
        "style_bias": "restrained, cleaner, corporate, polished, lower-risk",
        "energy_bias": "controlled, composed, authoritative",
        "composition_bias": "cleaner geometry, more negative space, lower background complexity",
        "palette_bias": "restricted palette with restrained accents",
        "detail_bias": "cleaner surfaces, less decorative detail",
    },
    "balanced": {
        "style_bias": "premium editorial, contemporary, polished, commercially strong",
        "energy_bias": "energetic but disciplined, confident, professional",
        "composition_bias": "clear hierarchy, dynamic but stable layout, deliberate focal contrast",
        "palette_bias": "premium neutrals with one strong accent family",
        "detail_bias": "hero-detail emphasis with a restrained background",
    },
    "bold": {
        "style_bias": "larger scale, more dramatic, more surprising, high-contrast",
        "energy_bias": "ambitious, high-energy, assertive, vivid",
        "composition_bias": "bolder crop, stronger scale contrast, more motion cues, still disciplined",
        "palette_bias": "higher-contrast palette with strong accent energy",
        "detail_bias": "high-impact hero detail, expressive texture, controlled spectacle",
    },
}

GLOBAL_DIRECTIVES = [
    "Start from purpose, audience, and channel rather than surface-level adjectives.",
    "Create a coherent visual system before detailing the image.",
    "Use one clear hero idea and preserve obvious hierarchy.",
    "Treat negative space and safe zones as design decisions, not leftover space.",
    "Avoid filler content, decorative noise, and meaningless visual data.",
    "Respect existing brand or context when available; if not, still commit to a clear direction.",
    "Avoid AI-slop tropes such as random HUD overlays, generic fog, empty gradients, and scattered floating debris.",
]

TASK_PROFILES = {
    "poster": {
        "communication_goal": "attract and persuade quickly in a campaign or recruitment context",
        "hero_strategy": "one dominant hero visual or symbolic concept, never a collage of equal-weight objects",
        "safe_zone": "reserve a clean, obvious text-safe zone in the upper third or one side for headline and CTA copy",
        "lighting": "crisp premium lighting with controlled contrast and energetic highlights",
        "palette": "restricted premium palette with disciplined neutrals and one energetic accent family",
        "detail_density": "hero-rich detail with restrained background complexity",
        "base_style": "editorial campaign key visual",
        "task_constraints": [
            "make the result feel campaign-ready rather than generic AI art",
            "prioritize focal hierarchy and typography-safe composition",
        ],
        "task_avoid": [
            "poster text rendered directly into the image unless explicitly requested",
            "random marketing icons and decorative interface fragments",
        ],
    },
    "product": {
        "communication_goal": "make the product feel desirable, premium, and commercially credible",
        "hero_strategy": "the product is the undisputed focal point with clear silhouette and edge readability",
        "safe_zone": "keep surrounding space supportive and uncluttered so the product remains dominant",
        "lighting": "commercial lighting that reveals material, finish, and shape without cheap reflections",
        "palette": "palette chosen to support product positioning rather than compete with the product",
        "detail_density": "high fidelity on the hero object, restrained props and background",
        "base_style": "high-end commercial product advertising",
        "task_constraints": [
            "preserve product proportions and perceived material integrity",
            "use props only when they reinforce product positioning",
        ],
        "task_avoid": [
            "oversized props stealing attention",
            "luxury claims paired with cheap lighting or noisy backgrounds",
        ],
    },
    "ppt": {
        "communication_goal": "support presentation storytelling with a clear, memorable visual metaphor",
        "hero_strategy": "a single strong metaphor or scene readable at presentation distance",
        "safe_zone": "reserve a large clean area for slide title and subtitle overlay",
        "lighting": "clean, legible lighting that supports shape readability over moodiness",
        "palette": "presentation-friendly palette with strong contrast and limited visual noise",
        "detail_density": "mid-detail image readable at a glance, not overloaded with tiny elements",
        "base_style": "presentation cover art",
        "task_constraints": [
            "favor readability from distance over excess detail",
            "keep enough room for future title placement",
        ],
        "task_avoid": [
            "ad-poster density",
            "tiny embedded text or fragile detail that disappears on slides",
        ],
    },
    "infographic": {
        "communication_goal": "communicate structure, grouping, and flow rather than literal dense data",
        "hero_strategy": "clear modular hierarchy with one dominant organizing principle",
        "safe_zone": "leave room for headings or labels without relying on the model to render tiny text",
        "lighting": "flat-to-controlled lighting that supports structure and clarity",
        "palette": "structured palette with clear grouping and low noise",
        "detail_density": "low-to-mid detail, with emphasis on grouping and directional logic",
        "base_style": "structured infographic-like visual system",
        "task_constraints": [
            "prioritize visual structure over fake data richness",
            "use symbolic clarity and modular composition",
        ],
        "task_avoid": [
            "tiny chart labels",
            "data slop, fake dashboards, and dense unreadable micro-details",
        ],
    },
    "teaching": {
        "communication_goal": "explain a process, comparison, or sequence with maximum clarity",
        "hero_strategy": "show the logic of the teaching point first, then add supporting visuals",
        "safe_zone": "keep panel or label areas simple and legible for later annotation",
        "lighting": "clear explanatory lighting, not overly cinematic",
        "palette": "clarity-first palette with simple grouping and controlled contrast",
        "detail_density": "mid-to-low detail with emphasis on readable sequence and large forms",
        "base_style": "instructional visual storytelling",
        "task_constraints": [
            "make sequence and cause-effect legible at first glance",
            "use big forms and obvious directional logic",
        ],
        "task_avoid": [
            "cinematic clutter that weakens explanation",
            "too many simultaneous steps in one frame",
        ],
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


def join_phrases(items: list[str]) -> str:
    return "; ".join(item for item in items if item)


def unique_preserving_order(items: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def make_design_reasoning(args: argparse.Namespace, task: str) -> dict:
    profile = TASK_PROFILES[task]
    direction = DIRECTION_PROFILES[args.direction]

    brand_strategy = (
        f"use the provided brand/context: {args.brand}"
        if args.brand
        else "no explicit brand provided; commit to one coherent visual system instead of averaging styles"
    )

    reference_strategy = (
        "use provided reference images to preserve consistency and context"
        if args.image
        else "no reference images provided; rely on the compiled visual system and brief"
    )

    source_sections = unique_preserving_order(CORE_SOURCE_SECTIONS + TASK_SOURCE_SECTIONS[task])

    visual_system = [
        f"base mode: {profile['base_style']}",
        f"direction bias: {direction['style_bias']}",
        f"energy bias: {direction['energy_bias']}",
        f"composition bias: {direction['composition_bias']}",
        f"palette bias: {direction['palette_bias']}",
    ]

    hierarchy_strategy = [
        "one clear hero idea",
        profile["hero_strategy"],
        "secondary elements must support the hero rather than compete with it",
        "background should create rhythm, not narrative confusion",
    ]

    anti_filler_rules = [
        "every element must earn its place",
        "do not add objects, labels, icons, or stats that do not strengthen the core message",
        "if the frame feels empty, solve with scale, crop, rhythm, or texture rather than random extra elements",
    ]

    anti_slop_rules = [
        "avoid generic AI clutter",
        "avoid random floating UI fragments or HUD overlays",
        "avoid generic gradient fog with no composition logic",
        "avoid cheap neon cyberpunk treatment unless explicitly requested",
        "avoid noisy micro-detail that weakens the hierarchy",
    ]

    if args.avoid:
        anti_slop_rules.append(args.avoid)

    return {
        "task": task,
        "direction": args.direction,
        "communication_goal": args.goal or profile["communication_goal"],
        "audience": args.audience or "broad professional audience",
        "channel": args.usage or task,
        "brief": args.brief.strip(),
        "brand_strategy": brand_strategy,
        "reference_strategy": reference_strategy,
        "visual_system": visual_system,
        "hierarchy_strategy": hierarchy_strategy,
        "safe_zone_strategy": args.safe_zone or profile["safe_zone"],
        "lighting_strategy": args.lighting or profile["lighting"],
        "palette_strategy": args.palette or profile["palette"],
        "detail_density": direction["detail_bias"] + "; " + profile["detail_density"],
        "style_direction": args.style or join_phrases(visual_system),
        "mood_direction": args.mood or direction["energy_bias"],
        "composition_logic": args.composition or direction["composition_bias"],
        "anti_filler_rules": anti_filler_rules,
        "anti_slop_rules": anti_slop_rules,
        "task_constraints": profile["task_constraints"] + ([args.constraints] if args.constraints else []),
        "task_avoid": profile["task_avoid"],
        "global_directives": GLOBAL_DIRECTIVES,
        "source_sections": source_sections,
        "primary_source_file": "references/claude-design-sys-prompt-full.txt",
    }


def compile_design_brief(reasoning: dict, aspect: str) -> dict:
    return {
        "task": reasoning["task"],
        "direction": reasoning["direction"],
        "brief": reasoning["brief"],
        "communication_goal": reasoning["communication_goal"],
        "audience": reasoning["audience"],
        "channel": reasoning["channel"],
        "brand_strategy": reasoning["brand_strategy"],
        "reference_strategy": reasoning["reference_strategy"],
        "visual_system": join_phrases(reasoning["visual_system"]),
        "hierarchy": join_phrases(reasoning["hierarchy_strategy"]),
        "composition": reasoning["composition_logic"],
        "safe_zone": reasoning["safe_zone_strategy"],
        "lighting": reasoning["lighting_strategy"],
        "palette": reasoning["palette_strategy"],
        "detail_density": reasoning["detail_density"],
        "style_direction": reasoning["style_direction"],
        "mood": reasoning["mood_direction"],
        "constraints": join_phrases(reasoning["task_constraints"]),
        "avoid": join_phrases(reasoning["anti_slop_rules"] + reasoning["task_avoid"]),
        "aspect": aspect,
        "source_sections": reasoning["source_sections"],
    }


def build_prompt(brief: dict) -> str:
    parts = [
        f"Create a {brief['task']} image for {brief['channel']} aimed at {brief['audience']}.",
        f"Treat this as a design-led visual solving this brief: {brief['brief']}.",
        f"Communication goal: {brief['communication_goal']}.",
        "Translate the brief into one strong hero concept rather than many equal-weight elements.",
        f"Brand and context strategy: {brief['brand_strategy']}.",
        f"Visual system: {brief['visual_system']}.",
        f"Hierarchy: {brief['hierarchy']}.",
        f"Composition: {brief['composition']}.",
        f"Safe zone: {brief['safe_zone']}.",
        f"Lighting: {brief['lighting']}.",
        f"Color strategy: {brief['palette']}.",
        f"Detail density: {brief['detail_density']}.",
        f"Style direction: {brief['style_direction']}.",
        f"Mood: {brief['mood']}.",
        f"Aspect ratio: {brief['aspect']}.",
        f"Important constraints: {brief['constraints']}.",
        f"Avoid: {brief['avoid']}.",
        "Emphasize strong hierarchy, intentional whitespace, disciplined background complexity, and polished professional finish.",
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
        description="Compile a design-system-driven brief into an image prompt and generate the image."
    )
    parser.add_argument("--task", default="auto", choices=["auto", "poster", "product", "ppt", "infographic", "teaching"])
    parser.add_argument("--brief", required=True, help="User brief or request")
    parser.add_argument("--audience", default=None, help="Target audience")
    parser.add_argument("--usage", default=None, help="Where the image will be used")
    parser.add_argument("--brand", default=None, help="Brand tone or reference context")
    parser.add_argument("--style", default=None, help="Preferred visual style override")
    parser.add_argument("--mood", default=None, help="Preferred mood override")
    parser.add_argument("--goal", default=None, help="Specific communication goal override")
    parser.add_argument("--composition", default=None, help="Composition override")
    parser.add_argument("--constraints", default=None, help="Must-have constraints")
    parser.add_argument("--avoid", default=None, help="Things to avoid")
    parser.add_argument("--aspect", default=None, help="Aspect ratio such as 1:1, 3:4, 16:9")
    parser.add_argument("--direction", default="balanced", choices=["conservative", "balanced", "bold"])
    parser.add_argument("--safe-zone", default=None, help="Safe-zone strategy override")
    parser.add_argument("--lighting", default=None, help="Lighting strategy override")
    parser.add_argument("--palette", default=None, help="Palette strategy override")
    parser.add_argument("--quality", default="final", choices=["draft", "final", "premium"])
    parser.add_argument("--model-override", default=None, help="Explicit model id override such as doubao-seedream-5-0-260128")
    parser.add_argument("--image", nargs="+", default=None, help="Reference image path(s) or URL(s)")
    parser.add_argument("--output", "-o", default=None, help="Output filename")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--output-format", default="png", choices=["png", "jpeg"])
    parser.add_argument("--response-format", default="b64_json", choices=["url", "b64_json"])
    parser.add_argument("--prompt-only", action="store_true", help="Only print design reasoning, compiled brief, and the final prompt")
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
    model = args.model_override or choose_model(args.quality)
    size = choose_size(task, args.aspect, args.quality)

    design_reasoning = make_design_reasoning(args, task)
    compiled_brief = compile_design_brief(design_reasoning, args.aspect)
    prompt = build_prompt(compiled_brief)

    print("[design_reasoning]")
    print(json.dumps(design_reasoning, ensure_ascii=False, indent=2))
    print("\n[compiled_brief]")
    print(json.dumps(compiled_brief, ensure_ascii=False, indent=2))
    print("\n[prompt]")
    print(prompt)
    print(f"\n[settings]\nmodel={model}\nsize={size}\naspect={args.aspect}\ndirection={args.direction}")
    sys.stdout.flush()

    if args.prompt_only:
        return 0

    return run_generation(args, prompt, task, model, size)


if __name__ == "__main__":
    raise SystemExit(main())
