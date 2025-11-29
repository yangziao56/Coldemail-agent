# Development Log

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
