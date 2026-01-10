# Cold Email Generator

An intelligent cold email generation tool with a step-by-step wizard interface.

## Workflow

Workflow of the wizard UI (`templates/index_v2.html`) and backend APIs (`app.py`), focusing on when each piece of info is collected (top → bottom) and what each core call can use (dotted arrows):

```mermaid
flowchart TD
  start[Start] --> login[Login] --> mode{Select mode}

  mode --> quick_mode[Quick]
  mode --> pro_mode[Professional]

  pro_mode --> pro_track_step[Choose track] --> info_track[[professional track]]

  quick_mode --> step1_q[Step 1 choose purpose and field]
  pro_track_step --> step1_p[Step 1 choose purpose and field]

  step1_q --> info_purpose_field[[purpose and field]]
  step1_p --> info_purpose_field

  info_purpose_field --> step2[Step 2 sender info]
  step2 --> sender_src{Sender info source}

  sender_src --> api_upload_sender[POST /api/upload-sender-pdf] --> info_sender_resume[[sender profile from resume]]
  sender_src --> sender_q[Questionnaire] --> api_questions[POST /api/generate-questionnaire] --> info_sender_answers[[questionnaire answers]] --> api_build_sender[POST /api/profile-from-questionnaire] --> info_sender_qa[[sender profile from answers]]
  sender_src --> sender_link_notes[Link and notes] --> info_sender_link_notes[[sender profile link and notes]]

  info_sender_resume --> step3[Step 3 targets]
  info_sender_qa --> step3
  info_sender_link_notes --> step3

  step3 --> target_src{Targets source}

  target_src --> manual_targets[Manual targets] --> info_manual_targets[[manual targets list]] --> selected_targets[[selected targets]]
  manual_targets --> info_target_link_notes[[target profile link and notes]] --> selected_targets

  target_src --> upload_receiver_doc[Upload receiver doc] --> api_upload_receiver[POST /api/upload-receiver-doc] --> info_receiver_doc[[receiver profile from document]] --> selected_targets

  target_src --> recommend_targets[Recommendations] --> step3_prefs[Collect target preferences]
  step3_prefs --> info_target_prefs[[target preferences from questions]]
  step3_prefs --> info_targeting_details[[ideal target description keywords location reply vs prestige examples evidence]]
  info_target_prefs --> api_find_recs[POST /api/find-recommendations] --> info_candidates[[candidate list with evidence and uncertainty]] --> selected_targets

  selected_targets --> step4[Step 4 email setup]
  step4 --> info_email_instructions[[email goal ask value constraints hard rules evidence]]
  step4 --> info_template[[template text]]

  info_email_instructions --> step5[Step 5 generate email]
  info_template --> step5
  info_target_link_notes --> step5

  step5 --> receiver_ready{Receiver profile ready}
  receiver_ready --> info_receiver_doc
  receiver_ready --> api_search_receiver[POST /api/search-receiver] --> info_receiver_web[[receiver profile from web with sources]]

  info_receiver_web --> api_generate_email[POST /api/generate-email]
  info_receiver_doc --> api_generate_email
  api_generate_email --> info_email[[email output]]

  %% What each core call can use (dotted arrows point to the call)
  info_purpose_field -.-> api_find_recs
  info_track -.-> api_find_recs
  info_sender_resume -.-> api_find_recs
  info_sender_qa -.-> api_find_recs
  info_sender_link_notes -.-> api_find_recs
  info_target_prefs -.-> api_find_recs
  info_targeting_details -.-> api_find_recs

  info_purpose_field -.-> api_generate_email
  info_sender_resume -.-> api_generate_email
  info_sender_qa -.-> api_generate_email
  info_sender_link_notes -.-> api_generate_email
  info_target_link_notes -.-> api_generate_email
  info_receiver_doc -.-> api_generate_email
  info_receiver_web -.-> api_generate_email
  info_email_instructions -.-> api_generate_email
  info_template -.-> api_generate_email
```

Quick reading:
- Search people (`POST /api/find-recommendations`): uses boxes `purpose and field`, optional `professional track`, sender info (`sender profile from resume` or `sender profile from answers` or `sender profile link and notes`), plus targeting inputs (`target preferences from questions` and optional `ideal target description keywords location reply vs prestige examples evidence`).
- Generate email (`POST /api/generate-email`): uses boxes `purpose and field`, sender info, receiver profile (`receiver profile from document` or `receiver profile from web with sources`), plus optional `target profile link and notes`, `email goal ask value constraints hard rules evidence`, and `template text`.

