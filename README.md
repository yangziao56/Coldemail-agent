# Cold Email Generator

An intelligent cold email generation tool with a step-by-step wizard interface.

🌐 **Live Demo**: [https://coldemail-agent.onrender.com/](https://coldemail-agent.onrender.com/)

## Workflow

Workflow of the wizard UI (`templates/index_v2.html`) and backend APIs (`app.py`), focusing on when each piece of info is collected (top → bottom) and what each core call can use (dotted arrows):

```mermaid
flowchart TD
  start([Start]) --> login["Login: /login"] --> mode{Mode}

  %% Step 1: intent info
  mode -->|Quick Start| qs_step1["Step 1 - Quick: set intent<br/>pick purpose + field"]
  mode -->|Professional| pro_track["Pro: select track<br/>finance / academic"] --> pro_intent["Auto: set purpose + field defaults"]
  qs_step1 --> ctx_intent["Purpose + field<br/>used for target search and email goal"]
  pro_intent --> ctx_intent

  %% Step 2: sender info
  ctx_intent --> step2["Step 2: collect sender info"]
  step2 --> sender_src{Sender source}

  sender_src -->|Resume PDF| sender_pdf["Resume PDF<br/>Pro required / Quick optional<br/>POST /api/upload-sender-pdf"]
  sender_pdf --> ctx_sender_rich["Sender profile - resume parsed<br/>name/edu/exp/skills/projects/raw_text<br/>plus optional link/notes"]

  sender_src -->|Questionnaire| q_questions["Questionnaire<br/>Quick fallback<br/>POST /api/generate-questionnaire OR /api/next-question"]
  q_questions --> q_answers["User answers<br/>stored in UI"]
  q_answers --> q_build["POST /api/profile-from-questionnaire"]
  q_build --> ctx_sender_mid["Sender profile - from questionnaire<br/>profile inferred from answers"]

  sender_src -->|Link/notes only| ctx_sender_light["Sender notes only<br/>Quick: raw_text from link and notes"]

  %% Step 3: targets + search people
  ctx_sender_rich --> step3["Step 3: find targets"]
  ctx_sender_mid --> step3
  ctx_sender_light --> step3
  step3 --> targets_src{How to get targets?}

  targets_src -->|Manual list| manual_targets["Manual targets<br/>name + field"] --> selected["Selected targets"]
  targets_src -->|Upload receiver doc| upload_doc["POST /api/upload-receiver-doc"] --> ctx_receiver_doc["Receiver profile - from document<br/>parsed from PDF, TXT, or MD"] --> selected

  targets_src -->|AI recommendations| pref_q["Preference Q&A optional<br/>POST /api/next-target-question"]
  pref_q --> ctx_prefs["Target preferences<br/>Q&A transcript and filters"]
  ctx_prefs --> rec_call["Search people: POST /api/find-recommendations<br/>Gemini Search grounding default"]
  rec_call --> rec_list["Candidate list<br/>name + position + match_score + reason<br/>sources when available"] --> selected

  %% Step 4: template
  selected --> step4["Step 4: template optional"] --> ctx_template["Email template text<br/>optional"]

  %% Step 5: generate email per target
  ctx_template --> step5["Step 5: generate emails per target"]
  step5 --> receiver_ready{Receiver info ready?}
  receiver_ready -->|Already have doc profile| ctx_receiver_doc --> gen_call["Generate email: POST /api/generate-email<br/>template optional"]
  receiver_ready -->|Need enrichment| search_receiver["POST /api/search-receiver<br/>uses name + field"] --> ctx_receiver_web["Receiver profile - web enriched<br/>from /api/search-receiver plus sources<br/>plus optional link and notes"] --> gen_call

  gen_call --> email_out["Email output<br/>Subject + body"] --> rewrite{Rewrite style?}
  rewrite -->|Yes| regen_api["POST /api/regenerate-email"] --> email_out
  rewrite -->|No| done([Done])

  %% Inputs used by core calls (dotted)
  ctx_intent -.-> rec_call
  ctx_sender_rich -.-> rec_call
  ctx_sender_mid -.-> rec_call
  ctx_sender_light -.-> rec_call
  ctx_prefs -.-> rec_call

  ctx_intent -.-> gen_call
  ctx_sender_rich -.-> gen_call
  ctx_sender_mid -.-> gen_call
  ctx_sender_light -.-> gen_call
  ctx_receiver_doc -.-> gen_call
  ctx_receiver_web -.-> gen_call
  ctx_template -.-> gen_call

  %% Styling
  classDef ctx fill:#f6f8fa,stroke:#57606a,color:#24292f;
  classDef api fill:#ddf4ff,stroke:#0969da,color:#0b3d91;
  classDef step fill:#fff8c5,stroke:#9a6700,color:#24292f;
  classDef choice fill:#ffebe9,stroke:#cf222e,color:#24292f;
  classDef out fill:#dafbe1,stroke:#1a7f37,color:#24292f;

  class ctx_intent,ctx_sender_rich,ctx_sender_mid,ctx_sender_light,ctx_prefs,ctx_receiver_doc,ctx_receiver_web,ctx_template ctx;
  class sender_pdf,q_questions,q_build,upload_doc,pref_q,rec_call,search_receiver,gen_call,regen_api api;
  class qs_step1,pro_track,pro_intent,step2,step3,step4,step5,q_answers step;
  class mode,sender_src,targets_src,receiver_ready,rewrite choice;
  class selected,rec_list,email_out out;
```

Quick reading:
- Search people (`/api/find-recommendations`): uses purpose + field, sender info (resume / questionnaire / notes), and target preferences (if provided).
- Generate email (`/api/generate-email`): uses purpose + field, sender info, receiver info (doc or web), and optional template text.
- Info richness (roughly): resume/doc uploads > questionnaire/web enrichment > link/notes only.

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

3. Run the web app:
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

## License

MIT
