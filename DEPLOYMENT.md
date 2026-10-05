# 笔记翻译作业：配置与部署

2026-10-05 已通过 Vercel CLI 上线：[Margin AI NoteTaker](https://ai-notetaker-three.vercel.app)。无需登录即可访问，真实 Supabase 与 OpenRouter 的公网端到端测试通过。项目 ID 已写入本地 `.env`；认证使用 Vercel CLI 的本机登录状态。

## 需要你提供的值

本项目的 `.env` 已配置完成；下面说明可用于换账号或重建部署。

下面的 Vercel Token 与 ID 是供本地 `manage.py deploy` 自动部署脚本使用的。通过 Vercel 网页导入 GitHub 仓库部署时，不需要在本地填写这些字段。

| 字段 | 需要什么 | 在哪里获取 |
| --- | --- | --- |
| `DATABASE_URL` | **已配置并验证**，包含实际数据库密码 | 使用 Supabase **Transaction pooler**，端口 `6543` |
| `VERCEL_TOKEN` | **可选**：CLI 已登录时留空；无人值守环境可使用 Token | <https://vercel.com/account/tokens> |
| `VERCEL_ORG_ID` | 项目所属账号或团队的 ID | 执行 Vercel `link` 后生成的 `.vercel/project.json` 中的 `orgId`；团队也可在 Team Settings 中查到 |
| `VERCEL_PROJECT_ID` | 目标 Vercel 项目的 ID | Project Settings → General → Project ID，或 `.vercel/project.json` 的 `projectId` |
| `APP_URL` | 最终可公开访问的应用 URL | 部署命令成功后自动填入；如使用固定生产域名，可再改成该域名 |

`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 已配置。`PORT=5001` 是本地启动端口。此应用通过 Flask 连接 Postgres，**不需要额外的 Supabase URL、anon key 或 service-role key**。

数据库 URI 应来自你的项目，不能根据区域猜测 host。把 `[YOUR-PASSWORD]` 替换为真实数据库密码，并对密码中的 `@`、`#`、`/` 等保留字符做 URL 编码。可使用 `postgresql://`、`postgres://` 或 `postgresql+psycopg://`；应用自动规范化驱动并默认加上 `sslmode=require`。

如果你还没有 Vercel 项目，可以先登录并交互式关联一个自己的项目：

```sh
pnpm dlx vercel@62.1.0 login
pnpm dlx vercel@62.1.0 link
```

运行位置是本项目根目录。将生成的 `orgId`、`projectId` 填进 `.env`，已登录的 CLI 不需要 Token，即可使用下面的部署工具。

## 填好后的操作

Vercel **不强制绑定 GitHub**：下面的 CLI 流程可以直接上传本地项目。也可以在 Vercel 网页选择 Import Git Repository，导入 [Wenbin-Feng/AI_NoteTaker](https://github.com/Wenbin-Feng/AI_NoteTaker)，将 `DATABASE_URL`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 配置为服务器环境变量后部署。连接 GitHub 后，推送代码可自动触发部署；不要把 `.env` 提交进仓库。

```sh
uv sync
# 只输出字段是否已配置，不显示密钥或数据库密码
uv run python manage.py check-config

# 创建云数据库的 note 表，重复执行保留现有数据
uv run python manage.py init-db

# 检查真实数据库和真实模型；模型检查会调用一次 LLM
uv run python manage.py check-config --live

# 同步 Production 环境变量并通过 Vercel CLI 部署
uv run python manage.py deploy
```

数据库初始化也可以在 Supabase SQL Editor 中执行 `supabase/schema.sql`。SQL 启用 RLS，并禁止 `anon`、`authenticated` 直接访问此表；网页通过 Flask API 读写，服务器使用数据库连接。云端启动不重复建表。

部署命令只同步 `DATABASE_URL`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 到目标项目的 **Production** 环境，更新这些字段的旧值。它不会修改 Preview/Development 环境，也不会把部署 Token 上传为应用配置。`.env` 已被 Git 和 Vercel 上传规则排除；`.venv`、本地数据库和本地截图也排除。

部署完成后，在 Vercel Project Settings → Deployment Protection 中，按照课程要求关闭提交 URL 的 **Require Log In / Vercel Authentication**。然后测试：

```sh
uv run python manage.py smoke --translate
```

这个测试会验证网页、JS/CSS、数据库健康、笔记新增/读取/搜索/更新/删除、真实翻译、保存译文为新笔记，以及原文保留。测试创建的笔记在结束后删除。若 URL 返回登录页、数据库异常或模型错误，命令会失败。

## 交作业前

- 用无需登录的浏览器打开最终 URL，确认可访问。
- 创建一条演示笔记，翻译成另一种语言，截图中同时展示原文与译文。
- 将公网链接、实现说明、测试记录和**上线后的截图**放入提交 PDF。
- `submission/screenshots/local-translation.png` 是本地真实翻译的截图，只能作为本地验证材料，不能当成 Vercel 部署完成的证据。
- 完整 Week 5 作业还要求 Task 2 的游戏过程和截图；本项目处理 Task 1 的笔记翻译应用。

## 参考

- [Supabase 官方数据库连接说明](https://supabase.com/docs/guides/database/connecting-to-postgres)：连接方式、密码编码和 SSL。
- [Vercel 官方 Flask 部署说明](https://vercel.com/docs/frameworks/backend/flask)：Flask 入口、`public/` 静态文件和函数配置。
- [Vercel CLI 环境变量说明](https://vercel.com/docs/cli/env)：通过 stdin 添加和更新环境变量。
- [Vercel 部署方式](https://vercel.com/docs/deployments)：GitHub 自动部署和无需 Git 绑定的 CLI 部署。
