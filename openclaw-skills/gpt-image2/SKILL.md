---
name: gpt-image2
description: 'Use when the user asks Codex to directly generate images with gpt-image-2 using inherited OpenAI/Codex-compatible environment credentials or local GPT_IMAGE2_* overrides, including text-to-image, reference-image guided generation, ratios, resolution, quality, variants, and saved local image files; run the bundled Node CLI and keep URL/sk configuration private.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
license: MIT
tags: '["codex", "gpt-image-2", "image-generation", "multimodal"]'
created_at: "2026-06-24"
updated_at: "2026-06-24"
quality: 4
complexity: "intermediate"
zh_description: "让 Codex 通过本地配置的 gpt-image-2 兼容画图服务生成图片，支持提示词、参考图、比例、清晰度和本地保存。"
---

# GPT Image 2

This skill lets Codex behave like a drawing assistant that can call a `gpt-image-2` compatible image service. It first tries to inherit OpenAI/Codex-compatible environment credentials already exposed to the current process, then reads the current Codex provider base URL from `~/.codex/config.toml` and the Codex `OPENAI_API_KEY` from `~/.codex/auth.json`, and it also supports local `GPT_IMAGE2_*` overrides. It is for direct generation from the current machine: interpret the user's visual request, run the bundled CLI, save the returned image files, and report the local paths.

Use the existing `imagegen` skill when the user needs the official OpenAI Image API workflow with editing, masking, background work, or broader project asset generation. Use this skill when the user specifically wants this gpt-image-2 compatible drawing path, inherited Codex/OpenAI-style credentials, a configured URL/sk pair, or a simple "Codex, draw this for me" workflow backed by `scripts/gpt-image2.mjs`.

## When to Use

- The user asks Codex to draw, generate, create, render, or make a new image through the configured drawing service.
- The user mentions `gpt-image-2`, `gpt-image2`, inherited Codex/OpenAI credentials, a local drawing channel, URL/sk configuration, or the included `gpt-image2.mjs` script.
- The request is text-to-image with optional reference images, image count, resolution, aspect ratio, quality, and output directory.
- The user wants saved local image files rather than prompt advice or sample API code.
- The user asks to validate request shape with a dry run or check an official-compatible image API mode.

Do not use this skill for mask-based editing, local canvas repainting, inpainting, background removal, or precise retouch workflows. Route those to a more suitable image editing skill if one is available.

## Core Capabilities

- Text-to-image generation from natural-language prompts.
- Reference-image guided generation with 1 to 16 local image files.
- Prompt-only multi-variant output with `-n`.
- Resolution controls: `1k`, `2k`, `4k`.
- Aspect-ratio controls: `1:1`, `3:2`, `2:3`, `4:3`, `3:4`, `5:4`, `4:5`, `16:9`, `9:16`, `2:1`, `1:2`, `21:9`, `9:21`.
- Quality controls: `auto`, `low`, `medium`, `high`.
- Local output directory selection.
- Dry-run inspection of URL, JSON body, multipart fields, and reference image metadata.

Reference-image requests currently save only the first returned image even if the user asks for multiple variants. Explain this only when it affects the user's request.

## Configuration Resolution

For normal use, do not ask the user for configuration before checking whether credentials are already available. The CLI resolves configuration in this order:

1. Command-line flags such as `--api-key`, `--base-url`, and other explicit flags.
2. Process environment variables, with `GPT_IMAGE2_*` first.
3. `scripts/.env`, with `GPT_IMAGE2_*` first.
4. Codex local config fallbacks: current provider `base_url` from `~/.codex/config.toml`, and `OPENAI_API_KEY` from `~/.codex/auth.json`.
5. Built-in defaults for non-secret settings.

Secret and endpoint variables resolve as:

```text
API key:  GPT_IMAGE2_API_KEY -> OPENAI_API_KEY -> CODEX_OPENAI_API_KEY -> Codex auth.json OPENAI_API_KEY
Base URL: GPT_IMAGE2_BASE_URL -> OPENAI_BASE_URL -> OPENAI_API_BASE_URL -> OPENAI_API_BASE -> CODEX_OPENAI_BASE_URL -> CODEX_OPENAI_API_BASE_URL -> current Codex model_provider base_url
```

This lets the skill use the same OpenAI-compatible key and base URL as the surrounding Codex configuration, including official API endpoints or third-party relay endpoints. It does not hard-code the official OpenAI endpoint. It reads only the local Codex config/auth fields needed for this API call and never prints the API key. It does not read session tokens, browser storage, or hidden app state.

If `scripts/.env` does not exist and the environment is missing required values, copy `scripts/.env.example` to `scripts/.env`. Never commit `scripts/.env`; it is ignored because it may contain secrets.

