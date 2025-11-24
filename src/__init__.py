"""Honest Connect Email Agent package."""

from .email_agent import ReceiverProfile, SenderProfile, build_prompt, generate_email

__all__ = [
    "SenderProfile",
    "ReceiverProfile",
    "build_prompt",
    "generate_email",
]
