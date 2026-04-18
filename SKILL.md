---
name: design-image-studio
description: Directly generate design-oriented AI images with strong creative direction and prompt engineering. Use this skill for posters, product visuals, PPT illustrations, infographics, teaching/demo diagrams, campaign key visuals, cover art, or when the user wants design-quality image generation rather than generic AI art. This skill turns a loose brief into a design brief, assembles a structured prompt, routes to the right Volcengine Seedream settings, and can generate the image immediately.
---

# Design Image Studio

Generate design-quality images directly. This skill preserves the full Claude design-system prompt as the upstream design brain, then compiles that design logic into a shorter image-model prompt.

## Primary Source of Truth

Do not treat `references/design-principles.md` as the whole design system. It is only an index.

The primary design source is:

- `references/claude-design-sys-prompt-full.txt`

Always read that file first for substantive design work. Then use:

- `references/claude-design-map.md`
- `references/design-compiler.md`
- the task-specific reference file for the current request

This skill should preserve as much of the original design-system prompt as possible at the reasoning layer, while stripping away HTML/tool-specific noise before handing a prompt to the image model.

## When to Use

Use this skill when the user wants any of the following:

- Poster generation
- Product hero images, ad visuals, or e-commerce scenes
- PPT cover art, chapter art, or slide illustrations
- Infographic-style visuals
- Teaching/demo diagrams or explanatory scenes
- Visual concept exploration with stronger art direction than a generic image prompt

Do not use this skill for pixel-accurate UI recreation, editable charts, or layouts that require precise text rendering. For those, generate HTML/SVG/PPT assets instead.

## Default Workflow

1. Classify the request into one of: `poster`, `product`, `ppt`, `infographic`, `teaching`, or `auto`
2. Read the full design system prompt:
   - `references/claude-design-sys-prompt-full.txt`
3. Read the compiler references:
   - `references/claude-design-map.md`
   - `references/design-compiler.md`
   - `references/model-routing.md`
4. Read the matching task file, such as `references/poster.md`
5. If the user wants refinement or the first result is weak, also read:
   - `references/anti-slop-and-failure-patterns.md`
6. Compile the full design system into a `design_reasoning` layer:
   - purpose
   - audience
   - channel
   - context/brand strategy
   - visual system
   - hierarchy strategy
   - safe-zone or text-zone logic
   - anti-filler rules
   - anti-slop rules
   - task-specific design constraints
7. Condense the reasoning into a `compiled_brief`
8. Translate the compiled brief into the shortest useful image prompt
9. Run `scripts/design_image.py` to generate directly, unless the user explicitly asks for prompt-only output
10. Iterate by changing one major variable at a time: direction, hierarchy, palette, lighting, realism, or density

## What Must Be Preserved From the Full Prompt

These must survive the compilation process:

- Start from purpose, audience, and channel
- Create a coherent visual system up front
- Treat hierarchy and whitespace as design decisions
- Avoid filler content and decorative noise
- Avoid AI-slop tropes
- Respect brand/context when available
- If no context exists, still commit to a strong direction instead of averaging styles
- Prefer multiple directions for ambiguous work, usually `conservative`, `balanced`, and `bold`

## Primary Command

Use the wrapper script first. It is the opinionated entry point for this skill.

```bash
python3 scripts/design_image.py \
  --task poster \
  --brief "为 AI 训练营生成一张高冲击力招生海报，强调增长、实战和速度" \
  --direction balanced \
  --aspect 3:4 \
  --quality final \
  --output training-poster.png
```

## Prompt-Only Mode

If the user only wants prompts, do:

```bash
python3 scripts/design_image.py \
  --task product \
  --brief "高端陶瓷咖啡杯广告图，适合电商首图" \
  --prompt-only
```

The wrapper prints:

- `design_reasoning`
- `compiled_brief`
- final `prompt`

Use those intermediate layers to judge whether the full design-system prompt has actually been preserved.

## Task References

- `references/poster.md` — posters, key visuals, covers
- `references/product-image.md` — product ads, hero shots, e-commerce visuals
- `references/ppt-visual.md` — slide cover art, chapter visuals, concept illustrations
- `references/infographic.md` — infographic-like visuals and structured information compositions
- `references/teaching-demo.md` — educational and explanatory diagrams/scenes
- `references/claude-design-map.md` — which sections of the full design prompt matter for image generation
- `references/design-compiler.md` — how to compile the full prompt into design reasoning, a compiled brief, and a final image prompt

## Execution Notes

- Prefer `Seedream 5.0 lite` as the default final model
- Use lower-cost draft settings before premium reruns when the direction is still unclear
- Use image-to-image or multi-image fusion when the user provides source materials
- For infographic or teaching visuals, avoid asking the model to render dense, tiny text accurately; prefer text placeholders or low-text compositions
- The wrapper script is not the design brain; it is the compiler between the full design system and the image model
- Do not collapse the full design prompt into a few style adjectives unless the user explicitly wants a minimal prompt

## Files

- `scripts/design_image.py` — design compiler and prompt builder
- `scripts/generate.py` — bundled Volcengine generation engine
- `references/claude-design-sys-prompt-full.txt` — full upstream design-system prompt
- `references/claude-design-map.md` — section map for image use
- `references/design-compiler.md` — compilation workflow
- `references/models.md` — model and resolution reference
- `references/troubleshooting.md` — common error handling