If the API key is still missing, do not generate yet. Ask the user in Chinese or the user's language:

```text
当前进程和 Codex auth.json 都没有可用于画图接口的 API key。请设置 GPT_IMAGE2_API_KEY 或 OPENAI_API_KEY；画图接口 URL 默认会读取 Codex 当前模型提供商的 base_url，也可以用 GPT_IMAGE2_BASE_URL 覆盖。
```

Write configuration values to `scripts/.env`:

- URL -> `GPT_IMAGE2_BASE_URL`
- sk -> `GPT_IMAGE2_API_KEY`
- default count -> `GPT_IMAGE2_N`
- default resolution -> `GPT_IMAGE2_RESOLUTION`
- default aspect ratio -> `GPT_IMAGE2_ASPECT_RATIO`
- default quality -> `GPT_IMAGE2_QUALITY`
- default output directory -> `GPT_IMAGE2_OUT_DIR`

When optional defaults are omitted, write the defaults explicitly:

```dotenv
GPT_IMAGE2_MODEL=gpt-image-2
GPT_IMAGE2_MODE=current
GPT_IMAGE2_N=1
GPT_IMAGE2_RESOLUTION=1k
GPT_IMAGE2_ASPECT_RATIO=1:1
GPT_IMAGE2_QUALITY=
GPT_IMAGE2_OUT_DIR=./image2_output
GPT_IMAGE2_TIMEOUT_MS=240000
```

After writing `.env`, tell the user the effective drawing defaults in natural language. Do not print the API key or token value.

## Normal Workflow

1. Identify the actual image prompt.
   Keep it close to the user's words. Expand or polish it only when the user asks for that, or when a tiny amount of structure helps preserve their stated constraints.

2. Detect reference images.
   If the user provides local image paths or attached images that should guide the output, pass each one with `--image`. Validate that paths exist before calling the script.

3. Infer count.
   Use the configured default count unless the user asks for multiple drafts, variants, or a specific number. Use multiple outputs only for prompt-only requests.

4. Infer resolution.
   Use the configured default unless the request implies a higher one. Use `2k` for requests like "高清", "more detail", or "sharper". Use `4k` for "4K", "ultra high resolution", "poster grade", "large print", or "big wallpaper".

5. Infer aspect ratio.
   Use an explicit ratio when provided. Use `9:16` or `3:4` for phone wallpapers, vertical posters, and portraits. Use `16:9` for desktop wallpapers, video covers, wide banners, and cinematic landscapes. Otherwise use the configured default.

6. Infer quality.
   Use the configured default. If blank, the current drawing path falls back to low quality. Use `high` or `medium` only when the user asks for high detail, premium polish, print quality, small text, or a named quality level.

7. Execute generation.
   Run `scripts/gpt-image2.mjs` from this skill directory. For long prompts, pass `--prompt` rather than relying on shell positionals.

8. Report results.
   Give the saved local file path(s), plus concise actionable errors if configuration is missing, the request is rejected, the response has no image payload, or a download fails.

## User-Facing Language

Normal replies should sound like a drawing assistant, not an API wrapper. Prefer wording such as:

- "当前画图服务"
- "默认画图通道"
- "这次生成"
- "保存到了..."
- "当前画图服务还没配置好"

Avoid internal terms unless the user is configuring or debugging:

- endpoint
- upstream
- provider
- request body
- env var
- sk, except when explicitly configuring
- supplier or channel names
- command-line flags

If configuration is missing outside setup, ask only for the missing pieces:

```text
当前进程和 Codex auth.json 都没有可用于画图接口的 API key。请设置 GPT_IMAGE2_API_KEY 或 OPENAI_API_KEY。
```

## Execution Examples

Run from `skills/multimodal-media/gpt-image2`:

```bash
node scripts/gpt-image2.mjs --prompt "生成一张雨夜街头的电影感海报"
node scripts/gpt-image2.mjs --prompt "生成一张雨夜街头的电影感海报" -n 4
node scripts/gpt-image2.mjs --prompt "生成一张雨夜街头的电影感海报" --resolution 4k --aspect-ratio 16:9
node scripts/gpt-image2.mjs --prompt "生成一张手机壁纸，国风女孩头像" --resolution 4k --aspect-ratio 9:16 --quality high
node scripts/gpt-image2.mjs --prompt "参考两张图，生成一张同风格海报" --image C:/path/ref-1.png --image C:/path/ref-2.jpg --resolution 2k --aspect-ratio 16:9
node scripts/gpt-image2.mjs --dry-run --prompt "检查请求体" --resolution 2k --aspect-ratio 16:9
node scripts/gpt-image2.mjs --dry-run --prompt "检查参考图请求形态" --image C:/path/reference.png
```

