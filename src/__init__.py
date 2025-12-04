"""Honest Connect Email Agent package."""

from .email_agent import (
    ReceiverProfile,
    SenderProfile,
    build_prompt,
    extract_profile_from_pdf,
    extract_profile_from_text,
    extract_text_from_pdf,
    generate_email,
)

__all__ = [
    "SenderProfile",
    "ReceiverProfile",
    "build_prompt",
    "generate_email",
    "extract_text_from_pdf",
    "extract_profile_from_text",
    "extract_profile_from_pdf",
]
