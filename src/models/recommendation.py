"""Recommendation data models.

Pure data structures for recommendation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Any


@dataclass
class Recommendation:
    """A single target recommendation."""
    name: str
    title: str = ""
    organization: str = ""
    domain: str = ""  # Renamed from 'field' to avoid conflict
    match_score: int = 0
    match_reason: str = ""
    contact_info: str = ""
    sources: list[str] = dataclass_field(default_factory=list)
    uncertainty: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "title": self.title,
            "organization": self.organization,
            "field": self.domain,
            "match_score": self.match_score,
            "match_reason": self.match_reason,
            "contact_info": self.contact_info,
            "sources": self.sources,
            "uncertainty": self.uncertainty,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Recommendation":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            title=data.get("title", ""),
            organization=data.get("organization", ""),
            domain=data.get("field", ""),
            match_score=data.get("match_score", 0),
            match_reason=data.get("match_reason", ""),
            contact_info=data.get("contact_info", ""),
            sources=data.get("sources", []),
            uncertainty=data.get("uncertainty", ""),
        )


@dataclass
class RecommendationResult:
    """Result of a recommendation search."""
    recommendations: list[Recommendation] = dataclass_field(default_factory=list)
    total_found: int = 0
    search_query: str = ""
    search_metadata: dict[str, Any] = dataclass_field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "recommendations": [r.to_dict() for r in self.recommendations],
            "total_found": self.total_found,
            "search_query": self.search_query,
            "search_metadata": self.search_metadata,
        }
