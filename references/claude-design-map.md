# Claude Design Map

This file explains how `design-image-studio` should use the full Claude design-system prompt for image generation.

## Primary Rule

Do not replace the full prompt with this file. This file is only a routing map.

Primary source:

- `claude-design-sys-prompt-full.txt`

## Preserve These Sections Aggressively

These sections contain the design judgment that should survive into image-generation reasoning:

- `## Your workflow`
- `## Output creation guidelines`
- `### How to do design work`
- `## Content Guidelines`
- `**Do not add filler content.**`
- `**Ask before adding material.**`
- `**Create a system up front:**`
- `**Use appropriate scales:**`
- `**Avoid AI slop tropes:**`

## Use These Ideas at the Reasoning Layer

When compiling for image generation, carry forward these ideas explicitly:

1. Start from purpose, audience, and output context
2. Build a coherent visual system before detailing the image
3. Prefer hierarchy, rhythm, and negative space over decorative clutter
4. Every element should earn its place
5. If context or brand exists, use it
6. If context does not exist, still choose a strong direction
7. Explore multiple directions when the ask is ambiguous
8. Surprise the user with strong visual design, but keep the result usable

## Task Mapping

### Poster

Most relevant source ideas:

- one dominant visual idea
- typography-safe or CTA-safe space
- high contrast and emotional direction
- campaign rather than generic web-art energy

### Product

Most relevant source ideas:

- visual system and brand consistency
- material and lighting discipline
- avoid decorative clutter
- hero-object clarity

### PPT

Most relevant source ideas:

- slide-safe composition
- readability from distance
- broad shapes over small details
- room for titles and supporting copy

### Infographic

Most relevant source ideas:

- structure over spectacle
- no data slop
- no filler labels
- grouped modules and clear hierarchy

### Teaching

Most relevant source ideas:

- clarity over cinematic excess
- visible sequence and logic
- limited background distraction
- strong explanatory hierarchy

## Down-Weight or Ignore for Image Prompt Compilation

Keep these in the repository, but do not push them directly into the image prompt:

- React/Babel details
- HTML file management
- `done`, verifier, file tools, GitHub tooling
- tweaks protocol
- deck speaker notes plumbing
- cross-project file path rules

These are implementation details for artifact creation, not useful content for a text-to-image model.

