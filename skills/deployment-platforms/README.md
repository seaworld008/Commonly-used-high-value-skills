# 部署平台 / Deployment Platforms

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦 Vercel、Netlify、Render、Cloudflare 等部署平台的发布与接入技能。

当前分类共 **7** 个技能。

## 推荐先看

- [cloudflare-deploy](./cloudflare-deploy/) - Deploy applications and infrastructure to Cloudflare using Workers, Pages, and related platform services. Use when the user asks to deploy, host, publish, or set up a project on Cloudflare.
- [netlify-deploy](./netlify-deploy/) - Deploy web projects to Netlify using the Netlify CLI (`npx netlify`). Use when the user asks to deploy, host, publish, or link a site/repo on Netlify, including preview and production deploys.
- [render-deploy](./render-deploy/) - Deploy applications to Render by analyzing codebases, generating render.yaml Blueprints, and providing Dashboard deeplinks. Use when the user wants to deploy, host, publish, or set up their application on Render''s cloud platform.
- [vercel-deploy](./vercel-deploy/) - Deploy applications and websites to Vercel. Use when the user requests deployment actions like "deploy my app", "deploy and give me the link", "push this live", or "create a preview deployment".

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `cloudflare-deploy` | Deploy applications and infrastructure to Cloudflare using Workers, Pages, and related platform services. Use when the user asks to deploy, host, publish, or set up a project on Cloudflare. | [目录](./cloudflare-deploy/) | [SKILL.md](./cloudflare-deploy/SKILL.md) |
| `netlify-deploy` | Deploy web projects to Netlify using the Netlify CLI (`npx netlify`). Use when the user asks to deploy, host, publish, or link a site/repo on Netlify, including preview and production deploys. | [目录](./netlify-deploy/) | [SKILL.md](./netlify-deploy/SKILL.md) |
| `pipe` | 持续集成工作流、触发策略、安全加固和复用设计。 | [目录](./pipe/) | [SKILL.md](./pipe/SKILL.md) |
| `render-deploy` | Deploy applications to Render by analyzing codebases, generating render.yaml Blueprints, and providing Dashboard deeplinks. Use when the user wants to deploy, host, publish, or set up their application on Render''s cloud platform. | [目录](./render-deploy/) | [SKILL.md](./render-deploy/SKILL.md) |
| `scaffold` | 云基础设施、环境配置和本地开发部署脚手架。 | [目录](./scaffold/) | [SKILL.md](./scaffold/SKILL.md) |
| `shard` | 多租户架构、租户隔离、路由和规模化设计。 | [目录](./shard/) | [SKILL.md](./shard/SKILL.md) |
| `vercel-deploy` | Deploy applications and websites to Vercel. Use when the user requests deployment actions like "deploy my app", "deploy and give me the link", "push this live", or "create a preview deployment". | [目录](./vercel-deploy/) | [SKILL.md](./vercel-deploy/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