Use `--dry-run` only for internal validation or when the user explicitly asks to inspect request shape. Do not use it for normal generation.

## Configuration Reference

The CLI reads command-line flags first, then process environment variables, then `scripts/.env`, then Codex local config/auth fallbacks, then defaults for non-secret settings. `GPT_IMAGE2_*` variables are the skill-specific override layer. Standard OpenAI/Codex-compatible variables are fallback layers so the skill can use the same visible key/base URL as Codex when the runtime exposes them.

```dotenv
GPT_IMAGE2_API_KEY=
GPT_IMAGE2_BASE_URL=
GPT_IMAGE2_MODEL=gpt-image-2
GPT_IMAGE2_MODE=current
GPT_IMAGE2_N=1
GPT_IMAGE2_RESOLUTION=1k
GPT_IMAGE2_ASPECT_RATIO=1:1
GPT_IMAGE2_QUALITY=
GPT_IMAGE2_OUT_DIR=./image2_output
GPT_IMAGE2_TIMEOUT_MS=240000
```

If `GPT_IMAGE2_BASE_URL` is blank, the script falls back to `OPENAI_BASE_URL`, `OPENAI_API_BASE_URL`, `OPENAI_API_BASE`, `CODEX_OPENAI_BASE_URL`, `CODEX_OPENAI_API_BASE_URL`, and then the active `model_provider` `base_url` in `~/.codex/config.toml`.

If `GPT_IMAGE2_API_KEY` is blank, the script falls back to `OPENAI_API_KEY`, `CODEX_OPENAI_API_KEY`, and then `OPENAI_API_KEY` in `~/.codex/auth.json`.

`GPT_IMAGE2_BASE_URL` should be the service root. The script appends `/images/generations` for prompt-only requests and `/images/edits` for reference-image requests.

Do not put API keys in shared docs, command history, screenshots, or generated output. Prefer environment variables or `scripts/.env`, which is ignored by git.

`GPT_IMAGE2_MODE=current` is the normal mode. Use `--mode official-compatible` only when the user explicitly wants to test or inspect an official-compatible request shape.

## Request Details

Prompt-only requests use a JSON generation path:

```json
{
  "model": "gpt-image-2",
  "prompt": "user prompt",
  "n": 1,
  "size": "1024x1024",
  "quality": "low"
}
```

Reference-image requests use multipart form data:

```text
model=gpt-image-2
prompt=<user prompt>
size=<resolved size>
quality=<optional quality>
image=<repeated local file fields>
```

Do not send `n` or `response_format` for reference-image requests. Save only the first returned image for reference-image requests.

## Output Handling

The script saves images from these response forms:

- `data[].b64_json` as raw Base64.
- `data[].b64_json` as `data:image/...;base64,...`.
- `data[].url` by downloading the returned URL.

If the response contains no usable image payload, report that the generation returned no image. If URL download fails, report the download failure instead of retrying indefinitely.

Generated files default to `scripts/image2_output/`, which is ignored by git.

## Prompt Guidance

When the user seems unsure how to describe the image, offer a compact prompt scaffold:

```text
你可以直接告诉我想画什么，也可以补充这些信息：参考图、生成几张、图片比例、清晰度、质量要求、保存位置。

例如：
"画一张赛博朋克雨夜街头，横版 16:9，2K，低质量，生成 2 张。"
"画一个国风女孩头像，方图，默认配置。"
"画一张手机壁纸，9:16，4K，高质量。"
"参考这两张图，生成一张同风格海报，16:9，2K。"
```

For production-like prompts, structure internally as:

```text
Primary request: <what to draw>
Subject: <main subject>
Scene/background: <environment>
Style/medium: <photo, illustration, 3D, poster, etc.>
Composition/framing: <close-up, wide, centered, negative space, etc.>
Lighting/mood: <lighting and emotion>
Color palette: <optional color anchors>
Text: "<exact text>", only if requested
Constraints: <must keep / avoid>
```

Do not invent new creative requirements. If the user asks for "a hero image for a website", it is fine to add implied composition constraints such as "space for headline text"; it is not fine to invent a mascot, brand, logo, or unrelated subject.

## Boundaries

This skill does not support:

- Inpainting.
- Masks.
- Local repaint workflows.
- Multi-turn canvas editing.
- Background removal or transparent cutouts.
- Precise identity-preserving edits.

When asked for those workflows, explain briefly that this skill supports text generation and reference-image guided generation, then route to the appropriate available editing workflow.
