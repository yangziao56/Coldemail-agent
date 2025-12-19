"""Profile Service - User profile extraction and management.

This module handles:
- PDF resume parsing and profile extraction
- Questionnaire-based profile building
- Profile validation and normalization

Interface Contract:
- extract_from_pdf(pdf_path) -> ProfileBase
- extract_from_text(text) -> ProfileBase  
- build_from_questionnaire(answers) -> SenderProfile
- All methods raise ProfileServiceError on failure

Owner: Can be assigned to intern (with tests)
Status: Interface Defined - Implementation Pending
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PyPDF2 import PdfReader

from src.models import ProfileBase, SenderProfile


class ProfileServiceError(Exception):
    """Raised when profile extraction fails."""
    pass


@dataclass
class QuestionnaireAnswer:
    """A single questionnaire answer."""
    question: str
    answer: str


class ProfileService:
    """Service for profile extraction and management."""
    
    def __init__(self, llm_service=None):
        """Initialize with optional LLM service dependency.
        
        Args:
            llm_service: LLM service for AI extraction. If None, uses default.
        """
        self._llm = llm_service
    
    @property
    def llm(self):
        """Lazy load LLM service."""
        if self._llm is None:
            from src.services.llm_service import LLMService
            self._llm = LLMService.get_instance()
        return self._llm
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract raw text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            str: Extracted text content
            
        Raises:
            ProfileServiceError: If PDF cannot be read
        """
        try:
            reader = PdfReader(str(pdf_path))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            raise ProfileServiceError(f"Failed to read PDF: {e}") from e
    
    def extract_from_pdf(self, pdf_path: Path) -> ProfileBase:
        """Extract profile from a PDF resume.
        
        Args:
            pdf_path: Path to the PDF resume
            
        Returns:
            ProfileBase: Extracted profile data
            
        Raises:
            ProfileServiceError: If extraction fails
        """
        raw_text = self.extract_text_from_pdf(pdf_path)
        return self.extract_from_text(raw_text)
    
    def extract_from_text(self, text: str) -> ProfileBase:
        """Extract profile from raw text using LLM.
        
        Args:
            text: Raw text content (from PDF or document)
            
        Returns:
            ProfileBase: Extracted profile data
            
        Raises:
            ProfileServiceError: If extraction fails
        """
        prompt = self._build_extraction_prompt(text)
        
        try:
            response = self.llm.call(prompt, json_mode=True)
            return self._parse_profile_response(response, raw_text=text)
        except Exception as e:
            raise ProfileServiceError(f"Profile extraction failed: {e}") from e
    
    def build_from_questionnaire(
        self,
        answers: list[QuestionnaireAnswer],
        *,
        purpose: str,
        field: str,
    ) -> SenderProfile:
        """Build a sender profile from questionnaire answers.
        
        Args:
            answers: List of question-answer pairs
            purpose: User's outreach purpose
            field: User's professional field
            
        Returns:
            SenderProfile: Constructed profile
            
        Raises:
            ProfileServiceError: If profile building fails
        """
        prompt = self._build_questionnaire_prompt(answers, purpose, field)
        
        try:
            response = self.llm.call(prompt, json_mode=True)
            return self._parse_sender_profile_response(response)
        except Exception as e:
            raise ProfileServiceError(f"Profile building failed: {e}") from e
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build prompt for profile extraction."""
        return f'''Extract structured profile information from the following text.
Return a JSON object with these fields:
- name: string (person's full name)
- education: array of strings (degrees, schools, years)
- experiences: array of strings (job titles, companies, descriptions)
- skills: array of strings (technical and soft skills)
- projects: array of strings (notable projects or achievements)

If a field cannot be determined, use an empty array or "Unknown" for name.

TEXT:
{text}

Return ONLY the JSON object, no additional text.'''
    
    def _build_questionnaire_prompt(
        self,
        answers: list[QuestionnaireAnswer],
        purpose: str,
        field: str,
    ) -> str:
        """Build prompt for questionnaire-based profile building."""
        answers_text = "\n".join(
            f"Q: {a.question}\nA: {a.answer}" for a in answers
        )
        
        return f'''Build a professional profile from the following questionnaire answers.
The user's purpose is: {purpose}
The user's field is: {field}

ANSWERS:
{answers_text}

Return a JSON object with these fields:
- name: string
- education: array of strings
- experiences: array of strings
- skills: array of strings
- projects: array of strings
- motivation: string (why they want to reach out)
- ask: string (what they hope to get from the connection)

Return ONLY the JSON object, no additional text.'''
    
    def _parse_profile_response(self, response: str, *, raw_text: str) -> ProfileBase:
        """Parse LLM response into ProfileBase."""
        import json
        try:
            data = json.loads(response)
            return ProfileBase(
                name=data.get("name", "Unknown"),
                raw_text=raw_text,
                education=data.get("education", []),
                experiences=data.get("experiences", []),
                skills=data.get("skills", []),
                projects=data.get("projects", []),
            )
        except json.JSONDecodeError as e:
            raise ProfileServiceError(f"Invalid JSON response: {e}") from e
    
    def _parse_sender_profile_response(self, response: str) -> SenderProfile:
        """Parse LLM response into SenderProfile."""
        import json
        try:
            data = json.loads(response)
            return SenderProfile(
                name=data.get("name", "Unknown"),
                raw_text="",  # Built from questionnaire, no raw text
                education=data.get("education", []),
                experiences=data.get("experiences", []),
                skills=data.get("skills", []),
                projects=data.get("projects", []),
                motivation=data.get("motivation", ""),
                ask=data.get("ask", ""),
            )
        except json.JSONDecodeError as e:
            raise ProfileServiceError(f"Invalid JSON response: {e}") from e
