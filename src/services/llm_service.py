"""LLM Service - Abstraction layer for AI model calls.

This module provides a unified interface for calling different LLM providers
(Gemini, OpenAI) with consistent error handling and response formatting.

Interface Contract:
- All methods return str (raw text) or dict (parsed JSON)
- All methods raise LLMServiceError on failure
- Callers should not depend on specific LLM provider details

Owner: Core Team (Senior)
Status: Interface Defined - Implementation Pending
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal

import google.generativeai as genai
from openai import OpenAI

from config import DEFAULT_MODEL, GEMINI_SEARCH_MODEL


class LLMServiceError(Exception):
    """Raised when LLM call fails."""
    pass


@dataclass
class LLMResponse:
    """Standardized response from LLM calls."""
    content: str
    model: str
    provider: Literal["gemini", "openai"]
    raw_response: Any = None


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""
    
    @abstractmethod
    def call(self, prompt: str, *, json_mode: bool = False) -> str:
        """Call the LLM with a prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            json_mode: If True, expect JSON response
            
        Returns:
            str: The LLM response text
            
        Raises:
            LLMServiceError: If the call fails
        """
        pass
    
    @abstractmethod
    def call_with_search(self, prompt: str, *, json_mode: bool = False) -> str:
        """Call the LLM with web search grounding.
        
        Args:
            prompt: The prompt to send to the LLM
            json_mode: If True, expect JSON response
            
        Returns:
            str: The LLM response text with web-grounded information
            
        Raises:
            LLMServiceError: If the call fails
        """
        pass


class GeminiService(BaseLLMService):
    """Google Gemini LLM service implementation."""
    
    def __init__(self, model: str = DEFAULT_MODEL, search_model: str = GEMINI_SEARCH_MODEL):
        self.model = model
        self.search_model = search_model
        self._configured = False
    
    def _configure(self) -> None:
        """Configure Gemini API (lazy initialization)."""
        if self._configured:
            return
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise LLMServiceError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self._configured = True
    
    def call(self, prompt: str, *, json_mode: bool = False) -> str:
        """Call Gemini model."""
        self._configure()
        try:
            gen_config = None
            if json_mode:
                gen_config = genai.GenerationConfig(
                    response_mime_type="application/json"
                )
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt, generation_config=gen_config)
            return response.text
        except Exception as e:
            raise LLMServiceError(f"Gemini call failed: {e}") from e
    
    def call_with_search(self, prompt: str, *, json_mode: bool = False) -> str:
        """Call Gemini with Google Search grounding."""
        self._configure()
        try:
            from google.generativeai import protos
            
            gen_config = None
            if json_mode:
                gen_config = genai.GenerationConfig(
                    response_mime_type="application/json"
                )
            
            model = genai.GenerativeModel(self.search_model)
            google_search_tool = genai.Tool(
                google_search=protos.GoogleSearch()
            )
            response = model.generate_content(
                prompt,
                tools=[google_search_tool],
                generation_config=gen_config,
            )
            return response.text
        except Exception as e:
            raise LLMServiceError(f"Gemini search call failed: {e}") from e


class OpenAIService(BaseLLMService):
    """OpenAI LLM service implementation."""
    
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self._client: OpenAI | None = None
    
    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client (lazy initialization)."""
        if self._client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise LLMServiceError("OPENAI_API_KEY environment variable not set")
            self._client = OpenAI(api_key=api_key)
        return self._client
    
    def call(self, prompt: str, *, json_mode: bool = False) -> str:
        """Call OpenAI model."""
        try:
            client = self._get_client()
            response_format = {"type": "json_object"} if json_mode else None
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=response_format,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMServiceError(f"OpenAI call failed: {e}") from e
    
    def call_with_search(self, prompt: str, *, json_mode: bool = False) -> str:
        """OpenAI does not support native web search - falls back to regular call."""
        # Note: OpenAI's web_search tool type is not supported in standard API
        return self.call(prompt, json_mode=json_mode)


# Default service instance (can be swapped for testing)
class LLMService:
    """Facade for LLM services with provider switching."""
    
    _instance: BaseLLMService | None = None
    
    @classmethod
    def get_instance(cls) -> BaseLLMService:
        """Get the configured LLM service instance."""
        if cls._instance is None:
            cls._instance = GeminiService()
        return cls._instance
    
    @classmethod
    def set_instance(cls, service: BaseLLMService) -> None:
        """Set a custom LLM service (useful for testing)."""
        cls._instance = service
    
    @classmethod
    def reset(cls) -> None:
        """Reset to default service."""
        cls._instance = None


# Convenience functions for backward compatibility
def call_llm(prompt: str, *, json_mode: bool = False) -> str:
    """Call the default LLM service."""
    return LLMService.get_instance().call(prompt, json_mode=json_mode)


def call_llm_with_search(prompt: str, *, json_mode: bool = False) -> str:
    """Call the default LLM service with web search."""
    return LLMService.get_instance().call_with_search(prompt, json_mode=json_mode)
