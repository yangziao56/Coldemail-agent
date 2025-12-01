"""Global configuration values."""

import os

# Default Gemini model (can be overridden via env)
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# Default model for recommendations (OpenAI)
RECOMMENDATION_MODEL = os.environ.get("OPENAI_RECOMMENDATION_MODEL", "gpt-5.1")
