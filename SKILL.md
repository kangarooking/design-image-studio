name: design-image-studio
description: Directly generate design-oriented AI images with strong creative direction and prompt engineering. Use this skill for posters, product visuals, PPT illustrations, infographics, teaching/demo diagrams, campaign key visuals, cover art, or when the user wants design-quality image generation rather than generic AI art. This skill turns a loose brief into a design brief, assembles a structured prompt, routes to the right Volcengine Seedream settings, and can generate the image immediately.
---

# Design Image Studio

Generate design-quality images directly. This skill combines:

- Design-direction rules distilled from `Claude-Design-Sys-Prompt.txt`
- Structured prompt assembly for creative and commercial visuals
- Direct execution through the bundled Volcengine Seedream scripts

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
2. Read the relevant reference files:
   - Always: `references/design-principles.md`, `references/prompt-framework.md`, `references/model-routing.md`
   - Then the matching task file, such as `references/poster.md`
   - If the user is asking for a refined result or previous images looked weak, read `references/anti-slop-and-failure-patterns.md`
3. Convert the user request into a compact design brief:
   - goal
   - audience
   - channel or usage context
   - visual focus
   - composition strategy
   - palette and mood
   - constraints and avoid-list
4. Generate a structured image prompt with:
   - subject
   - scene
   - composition
   - lighting
   - material/texture
   - color system
   - text-safe or layout-safe zones when needed
   - failure prevention constraints
5. Run `scripts/design_image.py` to generate directly, unless the user explicitly asks for prompt-only output
6. If needed, iterate by changing one variable at a time: composition, lighting, palette, realism, or density

## Primary Command

Use the wrapper script first. It is the opinionated entry point for this skill.

```bash
python3 scripts/design_image.py \
  --task poster \
  --brief "为 AI 训练营生成一张高冲击力招生海报，强调增长、实战和速度" \
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

## Task References

- `references/poster.md` — posters, key visuals, covers
- `references/product-image.md` — product ads, hero shots, e-commerce visuals
- `references/ppt-visual.md` — slide cover art, chapter visuals, concept illustrations
- `references/infographic.md` — infographic-like visuals and structured information compositions
- `references/teaching-demo.md` — educational and explanatory diagrams/scenes

## Execution Notes

- Prefer `Seedream 5.0 lite` as the default final model
- Use lower-cost draft settings before premium reruns when the direction is still unclear
- Use image-to-image or multi-image fusion when the user provides source materials
- For infographic or teaching visuals, avoid asking the model to render dense, tiny text accurately; prefer text placeholders or low-text compositions
- The wrapper script prints the assembled design brief and final prompt before generation so you can inspect and refine if needed

## Files

- `scripts/design_image.py` — design-aware wrapper and prompt builder
- `scripts/generate.py` — bundled Volcengine generation engine
- `references/models.md` — model and resolution reference
- `references/troubleshooting.md` — common error handling
