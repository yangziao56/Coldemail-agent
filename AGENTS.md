# Repository Guidelines（仓库指南）

## 项目结构与模块组织

- `app.py`：Flask Web 入口（路由 + session/密码保护）。
- `src/`：核心逻辑
  - `email_agent.py`：从 PDF/JSON 抽取画像、推荐目标、生成/改写邮件。
  - `web_scraper.py`：轻量搜索与页面抓取（在缺少检索增强/grounding 时作为补充）。
  - `cli.py`：CLI 封装（`python -m src.cli ...`）。
- `templates/`：单文件 HTML 模板（内联 CSS/JS，主界面为 `index_v2.html`）。
- `examples/`：示例 JSON 画像（`sender.json`、`receiver.json`）。

## 构建、测试与开发命令

- 安装依赖：`python -m pip install -r requirements.txt`
- 本地运行（Web）：`python app.py`（默认 `http://localhost:5000`）
- 生产运行：`gunicorn app:app`（见 `Procfile`）
- CLI 帮助：`python -m src.cli --help`
- 基础自检（当前未配置正式测试套件）：`python -m compileall .`

## 代码风格与命名约定

- Python：4 空格缩进；函数/变量用 `snake_case`，类用 `PascalCase`。
- 优先使用类型标注与小而纯的辅助函数（参考 `src/email_agent.py` 的解析工具）。
- HTML 模板：优先沿用现有内联 `<script>` 组织 UI 逻辑；除非必要，避免引入外部静态资源。

## 测试指南

- 尚未配置专用测试框架（当前没有 `tests/` 目录）。
- 新增/修改行为时，至少提供可复现路径：
  - CLI：在 `examples/` 增补/更新示例，并在说明中给出运行命令。
  - Web：注明相关接口与请求体（例如 `/api/generate-email`）。

## 提交与拉取请求（PR）规范

- 提交信息采用轻量约定：`feat: ...`、`fix: ...`、`docs: ...`、`chore: ...`、`style: ...`（偶尔使用版本标签如 `v3.0: ...`）。
- PR 需包含：
  - 改动内容与动机，以及任何用户可见的 UX 变化说明。
  - 修改 `templates/` 的 UI 时提供截图/GIF。
  - 确认未提交密钥或敏感数据。

## 文档更新要求（必须）

- 每次修改代码（含 UI、接口、配置、依赖、行为逻辑），都需要同步更新相关文档：`README.md`、`devlog.md`、`note.md`（至少更新“受影响的那一份/几份”，不要求无关内容也改）。
- PR 描述里简要列出“本次改动影响了哪些文档/为什么”。

### `README.md` 写法

- 面向“新用户/评审者”的入口文档：怎么用、怎么跑起来、核心能力是什么。
- 只保留稳定信息：Quick Start、关键命令、环境变量、CLI 示例、线上地址等；避免写过细的实现细节。
- 有用户可见变化时更新：功能列表、使用步骤、示例命令、截图/说明（如有）。

### `devlog.md` 写法

- 面向“开发过程”的按时间记录：每次重要迭代新增一个日期小节（`## YYYY-MM-DD: ...`）。
- 写清三件事：新增/变更点（bullets）、涉及文件（如 `templates/index_v2.html`）、风险/迁移提示（如环境变量或兼容性）。
- 偏事实记录，不做长篇背景论述。

### `note.md` 写法

- 面向“设计/思路沉淀”的长期文档：目标、核心抽象、版本演进、关键决策与取舍。
- 更新原则：当核心流程、抽象边界、模型/推荐策略、重要 UX 流程发生变化时，补充对应章节。
- 允许更主观的解释（为什么这么做），但保持结构清晰，避免把操作指南放进来（操作指南放 `README.md`）。

## 安全与配置提示

- 通过环境变量配置：`GEMINI_API_KEY`（或 `GOOGLE_API_KEY`）、可选 `OPENAI_API_KEY`，以及 Web 端的 `APP_PASSWORD`/`SECRET_KEY`。
- 不要提交 PDF（`.gitignore` 已忽略 `*.pdf`）。
