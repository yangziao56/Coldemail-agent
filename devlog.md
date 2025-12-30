# Development Log

## 2025-12-31: LinkedIn URL 生成策略优化

### 问题
- AI 模型（Gemini）会根据人名**编造** LinkedIn 个人主页 URL（如生成 `emilycartermergers`），而实际正确的是 `emilyacarter`
- 用户点击后会看到 "页面不存在" 错误
- Google Search grounding 返回的是重定向 URL（`vertexaisearch.cloud.google.com`），无法用于验证

### 解决方案
**改为生成 LinkedIn 搜索链接，而不是个人主页链接**

### 后端改动 (`src/email_agent.py`)
- 新增 `_generate_linkedin_search_url(name, company)` 函数
  - 生成格式：`https://www.linkedin.com/search/results/people/?keywords=Name%20Company`
  - 用户点击后在 LinkedIn 上搜索该人，自己选择正确的结果
- 修改 `_normalize_recommendations`：
  - 如果 AI 返回的 URL 验证失败，自动生成搜索链接
  - 从 position 字段提取公司名（如 "VP at Goldman Sachs"）
- 修改搜索提示词：
  - 明确告诉模型**不要生成 LinkedIn URL**（`linkedin_url` 留空）
  - 只需返回人名、职位、证据来源
- 简化 `_validate_linkedin_url`：
  - 移除对 grounding URLs 的依赖（因为是重定向 URL）
  - 只做格式验证和假 URL 模式过滤

### 前端改动 (`templates/index_v2.html`)
- `renderRecommendations` 中区分搜索链接和个人主页链接
  - 搜索链接：显示 🔍 图标 + "Search on LinkedIn" 提示
  - 个人主页链接：正常显示 LinkedIn 图标

### 用户体验改进
- ✅ 不再出现 "页面不存在" 错误
- ✅ 用户点击 LinkedIn 图标 → 打开搜索页面 → 自己选择正确的人
- ✅ 保证每个推荐都有可用的 LinkedIn 搜索入口

Files: `src/email_agent.py`, `templates/index_v2.html`

---

## 2025-12-30: Gemini Google Search API 升级

### 问题
- `google.generativeai` 包已废弃，`google_search_retrieval` 工具不再支持
- 报错：`400 Unable to submit request because google_search_retrieval is not supported`

### 解决方案
- 安装新的 `google-genai` 包 (v1.56.0)
- 使用新 API：`genai_new.Client` + `genai_types.Tool(google_search=genai_types.GoogleSearch())`

### 后端改动 (`src/email_agent.py`)
- 新增导入：`from google import genai as genai_new` 和 `from google.genai import types as genai_types`
- 重写 `_call_gemini_with_search` 函数使用新 API
- 新增 `_extract_json_from_text` 函数（因为 Search grounding 不支持 JSON mode）

Files: `src/email_agent.py`, `requirements.txt`（需要 `google-genai>=1.56.0`）

---

## 2025-12-30: LinkedIn Profile Search Enhancement

- **Find Targets 功能增强**：优先搜索 LinkedIn 信息
- **后端改动** (`src/email_agent.py`)：
  - 修改 `_build_recommendation_prompt`：新增 `linkedin_url` 字段要求
  - 修改 `_normalize_recommendations`：提取并处理 `linkedin_url`，自动从 sources 中识别 LinkedIn URLs
  - 修改搜索提示词：明确要求 "Search '[name] [company] LinkedIn'" 优先获取 LinkedIn 信息
  - 针对 Finance/Banking 专业人士优化搜索策略
- **前端改动** (`templates/index_v2.html`)：
  - `renderRecommendations`：每个推荐卡片显示 LinkedIn 图标链接
  - Profile Modal：新增 LinkedIn Profile 展示区域
  - 新增 `.linkedin-link` 样式（LinkedIn 品牌蓝色 #0a66c2）
- **返回数据结构**：每个推荐新增 `linkedin_url` 字段

Files: `src/email_agent.py`, `templates/index_v2.html`

## 2025-12-23: 用户上传数据存储功能

- 新增用户上传文件（简历 PDF + Target 信息）的持久化存储功能
- **存储结构**：
  - 路径：`data/users/{日期}/{时间戳}_{session_id}/`
  - 文件：`resume.pdf`（原始简历）、`resume_profile.json`（解析后数据）、`targets.json`（目标人选列表）、`metadata.json`（完整会话记录）
