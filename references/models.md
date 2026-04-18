# Model Comparison & Pricing Guide

## Available Models

| Attribute | Seedream 5.0 | Seedream 5.0 lite | Seedream 4.5 | Seedream 4.0 |
|---|---|---|---|---|
| **Model ID** | `doubao-seedream-5-0-260128` | `doubao-seedream-5-0-lite-260128` | `doubao-seedream-4-5-251128` | `doubao-seedream-4-0-250828` |
| **Tier** | High | Mid | High | Low |
| **Max Resolution** | 3K | 3K | 4K | 4K |
| **Output Formats** | PNG, JPEG | PNG, JPEG | JPEG | JPEG |
| **Web Search** | Yes | Yes | No | No |
| **Prompt Optimization** | Standard | Standard | Standard | Standard + Fast |
| **Rate Limit (IPM)** | 500 | 500 | 500 | 500 |

## Resolution Presets

### Seedream 5.0 lite — Recommended Pixel Values

| Aspect Ratio | 2K | 3K |
|---|---|---|
| 1:1 | 2048×2048 | 3072×3072 |
| 3:4 | 1728×2304 | 2592×3456 |
| 4:3 | 2304×1728 | 3456×2592 |
| 16:9 | 2848×1600 | 4096×2304 |
| 9:16 | 1600×2848 | 2304×4096 |
| 3:2 | 2496×1664 | 3744×2496 |
| 2:3 | 1664×2496 | 2496×3744 |
| 21:9 | 3136×1344 | 4704×2016 |

### Pixel Range Per Model

| Model | Min Pixels | Max Pixels |
|---|---|---|
| Seedream 5.0 lite | 3,686,400 (2560×1440) | 10,404,496 (3072×3072×1.1) |
| Seedream 4.5 | 3,686,400 (2560×1440) | 16,777,216 (4096×4096) |
| Seedream 4.0 | 921,600 (1280×720) | 16,777,216 (4096×4096) |

## Cost Estimation (Approximate, CNY per Image)

> **Note**: Actual pricing may vary. These are estimated costs for budgeting purposes.
> Check the Volcengine console for exact pricing.

| Resolution | Seedream 5.0 | Seedream 5.0 lite | Seedream 4.5 | Seedream 4.0 |
|---|---|---|---|---|
| 1K | ¥0.04 | ¥0.02 | ¥0.04 | ¥0.02 |
| 2K | ¥0.06 | ¥0.04 | ¥0.06 | ¥0.03 |
| 3K | ¥0.10 | ¥0.06 | ¥0.08 | ¥0.05 |
| 4K | ¥0.14 | ¥0.08 | ¥0.12 | ¥0.08 |

## Cost Optimization Strategies

### 1. Draft → Final Workflow
Use Seedream 4.0 at 1K for rapid prototyping (¥0.02/image), then generate the final version with 5.0 lite or 4.5 at higher resolution. This costs ~¥0.06 for two rounds instead of ¥0.10+ for multiple high-res attempts.

### 2. Batch Budget Planning
For N sequential images at resolution R with model M:
```
Total cost = N × cost_per_image(M, R)
```
Example: 4-frame storyboard with 5.0 lite at 2K = 4 × ¥0.04 = ¥0.16

### 3. Model Selection Decision Tree
```
Need web context? → 5.0 lite (only model with web search)
  ↓ No
Need PNG output? → 5.0 or 5.0 lite
  ↓ No (JPEG ok)
Need max 4K resolution? → 4.5 or 4.0
  ↓ No
Lowest cost? → 4.0
  ↓ No
Best value? → 5.0 lite (recommended default)
```

### 4. Fallback Chain
When cost is critical, configure a fallback chain:
```
Primary: 5.0 lite (¥0.04 @ 2K)
  ↓ on failure
Fallback: 4.0 (¥0.03 @ 2K)
```

## Input Image Constraints

| Constraint | Limit |
|---|---|
| Formats | JPEG, PNG, WebP, BMP, TIFF, GIF |
| Input method | Public URL or Base64 data URI |
| Aspect ratio range | 1:16 to 16:1 |
| Min dimension | 14px per side |
| Max file size | 10 MB per image |
| Max total pixels | 6000×6000 = 36M pixels |
| Max reference images | 14 per request |
| Total (input + output) | ≤ 15 images |

## Rate Limits

| Limit | Value |
|---|---|
| IPM (images/minute) | 500 (all models) |
| Data retention | 24 hours (save promptly) |
