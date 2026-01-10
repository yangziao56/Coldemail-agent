"""Global configuration values."""

import os
from pathlib import Path

# ============== 数据存储目录配置 ==============
# Render Disk 挂载路径，本地开发时使用项目根目录下的 data/
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent / "data"))
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    # 本地测试时可能没有权限创建 /var/data，跳过
    pass

# Default Gemini model (can be overridden via env)
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# Gemini model for recommendations with Google Search grounding
GEMINI_SEARCH_MODEL = os.environ.get("GEMINI_SEARCH_MODEL", "gemini-2.0-flash")

# Toggle Gemini Google Search grounding for recommendations - ENABLED by default
USE_GEMINI_SEARCH = os.environ.get("USE_GEMINI_SEARCH", "true").lower() in ("1", "true", "yes")

# Default model for recommendations (OpenAI) - disabled by default due to web_search incompatibility
RECOMMENDATION_MODEL = os.environ.get("OPENAI_RECOMMENDATION_MODEL", "gpt-5.1")

# Toggle OpenAI built-in web_search for recommendations - DISABLED by default
# OpenAI API does not support 'web_search' tool type, causes errors
USE_OPENAI_WEB_SEARCH = os.environ.get("USE_OPENAI_WEB_SEARCH", "false").lower() in ("1", "true", "yes")

# Toggle using OpenAI for recommendations at all (fallback uses Gemini)
USE_OPENAI_RECOMMENDATIONS = os.environ.get("USE_OPENAI_RECOMMENDATIONS", "false").lower() in ("1", "true", "yes")
