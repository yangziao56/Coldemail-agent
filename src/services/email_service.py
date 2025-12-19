"""Email Service - Email generation and customization.

This module handles:
- Cold email generation from sender/receiver profiles
- Email style customization (professional, friendly, concise, etc.)
- Email regeneration with custom instructions

Interface Contract:
- generate(sender, receiver, goal) -> str
- regenerate(email, style, instruction) -> str
- All methods raise EmailServiceError on failure

Owner: Can be assigned to intern (with tests)
Status: Interface Defined - Implementation Pending
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from src.models import SenderProfile, ReceiverProfile


class EmailServiceError(Exception):
    """Raised when email generation fails."""
    pass


class EmailStyle(Enum):
    """Available email styles."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CONCISE = "concise"
    DETAILED = "detailed"
    CUSTOM = "custom"


@dataclass
class EmailRequest:
    """Request for email generation."""
    sender: SenderProfile
    receiver: ReceiverProfile
    goal: str
    style: EmailStyle = EmailStyle.PROFESSIONAL


@dataclass
class EmailResult:
    """Result of email generation."""
    subject: str
    body: str
    style: EmailStyle


class EmailService:
    """Service for email generation and customization."""
    
    def __init__(self, llm_service=None):
        """Initialize with optional LLM service dependency.
        
        Args:
            llm_service: LLM service for generation. If None, uses default.
        """
        self._llm = llm_service
    
    @property
    def llm(self):
        """Lazy load LLM service."""
        if self._llm is None:
            from src.services.llm_service import LLMService
            self._llm = LLMService.get_instance()
        return self._llm
    
    def generate(
        self,
        sender: SenderProfile,
        receiver: ReceiverProfile,
        goal: str,
        *,
        style: EmailStyle = EmailStyle.PROFESSIONAL,
    ) -> EmailResult:
        """Generate a cold email.
        
        Args:
            sender: Sender's profile
            receiver: Receiver's profile
            goal: The goal of the email (e.g., "Request a 20-min chat")
            style: Email style preference
            
        Returns:
            EmailResult: Generated email with subject and body
            
        Raises:
            EmailServiceError: If generation fails
        """
        prompt = self._build_generation_prompt(sender, receiver, goal, style)
        
        try:
            response = self.llm.call(prompt, json_mode=True)
            return self._parse_email_response(response, style)
        except Exception as e:
            raise EmailServiceError(f"Email generation failed: {e}") from e
    
    def regenerate(
        self,
        original_email: str,
        *,
        style: EmailStyle | None = None,
        custom_instruction: str | None = None,
        sender: SenderProfile | None = None,
        receiver: ReceiverProfile | None = None,
    ) -> EmailResult:
        """Regenerate an email with different style or custom instructions.
        
        Args:
            original_email: The original email text
            style: New style to apply (optional)
            custom_instruction: Custom instruction for modification
            sender: Sender profile for context (optional)
            receiver: Receiver profile for context (optional)
            
        Returns:
            EmailResult: Regenerated email
            
        Raises:
            EmailServiceError: If regeneration fails
        """
        prompt = self._build_regeneration_prompt(
            original_email, style, custom_instruction, sender, receiver
        )
        
        try:
            response = self.llm.call(prompt, json_mode=True)
            result_style = style or EmailStyle.CUSTOM
            return self._parse_email_response(response, result_style)
        except Exception as e:
            raise EmailServiceError(f"Email regeneration failed: {e}") from e
    
    def _build_generation_prompt(
        self,
        sender: SenderProfile,
        receiver: ReceiverProfile,
        goal: str,
        style: EmailStyle,
    ) -> str:
        """Build prompt for email generation."""
        style_instruction = self._get_style_instruction(style)
        
        return f'''Generate a cold email based on the following information.

SENDER PROFILE:
Name: {sender.name}
Education: {', '.join(sender.education) if sender.education else 'Not specified'}
Experience: {', '.join(sender.experiences) if sender.experiences else 'Not specified'}
Skills: {', '.join(sender.skills) if sender.skills else 'Not specified'}
Motivation: {sender.motivation}
Ask: {sender.ask}

RECEIVER PROFILE:
Name: {receiver.name}
Education: {', '.join(receiver.education) if receiver.education else 'Not specified'}
Experience: {', '.join(receiver.experiences) if receiver.experiences else 'Not specified'}
Context: {receiver.context or 'Not specified'}

GOAL: {goal}

STYLE: {style_instruction}

REQUIREMENTS:
1. Subject line should be compelling but not clickbait
2. Opening should establish a genuine connection point
3. Body should clearly state the value exchange
4. Close with a clear, easy-to-accept call-to-action
5. Keep it concise (under 200 words for body)
6. Be authentic - don't fabricate connections or experiences

Return a JSON object with:
- subject: string (email subject line)
- body: string (email body)

Return ONLY the JSON object, no additional text.'''
    
    def _build_regeneration_prompt(
        self,
        original_email: str,
        style: EmailStyle | None,
        custom_instruction: str | None,
        sender: SenderProfile | None,
        receiver: ReceiverProfile | None,
    ) -> str:
        """Build prompt for email regeneration."""
        instruction = custom_instruction or ""
        if style and not custom_instruction:
            instruction = self._get_style_instruction(style)
        
        context = ""
        if sender:
            context += f"\nSender: {sender.name}"
        if receiver:
            context += f"\nReceiver: {receiver.name}"
        
        return f'''Rewrite the following email according to the instruction.

ORIGINAL EMAIL:
{original_email}
{context}

INSTRUCTION: {instruction}

Return a JSON object with:
- subject: string (email subject line)
- body: string (email body)

Return ONLY the JSON object, no additional text.'''
    
    def _get_style_instruction(self, style: EmailStyle) -> str:
        """Get instruction text for email style."""
        instructions = {
            EmailStyle.PROFESSIONAL: "Write in a formal, professional tone suitable for business communication.",
            EmailStyle.FRIENDLY: "Write in a warm, approachable tone while maintaining professionalism.",
            EmailStyle.CONCISE: "Keep the email brief and to the point. Aim for under 100 words.",
            EmailStyle.DETAILED: "Include more context and details about the sender's background and goals.",
            EmailStyle.CUSTOM: "Follow the custom instruction provided.",
        }
        return instructions.get(style, instructions[EmailStyle.PROFESSIONAL])
    
    def _parse_email_response(self, response: str, style: EmailStyle) -> EmailResult:
        """Parse LLM response into EmailResult."""
        import json
        try:
            data = json.loads(response)
            return EmailResult(
                subject=data.get("subject", ""),
                body=data.get("body", ""),
                style=style,
            )
        except json.JSONDecodeError as e:
            raise EmailServiceError(f"Invalid JSON response: {e}") from e