- **新增模块**：`src/services/user_uploads.py`
  - `UserUploadStorage` 类：单例模式管理用户上传数据
  - `save_user_resume()` / `save_user_targets()` / `add_user_target()`：便捷函数
- **API 更新**：
  - `/api/upload-sender-pdf`：上传简历时自动保存原始 PDF 和解析数据
  - `/api/save-targets`（新增）：保存用户选择的 target 列表
- **前端更新**：
  - 添加 `generateSessionId()` 生成唯一会话 ID
  - `state.sessionId` 贯穿整个用户会话
  - 在 `generateAllEmails()` 前自动保存 targets

Files: `src/services/user_uploads.py`（新增）, `app.py`, `templates/index_v2.html`

## 2025-12-23: UI 科幻梦核视觉主题更新

- 在保持 v2 全部功能和布局不变的前提下，更新视觉设计为科幻梦核风格
- **配色方案**：
  - 主背景：深空紫黑色（#0a0a12）
  - 主强调色：霓虹紫（#7b68ee → #9d8bff）
  - 次强调色：电子青（#00d4ff）、霓虹粉（#ff6b9d）
  - 成功/警告/错误：霓虹绿/金/红
- **字体**：添加 Brice Semi Expanded 字体（CDN）+ Inter 回退
- **视觉效果**：
  - 悬浮 LCD 面板效果（玻璃模糊 + 内发光边框）
  - 柔和漫射光背景（多层渐变动画）
  - 景深模糊效果（body::before 脉冲动画）
  - 优雅渐变过渡（cubic-bezier 缓动）
  - 动态环境反射（hover 时发光增强）
- **组件更新**：
  - .panel: 玻璃态 + 顶部渐变线 + hover 发光
  - .btn-primary: 渐变背景 + 霓虹投影
  - .option-card, .choice-btn: 扫光动画 + 边框发光
  - .mode-card: 全息卡片效果
  - .recommendation-item: 悬浮卡片动画
  - 滚动条: 自定义霓虹紫渐变样式
- **内联样式更新**：dropzone、notice、success 提示全部更新为深色主题

Files: `templates/index_v2.html`

## 2025-12-23: UI v3 Multi-Step Layout Refactor

- 创建 `index_v3.html` 新模板，采用组件化多步骤布局
- 四个核心组件：
  1. **TopBar**: 顶部导航栏（品牌标识 + 模式切换 + 退出）
  2. **StepNav**: 步骤导航（5 步：目的 → 个人信息 → 目标人选 → 模板 → 生成）
  3. **ModeSelector**: 模式选择卡片（快速 vs 专业）
  4. **PrivacyModal**: 隐私声明弹窗（同意后才能继续）
  5. **PurposeStep**: 目的选择步骤（4 卡片选择 + 领域选择）
- 设计风格：简洁、现代、Apple 风格设计系统
- CSS 变量：统一颜色、间距、圆角、阴影、过渡
- 状态管理：使用单一 `state` 对象管理全局状态
- 添加 `/v3` 测试路由（保持 v2 为默认）

Files: `templates/index_v3.html`, `app.py`

## 2025-12-23: Finance Track Fixed Questions (IBD Structure + Career Ladder + Bank Types)

- Professional Mode - Finance track 现在使用固定多选题而非动态生成
- 问题基于三个参考文档设计：
  - `question_fin/finance_structure.txt`: IBD 组织结构（Product Groups vs Sector Groups）
  - `question_fin/investment_banking_career_ladder.txt`: 职级阶梯（Analyst → MD）及各级职责
  - `question_fin/different_kinds_investment_banks.txt`: 银行类型分类
- **6 个固定多选题**（按逻辑顺序）：
  1. **银行类型偏好**：Bulge Bracket / Commercial Banks with IB / Middle Market / Boutiques（含具体公司示例）
  2. **Product vs Sector 偏好**：Product Groups / Sector Groups / Both
  3. **Product Group 细分**（条件显示：仅当选择 Product/Both）：M&A Advisory, DCM, Leveraged Finance, ECM
  4. **Sector Group 细分**（条件显示：仅当选择 Sector/Both）：TMT, Healthcare, FIG, Energy, Industrials, Consumer, Real Estate, Sponsors 等
  5. **目标级别偏好**：Analyst(1-3年) / Associate(4-6年) / VP/Director(7-9年) / ED/SVP(10-12年) / MD(12+年)
  6. **联系目的**：Learn about role / Career advice / Referral / Industry insight / Mentorship
