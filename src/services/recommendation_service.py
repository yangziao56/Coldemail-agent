"""Recommendation Service - Target person discovery and ranking.

This module handles:
- Finding potential contact targets based on sender profile
- Web search integration for real person discovery
- Ranking and scoring recommendations

Interface Contract:
- find_recommendations(sender_profile, preferences) -> list[Recommendation]
- enrich_recommendation(recommendation) -> Recommendation
- All methods raise RecommendationServiceError on failure

Owner: Core Team (Senior) - Uses external APIs
Status: Interface Defined - Implementation Pending
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.models import SenderProfile, Recommendation, RecommendationResult


class RecommendationServiceError(Exception):
    """Raised when recommendation service fails."""
    pass


@dataclass
class RecommendationPreferences:
    """User preferences for target recommendations."""
    field: str
    purpose: str
    target_type: str | None = None  # e.g., "professor", "engineer", "investor"
    location: str | None = None
    industry: str | None = None
    seniority: str | None = None
    max_results: int = 10
    extra_context: dict[str, Any] = field(default_factory=dict)


class RecommendationService:
    """Service for finding and ranking target recommendations."""
    
    def __init__(self, llm_service=None, web_scraper=None):
        """Initialize with optional dependencies.
        
        Args:
            llm_service: LLM service for AI analysis. If None, uses default.
            web_scraper: Web scraper for enrichment. If None, creates default.
        """
        self._llm = llm_service
        self._web_scraper = web_scraper
    
    @property
    def llm(self):
        """Lazy load LLM service."""
        if self._llm is None:
            from src.services.llm_service import LLMService
            self._llm = LLMService.get_instance()
        return self._llm
    
    @property
    def web_scraper(self):
        """Lazy load web scraper."""
        if self._web_scraper is None:
            from src.web_scraper import WebScraper
            self._web_scraper = WebScraper()
        return self._web_scraper
    
    def find_recommendations(
        self,
        sender_profile: SenderProfile | dict,
        preferences: RecommendationPreferences,
    ) -> RecommendationResult:
        """Find recommended targets based on sender profile and preferences.
        
        Args:
            sender_profile: The sender's profile
            preferences: Search preferences
            
        Returns:
            RecommendationResult: List of recommendations with metadata
            
        Raises:
            RecommendationServiceError: If search fails
        """
        prompt = self._build_recommendation_prompt(sender_profile, preferences)
        
        try:
            # Use search-enabled LLM for grounded results
            response = self.llm.call_with_search(prompt, json_mode=True)
            return self._parse_recommendations(response)
        except Exception as e:
            raise RecommendationServiceError(f"Recommendation search failed: {e}") from e
    
    def enrich_recommendation(self, recommendation: Recommendation) -> Recommendation:
        """Enrich a recommendation with additional web data.
        
        Args:
            recommendation: Basic recommendation to enrich
            
        Returns:
            Recommendation: Enriched with additional details
            
        Raises:
            RecommendationServiceError: If enrichment fails
        """
        try:
            # Search for more info about the person
            search_results = self.web_scraper.search_person(
                recommendation.name,
                recommendation.field,
                max_results=3,
            )
            
            if search_results:
                # Fetch and extract additional context
                for result in search_results:
                    try:
                        content = self.web_scraper.fetch_page_content(result.url)
                        if content:
                            recommendation.sources.append(result.url)
                            # Could add more sophisticated extraction here
                    except Exception:
                        continue
            
            return recommendation
        except Exception as e:
            raise RecommendationServiceError(f"Enrichment failed: {e}") from e
    
    def _build_recommendation_prompt(
        self,
        sender_profile: SenderProfile | dict,
        preferences: RecommendationPreferences,
    ) -> str:
        """Build prompt for recommendation search."""
        # Handle both SenderProfile and dict
        if isinstance(sender_profile, dict):
            sender_name = sender_profile.get("name", "Unknown")
            sender_education = sender_profile.get("education", [])
            sender_experiences = sender_profile.get("experiences", [])
            sender_skills = sender_profile.get("skills", [])
        else:
            sender_name = sender_profile.name
            sender_education = sender_profile.education
            sender_experiences = sender_profile.experiences
            sender_skills = sender_profile.skills
        
        extra_context = ""
        if preferences.extra_context:
            extra_context = "\nAdditional context:\n"
            for key, value in preferences.extra_context.items():
                extra_context += f"- {key}: {value}\n"
        
        return f'''Find {preferences.max_results} real people who would be good networking targets.

SENDER PROFILE:
Name: {sender_name}
Education: {', '.join(sender_education) if sender_education else 'Not specified'}
Experience: {', '.join(sender_experiences) if sender_experiences else 'Not specified'}
Skills: {', '.join(sender_skills) if sender_skills else 'Not specified'}

SEARCH CRITERIA:
Field: {preferences.field}
Purpose: {preferences.purpose}
Target Type: {preferences.target_type or 'Any relevant professional'}
Location: {preferences.location or 'Any'}
Industry: {preferences.industry or 'Any'}
Seniority: {preferences.seniority or 'Any'}
{extra_context}

REQUIREMENTS:
1. Find REAL people with verifiable current positions
2. Each person should have public contact information or professional profile
3. Prioritize people who are likely to respond to cold outreach
4. Include match score (0-100) and reasoning for each
5. Include source URLs where possible

Return a JSON object with:
- recommendations: array of objects with:
  - name: string
  - title: string (current position)
  - organization: string
  - field: string
  - match_score: number (0-100)
  - match_reason: string
  - contact_info: string (email, LinkedIn, etc. if public)
  - sources: array of URLs
  - uncertainty: string (any caveats about the recommendation)

Return ONLY the JSON object, no additional text.'''
    
    def _parse_recommendations(self, response: str) -> RecommendationResult:
        """Parse LLM response into RecommendationResult."""
        import json
        try:
            data = json.loads(response)
            recommendations = []
            
            for item in data.get("recommendations", []):
                rec = Recommendation(
                    name=item.get("name", "Unknown"),
                    title=item.get("title", ""),
                    organization=item.get("organization", ""),
                    field=item.get("field", ""),
                    match_score=item.get("match_score", 0),
                    match_reason=item.get("match_reason", ""),
                    contact_info=item.get("contact_info", ""),
                    sources=item.get("sources", []),
                    uncertainty=item.get("uncertainty", ""),
                )
                recommendations.append(rec)
            
            return RecommendationResult(
                recommendations=recommendations,
                total_found=len(recommendations),
            )
        except json.JSONDecodeError as e:
            raise RecommendationServiceError(f"Invalid JSON response: {e}") from e
