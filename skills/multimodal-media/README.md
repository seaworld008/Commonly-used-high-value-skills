# 多模态内容 / Multimodal Media

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦图像、音频、视频、截图、摘要与转写的多模态生产力技能集合。

当前分类共 **9** 个技能。

## 推荐先看

- [imagegen](./imagegen/) - Use when the user asks to generate or edit images via the OpenAI Image API (for example: generate image, edit/inpaint/mask, background removal or replacement, transparent background, product shots, concept art, covers, or batch variants); run the bundled CLI (`scripts/image_gen.py`) and require `OPENAI_API_KEY` for live calls.
- [sora](./sora/) - Use when the user asks to generate, remix, poll, list, download, or delete Sora videos via OpenAI\u2019s video API using the bundled CLI (`scripts/sora.py`), including requests like \u201cgenerate AI video,\u201d \u201cSora,\u201d \u201cvideo remix,\u201d \u201cdownload video/thumbnail/spritesheet,\u201d and batch video generation; requires `OPENAI_API_KEY` and Sora API access.
- [speech](./speech/) - Use when the user asks for text-to-speech narration or voiceover, accessibility reads, audio prompts, or batch speech generation via the OpenAI Audio API; run the bundled CLI (`scripts/text_to_speech.py`) with built-in voices and require `OPENAI_API_KEY` for live calls. Custom voice creation is out of scope.
- [transcribe](./transcribe/) - Transcribe audio files to text with optional diarization and known-speaker hints. Use when a user asks to transcribe speech from audio/video, extract text from recordings, or label speakers in interviews or meetings.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `clay` | AI 3D model generation agent. Generates text-to-3D and image-to-3D code (Python/JS/OpenSCAD) using Meshy, Tripo, Hunyuan3D, Rodin, Sloyd, and Stability APIs. Handles game pipeline integration, LOD, retopology, UV, and QC validation. | [目录](./clay/) | [SKILL.md](./clay/SKILL.md) |
| `imagegen` | Use when the user asks to generate or edit images via the OpenAI Image API (for example: generate image, edit/inpaint/mask, background removal or replacement, transparent background, product shots, concept art, covers, or batch variants); run the bundled CLI (`scripts/image_gen.py`) and require `OPENAI_API_KEY` for live calls. | [目录](./imagegen/) | [SKILL.md](./imagegen/SKILL.md) |
| `screenshot` | Use when the user explicitly asks for a desktop or system screenshot (full screen, specific app or window, or a pixel region), or when tool-specific capture capabilities are unavailable and an OS-level capture is needed. | [目录](./screenshot/) | [SKILL.md](./screenshot/SKILL.md) |
| `sketch` | AI image generation code creation using Gemini API. Handles text-to-image generation, image editing, and prompt optimization. Use when image generation code is needed. | [目录](./sketch/) | [SKILL.md](./sketch/SKILL.md) |
| `sora` | Use when the user asks to generate, remix, poll, list, download, or delete Sora videos via OpenAI\u2019s video API using the bundled CLI (`scripts/sora.py`), including requests like \u201cgenerate AI video,\u201d \u201cSora,\u201d \u201cvideo remix,\u201d \u201cdownload video/thumbnail/spritesheet,\u201d and batch video generation; requires `OPENAI_API_KEY` and Sora API access. | [目录](./sora/) | [SKILL.md](./sora/SKILL.md) |
| `speech` | Use when the user asks for text-to-speech narration or voiceover, accessibility reads, audio prompts, or batch speech generation via the OpenAI Audio API; run the bundled CLI (`scripts/text_to_speech.py`) with built-in voices and require `OPENAI_API_KEY` for live calls. Custom voice creation is out of scope. | [目录](./speech/) | [SKILL.md](./speech/SKILL.md) |
| `summarize` | 对网页、文档、邮件与长文本进行快速摘要，提炼核心信息。 | [目录](./summarize/) | [SKILL.md](./summarize/SKILL.md) |
| `tone` | Game audio generation agent. Produces code (Python/JS/TS/Shell) for SFX, BGM, Voice, Ambient, and UI sounds using ElevenLabs/Stable Audio/MusicGen/Suno/OpenAI TTS/JSFXR. Handles LUFS normalization and middleware integration. | [目录](./tone/) | [SKILL.md](./tone/SKILL.md) |
| `transcribe` | Transcribe audio files to text with optional diarization and known-speaker hints. Use when a user asks to transcribe speech from audio/video, extract text from recordings, or label speakers in interviews or meetings. | [目录](./transcribe/) | [SKILL.md](./transcribe/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