- **UI 特性**：
  - 多选支持（复选框样式）
  - 条件逻辑跳转（根据 Q2 决定是否显示 Q3/Q4）
  - 完成后显示偏好摘要
  - Skip 跳过支持
- Academic track 保持动态问题生成（调用 API）

Files: `templates/index_v2.html`

## 2025-12-21: Prompt Data Collection Feature

- 新增 Prompt 数据收集功能，用于收集 `find_target` 和 `generate_email` 两个步骤的 prompt 与输出。
- 数据格式：ID、用户信息、prompt_find_target、output_find_target、prompt_generate_email、output_generate_email、时间戳。
- 新增 `src/services/prompt_collector.py` 服务模块，使用单例模式管理会话。
- 数据存储位置：`data/prompt_logs/{日期}/{时间戳}_{id}.json`。
- 环境变量 `COLLECT_PROMPTS` 控制是否启用（默认启用）。
- 支持导出为 JSONL/CSV 格式供后续分析。

Files: `src/services/prompt_collector.py`, `src/email_agent.py`, `app.py`

## 2025-12-21: Finance Benchmark v0.1 - Richer Context Fields

- Expanded the finance benchmark schema/cases to include more structured context for realistic evaluation (especially for banker workflows): role titles, seniority, bank tier, coverage/product group, sector/stage, recruiting context, contact channels, plus an optional `email_spec` for explicit ask/value/hard rules/compliance.
- Updated rubric/templates so teams can collect this info via interviews/surveys and convert real samples into reproducible benchmark cases.

Files: `benchmarks/finance/schema_v0.json`, `benchmarks/finance/finance_v0.json`, `benchmarks/finance/README.md`, `benchmarks/finance/anonymization_and_labeling_template.md`, `benchmarks/finance/rubric_v0.md`, `benchmarks/finance/survey_template.md`, `README.md`

## 2025-12-21: Finance Survey v1 (Google Forms Ready)

- Added a copy-paste-ready finance outreach survey for Google Forms/Typeform, designed to collect both benchmark-ready cases and marketing research signals without asking for sensitive information.

Files: `benchmarks/finance/survey_v1_google_forms.md`, `benchmarks/finance/survey_template.md`, `benchmarks/finance/README.md`

## 2025-12-20: Finance Benchmark Starter Pack (v0)

- Added a finance-focused benchmark starter kit: schema, 10 synthetic cases (format demo), rubric, anonymization/labeling template, and a marketing research + survey template.
- Goal: make “find people” and “generate email” evaluation more reproducible (expected constraints + evidence-aware scoring), and provide a clear path to replace synthetic cases with anonymized real samples.

Files: `benchmarks/finance/README.md`, `benchmarks/finance/schema_v0.json`, `benchmarks/finance/finance_v0.json`, `benchmarks/finance/rubric_v0.md`, `benchmarks/finance/anonymization_and_labeling_template.md`, `benchmarks/finance/survey_template.md`, `README.md`

## 2025-12-16: Context Expansion (Targeting + Email)

- Step 3: added optional structured targeting inputs (ideal target description, must-have/must-not keywords, location, reply vs prestige, examples, evidence) for both Quick and Professional, and passed them into `preferences` for `POST /api/find-recommendations`.
- Recommendations: updated prompt + normalization so each candidate can include `evidence`, `sources`, and `uncertainty` (and the UI modal now surfaces them).
- Step 4: added optional email instruction inputs (goal, ask, value, constraints, hard rules, evidence) and fed them into generation (goal/ask fields + sender free-text) to reduce hallucinations.
- Receiver enrichment: `POST /api/search-receiver` now returns `raw_text`, and `POST /api/generate-email` preserves receiver `sources` so the email prompt can cite verifiable info.
- Updated `README.md` workflow diagram to show the time order of info collection and what each core API call can use.

