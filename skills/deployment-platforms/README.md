# 部署平台 / Deployment Platforms

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦 Vercel、Netlify、Render、Cloudflare 等部署平台的发布与接入技能。

当前分类共 **7** 个技能。

## 推荐先看

- [cloudflare-deploy](./cloudflare-deploy/) - 用于将应用部署到 Cloudflare 并处理相关发布流程。
- [netlify-deploy](./netlify-deploy/) - 用于将网站或应用部署到 Netlify 并获取预览或生产链接。
- [render-deploy](./render-deploy/) - 用于将服务或应用部署到 Render 并处理运行配置。
- [vercel-deploy](./vercel-deploy/) - 用于将应用或网站部署到 Vercel，创建预览部署或生产发布链接。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `cloudflare-deploy` | 用于将应用部署到 Cloudflare 并处理相关发布流程。 | [目录](./cloudflare-deploy/) | [SKILL.md](./cloudflare-deploy/SKILL.md) |
| `netlify-deploy` | 用于将网站或应用部署到 Netlify 并获取预览或生产链接。 | [目录](./netlify-deploy/) | [SKILL.md](./netlify-deploy/SKILL.md) |
| `pipe` | 用于pipe，支持部署发布、配置、预览和故障处理。 | [目录](./pipe/) | [SKILL.md](./pipe/SKILL.md) |
| `render-deploy` | 用于将服务或应用部署到 Render 并处理运行配置。 | [目录](./render-deploy/) | [SKILL.md](./render-deploy/SKILL.md) |
| `scaffold` | 用于scaffold，支持部署发布、配置、预览和故障处理。 | [目录](./scaffold/) | [SKILL.md](./scaffold/SKILL.md) |
| `shard` | 用于shard，支持部署发布、配置、预览和故障处理。 | [目录](./shard/) | [SKILL.md](./shard/SKILL.md) |
| `vercel-deploy` | 用于将应用或网站部署到 Vercel，创建预览部署或生产发布链接。 | [目录](./vercel-deploy/) | [SKILL.md](./vercel-deploy/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
