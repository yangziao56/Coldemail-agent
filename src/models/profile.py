"""Profile data models.

Pure data structures with no business logic.
These can be safely used by any module.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
from typing import Any


@dataclass
class ProfileBase:
    """Base profile containing common fields."""
    name: str
    raw_text: str
    education: list[str] = dataclass_field(default_factory=list)
    experiences: list[str] = dataclass_field(default_factory=list)
    skills: list[str] = dataclass_field(default_factory=list)
    projects: list[str] = dataclass_field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "raw_text": self.raw_text,
            "education": self.education,
            "experiences": self.experiences,
            "skills": self.skills,
            "projects": self.projects,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileBase":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            raw_text=data.get("raw_text", ""),
            education=data.get("education", []),
            experiences=data.get("experiences", []),
            skills=data.get("skills", []),
            projects=data.get("projects", []),
        )


@dataclass
class SenderProfile(ProfileBase):
    """Sender profile with motivation and ask."""
    motivation: str = ""
    ask: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data["motivation"] = self.motivation
        data["ask"] = self.ask
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SenderProfile":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            raw_text=data.get("raw_text", ""),
            education=data.get("education", []),
            experiences=data.get("experiences", []),
            skills=data.get("skills", []),
            projects=data.get("projects", []),
            motivation=data.get("motivation", ""),
            ask=data.get("ask", ""),
        )


@dataclass
class ReceiverProfile(ProfileBase):
    """Receiver profile with context and sources."""
    context: str | None = None
    sources: list[str] = dataclass_field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        data["context"] = self.context
        data["sources"] = self.sources
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReceiverProfile":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            raw_text=data.get("raw_text", ""),
            education=data.get("education", []),
            experiences=data.get("experiences", []),
            skills=data.get("skills", []),
            projects=data.get("projects", []),
            context=data.get("context"),
            sources=data.get("sources", []),
        )
