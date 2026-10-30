# SkyAI 公共导航与静态页面发布经验

这份记录沉淀一次天空 AI 中转站公共页面维护：首页已经有 Skills 入口，但模型广场和使用指南使用另一套静态共享头部，导致入口缺失。修复时没有重建应用、数据库、Redis 或支付服务，只更新共享头部、静态 HTML、gzip 文件和对应 Nginx 路由。

## 适用场景

- 首页有导航项，模型广场、使用指南或 Skills 专题缺少同一入口。
- 新增一级公共页面，需要和 /home、/ai-models 等产品路由保持一致。
- 用户看到 Markdown、iframe 或首页回退，而目标应当是真实 HTML 页面。
- 修改了静态页面的内联 CSS、JavaScript、gzip 或不可变 HTML 文件名。
- 服务存在主域名和 CDN/备用域名，需要比较两个入口的真实结果。

## 先找对页面来源

不要只修改首页。先建立来源表：

| 页面 | 常见来源 | 误区 |
| --- | --- | --- |
| 首页 | 后台保存的自定义 HTML/Markdown | 以为首页改了，其他页面会自动同步 |
| 模型广场 | 模型目录模板 + 共享头部渲染器 | 只改后台首页内容 |
| 使用指南 | 指南模板 + 共享头部渲染器 | 为加一个链接重写整篇指南 |
| Skills 专题 | 独立不可变静态 HTML | 把它配置成 Markdown 或 iframe |
| 侧边栏菜单 | 后台 custom menu 数组 | 以为菜单地址会修改公共头部 |

共享导航应有一个明确源文件。模板改动后，必须重新生成模型页和指南页，再检查当前页高亮、移动端布局和 Skills 入口。

## 一级路由规范

先定唯一规范地址。若同类产品页无尾斜杠，就使用 /skills：

- GET /skills -> 200 text/html
- GET /skills/ -> 308 /skills
- GET /guide/skills -> 308 /skills
- GET /guide/skills/ -> 308 /skills
- POST /skills -> 405
- GET /skills/unknown -> 404

页面内所有入口必须使用同一规范地址，例如 HTML 链接 href=/skills。不要混用 /skills、/skills/、后台内部菜单 ID 或 md: URL。未知子路径不能被应用宽泛回退到首页，否则拼写错误会返回 200 并形成重复内容。

## 静态 HTML 发布

公共营销页应是可直接访问的 HTML。需要时将 CSS 内联、图标使用 data URL，并避免无必要的外部脚本。

每个版本使用不可变文件名，例如 skills-<sha256-prefix>.html 和 skills-<sha256-prefix>.html.gz。以下内容必须成套更新：

- HTML 正文 SHA-256
- gzip 解压后正文
- Nginx try_files 文件名
- 内联 style/script 的 CSP SHA-256
- manifest 中的字节数、文件名和 CSP

修改内联样式后必须重新计算 CSP。HTTP 200 不能证明页面正常；CSP 不匹配时浏览器仍可能拒绝样式或脚本。

建议的响应边界：HTML content type、短期 must-revalidate 缓存、Vary: Accept-Encoding、nosniff、SAMEORIGIN，以及无运行时请求页面的 connect-src 'none'。

## 安全发布顺序

1. git fetch origin --prune，确认工作区干净。
2. 读取服务器当前 Nginx snippet、活动 HTML 和 gzip 文件名。
3. 在 root-only 变更目录备份 snippet、旧 HTML 和旧 gzip。
4. 本地生成 HTML、gzip、manifest 和 CSP。
5. 上传到受控暂存目录，文件先使用严格权限。
6. 安装新的不可变文件，保持既有 owner 和 mode。
7. 只替换精确的 try_files 行和必要的路由块。
8. 在现有 Nginx 容器中运行 nginx -t。
9. 平滑 reload Nginx。
10. 做浏览器、HTTP、双入口和容器健康验收。

公共导航发布不需要重建 PostgreSQL、Redis、应用或支付桥，也不应使用 Docker socket 或全局 docker prune。

## 浏览器验收

使用已登录的同一浏览器检查真实渲染结果，而不是只看源文件：

- 首页、模型广场、使用指南、Skills 专题都出现 Skills 技能库 ↗。
- 顶部导航保持一行，桌面端不横向滚动。
- 页面滚动后头部仍固定在视口顶部。
- Skills 链接指向 /skills，没有多余尾斜杠。
- Skills 页面是 HTML，不是 Markdown 占位或意外 iframe。
- 当前页面的 aria-current、标题、页脚、账户按钮和产品入口仍存在。

读取 .sky-site-header 的 computed position，滚动到 1200 后检查 getBoundingClientRect().top 接近 0，再滚回顶部。期望 position 为 sticky。

## 双入口 HTTP 验收矩阵

主域名和备用/CDN 域名都要跑同一组检查：

| 检查 | 期望 |
| --- | --- |
| 规范页面 | 200、HTML、标题和导航正确 |
| 尾斜杠别名 | 308 到规范地址 |
| 历史别名 | 308 到规范地址 |
| POST 静态页 | 405 |
| 未知子路径 | 404 |
| 私有静态文件 | 404 |
| gzip 请求 | 解压正文等于 HTML SHA-256 |
| 条件请求 | ETag 命中时 304 |
| 未授权动态 API | 401 或平台定义的未授权响应 |

两个入口的 HTML hash、CSP 和关键响应头应一致。还应检查模型页、指南页的当前页高亮和正文保持不变。

## 回滚

回滚只恢复文件级变更：

1. 恢复备份的 Nginx snippet、HTML 和 gzip。
2. 运行 nginx -t。
3. 平滑 reload Nginx。
4. 重新跑路由、浏览器和双入口验收。

如果同时改了后台首页内容或菜单，只通过已登录控制台恢复保存的 home_content 或菜单数组。导航问题不要恢复数据库快照，也不要重建应用容器。

## 禁止事项

- 只验证首页就宣布公共导航完成。
- 手工编辑仓库生成的技能 README、目录、catalog 或 OpenClaw 导出。
- 修改内联 CSS/JS 后继续使用旧 CSP。
- 用宽泛应用回退处理未知静态子路径。
- 把凭据、Cookie、带 token 的管理 URL 或私有交接文件写入公共仓库。
- 用户要求一级 HTML 页面时使用 iframe 或 Markdown 替代。
- 只看 200 状态码，不检查浏览器渲染、gzip、CSP 和真实入口。

## 发布记录应包含

- 规范路由和兼容跳转
- 不可变文件名、SHA-256、gzip 和 CSP hash
- 主/备用入口验收结果
- 浏览器头部和 sticky 行为结果
- Nginx test/reload 结果
- 备份目录和回滚步骤
- 容器健康状态，以及应用、数据库、Redis、支付服务未重启的明确说明
