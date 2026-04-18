# Design Compiler

`design-image-studio` should behave like a compiler:

1. **Read the full design system**
2. **Select the relevant design rules**
3. **Produce design reasoning**
4. **Condense that reasoning into a compiled brief**
5. **Translate the compiled brief into a short image-model prompt**

Do not skip directly from user brief to image prompt unless the user explicitly asks for a very short prompt.

## Stage 1: Read the Full Prompt

Always begin with:

- `claude-design-sys-prompt-full.txt`

Then use:

- `claude-design-map.md`
- task-specific references
- `anti-slop-and-failure-patterns.md` if refinement is needed

## Stage 2: Design Reasoning

Produce a `design_reasoning` object with fields like:

- `task`
- `communication_goal`
- `audience`
- `channel`
- `brand_strategy`
- `visual_system`
- `hierarchy_strategy`
- `safe_zone_strategy`
- `detail_density`
- `lighting_strategy`
- `palette_strategy`
- `anti_filler_rules`
- `anti_slop_rules`
- `direction`
- `source_sections`

This is where the full Claude design prompt should do most of its work.

## Stage 3: Compiled Brief

Compress the reasoning into a shorter `compiled_brief`:

- what the image is for
- what the viewer should notice first
- what kind of layout or safe zone must remain open
- what the visual system should feel like
- what must not appear

The compiled brief should still read like design thinking, not like raw model syntax.

## Stage 4: Final Image Prompt

Translate the compiled brief into a short prompt with:

- one clear hero idea
- scene or environment
- composition and framing
- lighting
- color system
- material or rendering style
- negative constraints

The final prompt should be much shorter than the design reasoning.

## Direction Modes

When the ask is ambiguous, explore with one of these modes:

- `conservative` — restrained, cleaner, safer, more corporate
- `balanced` — premium and energetic without overreaching
- `bold` — larger scale, stronger contrast, more experimental, but still disciplined

## Success Condition

The full Claude design-system prompt should still be visible in the intermediate reasoning layer, even if it is compressed before the actual generation call.