Files: `templates/index_v2.html`, `src/email_agent.py`, `app.py`, `README.md`

## 2025-12-13: UI Polish (Apple-like Visual Refresh)

- Updated `templates/index_v2.html` styling to a lighter, glassy “Apple-like” look (subtle gradients, soft borders/shadows, blue accent).
- Quick Start: Step 2 now asks for optional resume/profile link/notes first; only if those are empty it shows the 5-question questionnaire (generated in one request).
- Quick Start: resume upload uses the same drag & drop dropzone pattern as Professional mode.
- Quick Start: the 5-question builder is generated only after clicking “Generate Questions”.
- Step 3 target preferences: removed the static 5-field form; use the dynamic preference questions + Step 1 field as defaults.
- Hard-capped dynamic questionnaires to `max_questions` to prevent over-generation.
- Quick Start: added a small onboarding modal shown when entering Step 1 (with “Don’t show again”).
- Quick Start: clarified onboarding copy to explain what context is collected and why.
- Documented product principle that everything should serve the two core tasks (find targets + generate emails), emphasizing structured context, evidence/uncertainty, and a feedback loop (`AGENTS.md`, `note.md`).

## 2025-12-12: v3.0 - Mode Selection (Quick Start & Professional) 🚀

### New Features

- **Mode Selection Screen**
  - Added beautiful mode selection interface after login
  - Two modes: "Quick Start" and "Professional"
  - Card-based UI with icons, descriptions, and feature lists

- **Privacy Notice** 🔒 (NEW!)
  - Displayed after mode selection, before proceeding
  - Informs users that:
    - Personal info and answers are only used for target matching and email generation
    - Data is not shared with third parties
    - Uploaded resumes are processed securely, not stored permanently
    - Session data is cleared when app is closed
  - User must acknowledge to continue

- **Quick Start Mode** ⚡
  - Designed for users without a resume
  - No document upload required
  - Uses interactive questionnaire to build user profile
  - Smart target matching with recommendations
  - Streamlined 5-step workflow:
    1. Purpose & Field selection
    2. Quick Profile Builder (questionnaire)
    3. Find Targets (manual or AI-recommended)
    4. Email Template selection
    5. Generate personalized emails

- **Professional Mode** 💼 (NEW!)
  - **Track Selection**: Choose between Finance or Academic
  - **Resume Upload**: Required for profile analysis
    - Drag & drop or click to upload
    - AI-powered resume parsing
    - Shows extracted profile summary
  - **Target Choice**: 
    - "Yes, I Have Targets" → Direct to manual input
    - "Find Targets for Me" → AI recommendations
  - **Professional Preference Questions**:
    - Track-specific questions
    - Based on resume analysis
    - Generates highly relevant recommendations
  - **Finance Track Features**:
    - Investment banking connections
    - Hedge fund & asset management
    - Fintech startups & VCs
    - Quantitative research roles
  - **Academic Track Features**:
    - Professor & researcher connections
    - PhD & postdoc applications
    - Research collaborations
    - Academic conference networking

### Professional Mode Flow

```
Mode Selection → Track (Finance/Academic) → Resume Upload → Target Choice
    ↓ (Have targets)                    ↓ (Need recommendations)
    Manual Input                        Preference Questions → AI Find Targets
    ↓                                   ↓
    Step 3 (Find Targets) → Step 4 (Template) → Step 5 (Generate)
```

### Modified Files

- `templates/index_v2.html`:
  - Added Professional mode panels:
    - `pro-track-selection`: Finance/Academic choice
    - `pro-resume-upload`: Resume upload with drag & drop
    - `pro-target-choice`: Have targets vs need recommendations
    - `pro-preferences`: Professional preference questions
  - Added new state variables:
    - `proTrack`: 'finance' or 'academic'
    - `proTargetChoice`: 'have' or 'need'
    - `proPreferenceHistory`: Preference Q&A history
  - Added new functions:
    - `setupProfessionalMode()`: All professional flow logic
    - `uploadProResume()`: Handle resume upload
    - `loadProPreferenceQuestions()`: Load track-specific questions
    - `renderProPreferenceQuestion()`: Render interactive questions
    - `findProTargets()`: Find recommendations based on profile

### UI/UX Improvements

