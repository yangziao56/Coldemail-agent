"""Service layer - Business logic modules.

Each service module has a clear interface and can be developed/tested independently.
"""

from .llm_service import LLMService
from .profile_service import ProfileService
from .email_service import EmailService
from .recommendation_service import RecommendationService

__all__ = [
    "LLMService",
    "ProfileService", 
    "EmailService",
    "RecommendationService",
]
