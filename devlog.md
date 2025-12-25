# Development Log

## 2025-12-16: Context Expansion (Targeting + Email)

- Step 3: added optional structured targeting inputs (ideal target description, must-have/must-not keywords, location, reply vs prestige, examples, evidence) for both Quick and Professional, and passed them into `preferences` for `POST /api/find-recommendations`.
- Recommendations: updated prompt + normalization so each candidate can include `evidence`, `sources`, and `uncertainty` (and the UI modal now surfaces them).
- Step 4: added optional email instruction inputs (goal, ask, value, constraints, hard rules, evidence) and fed them into generation (goal/ask fields + sender free-text) to reduce hallucinations.
- Receiver enrichment: `POST /api/search-receiver` now returns `raw_text`, and `POST /api/generate-email` preserves receiver `sources` so the email prompt can cite verifiable info.
- Updated `README.md` workflow diagram to show the time order of info collection and what each core API call can use.

## 2025-12-20: UI/Flow Fixes & Crawler Integration

- Fixed a regex parsing bug in `index_v2.html` that caused card selection to fail in the two-column selection UI.
- Quick Start: restored/updated the back button behavior.
- PDF upload: added failure handling/logging to surface errors instead of silent failures.
- Professional flow: removed unused pre-steps to streamline the path.
- Find Matches: integrated the crawler agent into the matching flow.

Files: `templates/index_v2.html`, `src/agents/advisor_crawler.py`, `app.py`

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
