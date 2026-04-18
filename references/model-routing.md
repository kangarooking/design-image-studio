# Model Routing

Use these defaults when calling the bundled Volcengine generator.

## Default Model Choice

- Draft exploration: `doubao-seedream-4-0-250828`
- Default final output: `doubao-seedream-5-0-lite-260128`
- Premium rerun when realism/material is critical: `doubao-seedream-4-5-251128`

## Resolution Strategy

- Posters and product visuals: 3K when final quality matters
- PPT visuals: 2K is usually enough unless the image will be full-bleed on large screens
- Infographics and teaching visuals: 2K by default; increase only if the composition is detail-heavy

## Aspect Recommendations

- Poster: `3:4`, `2:3`, `9:16`, sometimes `1:1`
- Product: `1:1`, `4:5`, `16:9`
- PPT: `16:9`
- Infographic: `4:3`, `3:4`, `16:9`
- Teaching: `16:9`, `4:3`

## Execution Rules

- If the user supplies reference images, pass them through `--image`
- If the design still feels unresolved, run a draft first
- Prefer changing one major variable per rerun
- Use `--dry-run` if the user is cost-sensitive or asking for many variants