- Professional mode cards with track-specific styling
- Drag & drop resume upload area
- Resume summary display after upload
- Track-aware preference questions
- Seamless transition from professional flow to main email generation
- Enlarged the Step 5 “Custom” tone instruction textbox for easier editing
- Quick Start questionnaire now generates a full 5-question set upfront (instead of per-question generation)
- Simplified the top-right mode switcher (removed redundant status text)

---

## 2025-12-05: v2.2 - Gemini Google Search Integration 🔍

### Bug Fixes

- **Fixed OpenAI web_search Error**
  - OpenAI API does not support `web_search` tool type (only `function` and `custom`)
  - Error: `Invalid value: 'web_search'. Supported values are: 'function' and 'custom'.`
  - Solution: Disabled OpenAI recommendations by default, switched to Gemini

- **Fixed DuckDuckGo Timeout on Render.com**
  - DuckDuckGo search was blocked/timeout on cloud servers
  - Error: `Connection to html.duckduckgo.com timed out`
  - Solution: Use Gemini's built-in Google Search grounding instead

- **Fixed Step 1 Field Selection Missing**
  - Field selection (AI/ML, Software, Finance, Other) was lost during git merge
  - Restored full Step 1 with both Purpose and Field options

### New Features

- **Gemini Google Search Grounding**
  - Uses Gemini's native `google_search_retrieval` tool
  - Real-time web search for finding target recommendations
  - Finds verified, currently active professionals
  - Much faster and more reliable than external scraping

### Modified Files

- `config.py`:
  - Added `GEMINI_SEARCH_MODEL`: Model for search-enabled requests
  - Added `USE_GEMINI_SEARCH`: Toggle for Google Search grounding (default: true)
  - Changed `USE_OPENAI_WEB_SEARCH` default to `false`
  - Changed `USE_OPENAI_RECOMMENDATIONS` default to `false`

- `src/email_agent.py`:
  - Added `_call_gemini_with_search()`: Gemini API call with Google Search grounding
  - Updated `find_target_recommendations()`:
    - Primary: Gemini with Google Search (new)
    - Fallback 1: OpenAI with web_search (disabled)
    - Fallback 2: OpenAI with manual scraping (disabled)
    - Fallback 3: Gemini without search

- `templates/index_v2.html`:
  - Restored Field selection in Step 1
  - Added `field` and `fieldCustom` to state
  - Added `fieldLabels` mapping
  - Added `getFieldLabel()` function
  - Updated `checkStep1Valid()` to require both purpose and field
  - Updated `getFieldText()` to prioritize Step 1 field

- `README.md`: Updated to v2.2 with new features and bug fixes

### Technical Details

```python
# Gemini Google Search grounding usage
gemini_model = genai.GenerativeModel(
    model,
    generation_config=generation_config,
    tools="google_search_retrieval"  # Enable Google Search
)
response = gemini_model.generate_content(prompt)
```

### Recommendation Flow (v2.2)

1. **Gemini + Google Search** (Primary) - Real-time web search
2. OpenAI + web_search (Disabled) - API doesn't support this
3. OpenAI + manual scraping (Disabled) - Timeout issues
4. **Gemini without search** (Fallback) - Uses model knowledge

---

## 2025-12-02: v2.1 - Enhanced Target Management 🆕

### New Features

- **Manual Target Document Upload**
  - Support for PDF, TXT, and MD file uploads when manually adding targets
  - AI-powered profile extraction from uploaded documents
  - Auto-fills name and field from extracted data
  - Skips web search for targets with uploaded documents (uses local data)

- **Target Profile Preview Modal**
  - "📋 View" button on each recommended target
  - Modal shows: name, position, match score, education, experience, skills, projects, match reason
  - "Select This Target" button to add directly from modal
  - Click outside modal to close

### Modified Files

- `app.py`:
  - Added `/api/upload-receiver-doc` endpoint for target document upload
  - Supports PDF (using existing PDF parser) and TXT/MD (using Gemini)

- `src/email_agent.py`:
  - Added `parse_text_to_profile()`: Parse text content into structured profile

