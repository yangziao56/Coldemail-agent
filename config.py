"""Global configuration values."""

import os

# Default Gemini model (can be overridden via env)
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# Default model for recommendations (OpenAI)
RECOMMENDATION_MODEL = os.environ.get("OPENAI_RECOMMENDATION_MODEL", "gpt-5.1")

# Toggle OpenAI built-in web_search for recommendations
USE_OPENAI_WEB_SEARCH = os.environ.get("USE_OPENAI_WEB_SEARCH", "true").lower() in ("1", "true", "yes")
