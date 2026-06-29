# 多模态内容 / Multimodal Media

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦图像、音频、视频、截图、摘要与转写的多模态生产力技能集合。

当前分类共 **10** 个技能。

## 推荐先看

- [imagegen](./imagegen/) - 用于生成、编辑和迭代图像内容与视觉素材。
- [sora](./sora/) - 用于构思、生成和评审 Sora 视频或视频提示词。
- [speech](./speech/) - 用于语音，支持内容生成、编辑、分析和交付。
- [transcribe](./transcribe/) - 用于将音频或视频中的语音转写为文本，并可结合说话人分离和已知说话人提示。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `clay` | 用于clay，支持内容生成、编辑、分析和交付。 | [目录](./clay/) | [SKILL.md](./clay/SKILL.md) |
| `gpt-image2` | 让 Codex 通过本地配置的 gpt-image-2 兼容画图服务生成图片，支持提示词、参考图、比例、清晰度和本地保存。 | [目录](./gpt-image2/) | [SKILL.md](./gpt-image2/SKILL.md) |
| `imagegen` | 用于生成、编辑和迭代图像内容与视觉素材。 | [目录](./imagegen/) | [SKILL.md](./imagegen/SKILL.md) |
| `screenshot` | 用于截图、屏幕捕获、视觉核查和界面证据收集。 | [目录](./screenshot/) | [SKILL.md](./screenshot/SKILL.md) |
| `sketch` | 用于sketch，支持内容生成、编辑、分析和交付。 | [目录](./sketch/) | [SKILL.md](./sketch/SKILL.md) |
| `sora` | 用于构思、生成和评审 Sora 视频或视频提示词。 | [目录](./sora/) | [SKILL.md](./sora/SKILL.md) |
| `speech` | 用于语音，支持内容生成、编辑、分析和交付。 | [目录](./speech/) | [SKILL.md](./speech/SKILL.md) |
| `summarize` | 用于忠实摘要网页、文档、邮件、转录稿或长文本，并提炼重点和后续行动。 | [目录](./summarize/) | [SKILL.md](./summarize/SKILL.md) |
| `tone` | 用于tone，支持内容生成、编辑、分析和交付。 | [目录](./tone/) | [SKILL.md](./tone/SKILL.md) |
| `transcribe` | 用于将音频或视频中的语音转写为文本，并可结合说话人分离和已知说话人提示。 | [目录](./transcribe/) | [SKILL.md](./transcribe/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