- `templates/index_v2.html`:
  - Version badge updated to v2.1
  - Added file upload input in manual target section
  - Added profile modal HTML and styles
  - Updated JavaScript:
    - `setupTargetDocUpload()`: Handle target document uploads
    - `uploadTargetDoc()`: Upload and process target documents
    - `openProfileModal()`: Display target profile in modal
    - `closeProfileModal()`: Close the modal
    - `selectFromModal()`: Select target from modal view
    - `renderRecommendations()`: Added "View" button to each recommendation
    - Updated `generateAllEmails()`: Skip web search if profile data exists

### UI Improvements
- Modal overlay with smooth animations
- Profile sections with icons (🎯 Position, 📊 Match Score, 🎓 Education, etc.)
- Loading state for document analysis
- Success message after document upload

---

## 2025-11-29: v2.0 - Web Interface with Smart Wizard 🎉

### New Features

- **Multi-Step Wizard Interface**
  - Step 1: Purpose & Field Selection
    - 4 purpose options: Academic, Job Seeking, Coffee Chat, Other
    - 4 field options: AI/ML, Software Engineering, Finance/Fintech, Other
    - Custom input support for both
  
  - Step 2: Profile Building
    - Resume upload option (PDF)
    - Quick questionnaire (5 questions) for users without resume
    - Each question has 4 options with custom input
  
  - Step 3: Target Discovery
    - Manual target input
    - AI-powered recommendation system (top 10 matches)
    - Match analysis with compatibility score
    - "Generate More" and "Add Manually" options
  
  - Step 4: Email Generation & Customization
    - Regenerate with style options:
      - More Professional
      - More Friendly  
      - More Concise
      - More Detailed
      - Custom instructions
    - Copy to clipboard functionality

- **Password Protection**
  - Session-based authentication
  - Password: gogogochufalo

- **Render Deployment**
  - Live at https://coldemail-agent.onrender.com/
  - Gunicorn production server
  - Environment variable configuration

### New Files
- `templates/index_v2.html`: New wizard-style web interface
- `templates/login.html`: Login page
- `app.py`: Flask web application
- `Procfile`: Render deployment config
- `runtime.txt`: Python version specification

### Modified Files
- `src/email_agent.py`:
  - Added `generate_questionnaire()`: Generate profile questions
  - Added `build_profile_from_answers()`: Build profile from questionnaire
  - Added `find_target_recommendations()`: AI-powered target suggestions
  - Added `regenerate_email_with_style()`: Style-based email regeneration

- `src/web_scraper.py`:
  - Now uses Gemini's knowledge base first (fixes cloud server blocking)
  - Web scraping as fallback
  - Returns basic profile even if all methods fail

### New Dependencies
- `flask>=3.0.0`
- `gunicorn>=21.0.0`

---

## 2025-11-29: v1.2 - Switch to Gemini API

### Changes
- **API Migration**: Switched from OpenAI GPT-4o-mini to Google Gemini API
  - Default model changed to `gemini-2.0-flash`
  - Environment variable changed to `GEMINI_API_KEY` or `GOOGLE_API_KEY`
  - Removed `openai` dependency, added `google-generativeai` dependency

### Modified Files
- `src/email_agent.py`: Replaced OpenAI SDK with Gemini SDK
- `src/web_scraper.py`: Replaced OpenAI SDK with Gemini SDK
- `src/cli.py`: Updated default model name
- `requirements.txt`: Replaced dependency packages
- `README.md`: Updated API Key setup instructions

---

## 2025-11-29: v1.1 - Web Search Feature

### New Features
- **Web Search for Receiver Info**: Users only need to provide the receiver's name and field, and the system will automatically search and scrape relevant information from the web
  - Supports DuckDuckGo and Bing search engines
  - Automatically scrapes and parses web page content
  - Uses LLM to extract structured information (education, experience, skills, projects, etc.)

### New Files
- `src/web_scraper.py`: Web search and scraping module
  - `WebScraper` class: Search engine queries and web page scraping
  - `extract_person_profile_from_web()`: Extract person information from the web

### Modified Files
- `src/email_agent.py`: 
  - Added `from_web()` class method to `ReceiverProfile`
  - Added `sources` field to record information sources
- `src/cli.py`:
  - Added `--receiver-name` parameter
  - Added `--receiver-field` parameter
  - Added `--max-pages` parameter

### New Dependencies
- `requests>=2.31.0`
- `beautifulsoup4>=4.12.0`