🌐 **Live Demo**: [https://coldemail-agent.onrender.com/](https://coldemail-agent.onrender.com/)

## Features

### v3.0 (Current) - Mode Selection & Privacy 🎯

- **Mode Selection After Login**
  - **Quick Start Mode**: For users without a resume
    - No resume upload required
    - Optional: add resume/profile link/notes; otherwise answer a 5-question questionnaire
    - Perfect for beginners or quick outreach
  - **Professional Mode**: For users with a resume
    - Resume upload required
    - Track selection: Finance or Academic
    - Target options: Have targets vs Need recommendations
    - Tailored preference questions based on track

- **Privacy Notice Modal**
  - Clear data usage policy displayed after mode selection
  - Explains how AI processes data
  - Confirms data security and no permanent storage

- **Track-Specific Preferences**
  - Finance: Investment banking, Asset management, Private equity, Consulting
  - Academic: Research collaboration, PhD applications, Postdoc positions, Academic networking

### v2.2 - Gemini Google Search Integration 🔍

- **Real-time Web Search for Recommendations**
  - Uses Gemini's built-in Google Search grounding
  - Finds REAL people with verified current positions
  - No more DuckDuckGo timeout errors on cloud servers
  - Faster and more reliable than external web scraping

- **Bug Fixes**
  - Fixed: OpenAI `web_search` tool type not supported (400 error)
  - Fixed: DuckDuckGo search timeout on Render.com
  - Fixed: Step 1 Field selection was missing after merge

### v2.1 - Enhanced Target Management

- **Manual Target Document Upload**
  - Upload PDF, TXT, or MD files with target's information
  - Auto-extracts profile data using AI
  - Skips web search when document is provided

- **Target Profile Preview**
  - Click "📋 View" to see detailed profile before selecting
  - View match score, position, education, experience, skills, projects
  - Select target directly from the profile modal

### v2.0 - Web Interface with Smart Wizard

- **Step 1: Purpose Selection**
  - 4 purpose categories: Academic Outreach 🎓, Job Seeking 💼, Coffee Chat ☕, Other ✨
  - 4 field categories: AI/ML 🤖, Software Engineering 💻, Finance/Fintech 📈, Other 🔬
  - Custom input support for both

- **Step 2: Build Your Profile**
  - Option A: Upload PDF resume (recommended)
  - Option B: Quick 5-question questionnaire to build profile
    - Each question has 4 options including custom input

- **Step 3: Find Targets**
  - Manual input: Enter name and field directly
  - **NEW**: Upload target's document (PDF/TXT/MD)
  - AI Recommendations: Get top 10 matching contacts based on your profile
    - **NEW**: Click "📋 View" to see target profile
    - Multi-select targets for batch email generation
    - Options to generate more or add manually

- **Step 4: Generate & Customize Email**
  - Regenerate with different styles:
    - 📋 More Professional
    - 😊 More Friendly
    - ✂️ More Concise
    - 📝 More Detailed
    - ✏️ Custom instructions
  - Edit Subject/Body and copy subject, email, or all emails

### v1.x - CLI Tool

- **v1.2**: Switched to Google Gemini API
- **v1.1**: Web search for receiver info (name + field only)
- **v1.0**: PDF resume parsing
- **v0**: JSON input support

## Quick Start

### Web Interface (Recommended)

1. Visit [https://coldemail-agent.onrender.com/](https://coldemail-agent.onrender.com/)
2. Enter password: `gogogochufalo`
3. **Choose your mode:**
   - **Quick Start**: No resume? Build profile via questionnaire
   - **Professional**: Upload resume, choose Finance or Academic track
4. Review privacy notice and continue
5. Follow the wizard steps to generate your cold email

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up Google Gemini API Key:
   ```bash
   export GEMINI_API_KEY=your_api_key
   ```
   Get your API Key: https://makersuite.google.com/app/apikey

3. (Optional) Set up SerpAPI Key for accurate LinkedIn URLs:
   ```bash
   export SERPAPI_KEY=your_serpapi_key
   ```
   Get your API Key: https://serpapi.com/
   
   > Without SerpAPI, LinkedIn links will be search URLs. With SerpAPI, the system can find real LinkedIn profile URLs.

4. (Production) Set up persistent data directory for Render Disk:
   ```bash
   export DATA_DIR=/var/data
   ```
   > Local development uses `./data` by default. On Render, set this to your Disk mount path.

5. Run the web app:
   ```bash
   python app.py
   ```

4. Open http://localhost:5000 in your browser

### CLI Usage

#### Web Search Input

```bash
python -m src.cli \
  --sender-pdf /path/to/sender.pdf \
  --receiver-name "Andrew Ng" \
  --receiver-field "AI research, deep learning" \
  --motivation "Why you want to reach out" \
  --ask "What you hope they can help with" \
  --goal "Request a 20-min chat to discuss their recent projects"
```

#### PDF Input

```bash
python -m src.cli \
  --sender-pdf /path/to/sender.pdf \
  --receiver-pdf /path/to/receiver.pdf \
  --motivation "Why you want to reach out" \
  --ask "What you hope they can help with" \
  --goal "Request a 20-min chat"
```

#### JSON Input (v0 Compatible)

```bash
python -m src.cli \
  --sender-json examples/sender.json \
  --receiver-json examples/receiver.json \
  --goal "Request a 20-min chat"
```

## Tech Stack

- **Backend**: Python, Flask, Google Gemini API
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Render.com
- **PDF Parsing**: PyPDF2
- **Web Scraping**: BeautifulSoup4, Requests

## Prompt Data Collection

为了后续分析和模型改进，系统支持收集 `find_target` 和 `generate_email` 两个核心步骤的 prompt 与输出。

### 数据格式

每条记录包含：
- `id`: 唯一标识符
- `user_info`: 用户信息（purpose、field、sender_name）
- `prompt_find_target`: 找人步骤的 prompt
- `output_find_target`: 找人步骤的输出
- `prompt_generate_email`: 生成邮件的 prompt
- `output_generate_email`: 生成邮件的输出
- `timestamp`: 时间戳

### 配置

- 环境变量 `COLLECT_PROMPTS=false` 可禁用数据收集（默认启用）
- 数据存储于 `data/prompt_logs/{日期}/` 目录

### 导出

```python
from src.services.prompt_collector import prompt_collector

# 导出为 JSONL 格式
prompt_collector.export_all_to_jsonl("output.jsonl")

# 导出为 CSV 格式
prompt_collector.export_all_to_csv("output.csv")
```

## Benchmark (Finance)

Starter benchmark assets (schema v0.1 + 10 sample cases + rubric + survey template) live in `benchmarks/finance/`.

## License

MIT
