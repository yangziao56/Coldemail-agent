"""Data models - Pure data structures with no business logic."""

from .profile import ProfileBase, SenderProfile, ReceiverProfile
from .recommendation import Recommendation, RecommendationResult

__all__ = [
    "ProfileBase",
    "SenderProfile",
    "ReceiverProfile",
    "Recommendation",
    "RecommendationResult",
]
