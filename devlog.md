# Development Log

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
