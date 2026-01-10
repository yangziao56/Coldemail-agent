from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import google.generativeai as genai
from google import genai as genai_new  # New google-genai package for search
from google.genai import types as genai_types
from openai import OpenAI
from PyPDF2 import PdfReader

from config import (
    DEFAULT_MODEL,
    GEMINI_SEARCH_MODEL,
    USE_GEMINI_SEARCH,
    RECOMMENDATION_MODEL,
    USE_OPENAI_WEB_SEARCH,
    USE_OPENAI_RECOMMENDATIONS,
)

# Prompt 数据收集 (可选)
try:
    from src.services.prompt_collector import prompt_collector
    PROMPT_COLLECTOR_AVAILABLE = True
except ImportError:
    PROMPT_COLLECTOR_AVAILABLE = False
    prompt_collector = None

@dataclass
class ProfileBase:
    name: str
    raw_text: str
    education: list[str]
    experiences: list[str]
    skills: list[str]
    projects: list[str]


@dataclass
class SenderProfile(ProfileBase):
    motivation: str
    ask: str

    @classmethod
    def from_json(cls, path: Path) -> "SenderProfile":
        data = _load_json(path)
        return cls(
            name=_require_field(data, "name", path),
            raw_text=_require_field(data, "raw_text", path),
            education=_load_str_list(data, "education", path),
            experiences=_load_str_list(data, "experiences", path),
            skills=_load_str_list(data, "skills", path),
            projects=_load_str_list(data, "projects", path),
            motivation=_require_field(data, "motivation", path),
            ask=_require_field(data, "ask", path),
        )

    @classmethod
    def from_pdf(
        cls,
        pdf_path: Path,
        *,
        motivation: str,
        ask: str,
        model: str = DEFAULT_MODEL,
    ) -> "SenderProfile":
        motivation_text = motivation.strip()
        ask_text = ask.strip()
        if not motivation_text or not ask_text:
            raise ValueError("Both motivation and ask are required when loading profiles from PDF")

        profile = extract_profile_from_pdf(pdf_path, model=model)
        return cls(
            name=profile.name,
            raw_text=profile.raw_text,
            education=profile.education,
            experiences=profile.experiences,
            skills=profile.skills,
            projects=profile.projects,
            motivation=motivation_text,
            ask=ask_text,
        )


@dataclass
class ReceiverProfile(ProfileBase):
    context: str | None = None
    sources: list[str] | None = None  # Web sources if scraped from internet

    @classmethod
    def from_json(cls, path: Path) -> "ReceiverProfile":
        data = _load_json(path)
        return cls(
            name=_require_field(data, "name", path),
            raw_text=_require_field(data, "raw_text", path),
            education=_load_str_list(data, "education", path),
            experiences=_load_str_list(data, "experiences", path),
            skills=_load_str_list(data, "skills", path),
            projects=_load_str_list(data, "projects", path),
            context=data.get("context"),
        )

    @classmethod
    def from_pdf(
        cls,
        pdf_path: Path,
        *,
        model: str = DEFAULT_MODEL,
        context: str | None = None,
    ) -> "ReceiverProfile":
        profile = extract_profile_from_pdf(pdf_path, model=model)
        return cls(
            name=profile.name,
            raw_text=profile.raw_text,
            education=profile.education,
            experiences=profile.experiences,
            skills=profile.skills,
            projects=profile.projects,
            context=context.strip() if isinstance(context, str) and context.strip() else None,
        )

    @classmethod
    def from_web(
        cls,
        name: str,
        field: str,
        *,
        model: str = DEFAULT_MODEL,
        context: str | None = None,
        max_pages: int = 3,
    ) -> "ReceiverProfile":
        """
        Create a ReceiverProfile by searching the web for information about a person.
        
        Args:
            name: The person's name to search for
            field: Their field/domain (e.g., "AI research", "machine learning professor")
            model: Gemini model to use for extraction
            context: Optional additional context about the person
            max_pages: Maximum number of web pages to scrape
            
        Returns:
            ReceiverProfile with information scraped from the web
        """
        from .web_scraper import extract_person_profile_from_web
        
        scraped_info = extract_person_profile_from_web(
            name=name,
            field=field,
            model=model,
            max_pages=max_pages,
        )
        
        return cls(
            name=scraped_info.name,
            raw_text=scraped_info.raw_text,
            education=scraped_info.education,
            experiences=scraped_info.experiences,
            skills=scraped_info.skills,
            projects=scraped_info.projects,
            context=context.strip() if isinstance(context, str) and context.strip() else None,
            sources=scraped_info.sources,
        )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON in {path}: {exc}") from exc


def _require_field(data: dict[str, Any], key: str, source: Path | str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Field '{key}' is required and must be a non-empty string in {source}"
        )
    return value.strip()


def _load_str_list(data: dict[str, Any], key: str, source: Path | str) -> list[str]:
    value = data.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Field '{key}' must be a list of strings in {source}")
    cleaned: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())
    return cleaned


def extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    combined = "\n".join(text.strip() for text in pages_text if text and text.strip())
    cleaned = combined.strip()
    if not cleaned:
        raise ValueError(f"No extractable text found in PDF {pdf_path}")
    return cleaned


def _validate_linkedin_url(url: str | None, grounding_urls: list[str] | None = None) -> str | None:
    """
    Validate a LinkedIn URL format.
    
    Note: We cannot verify if the URL actually exists without making an HTTP request.
    This function only validates the URL format and filters obviously fake patterns.
    
    Args:
        url: The URL to validate
        grounding_urls: Not used anymore (kept for compatibility)
        
    Returns:
        The validated URL if it looks legitimate, None otherwise
    """
    if not url or not isinstance(url, str):
        return None
    
    url = url.strip()
    
    # Must be a LinkedIn URL (personal profile or company)
    valid_prefixes = [
        "https://www.linkedin.com/in/",
        "https://linkedin.com/in/",
        "https://www.linkedin.com/company/",
        "https://linkedin.com/company/",
    ]
    if not any(url.startswith(prefix) for prefix in valid_prefixes):
        return None
    
    # Extract the profile ID/slug
    try:
        if '/in/' in url:
            parts = url.rstrip('/').split('/in/')
            if len(parts) != 2:
                return None
            profile_slug = parts[1].split('/')[0].split('?')[0]
        elif '/company/' in url:
            parts = url.rstrip('/').split('/company/')
            if len(parts) != 2:
                return None
            profile_slug = parts[1].split('/')[0].split('?')[0]
        else:
            return None
        
        # Profile slug should be reasonable (not empty, not too short)
        if not profile_slug or len(profile_slug) < 2:
            return None
        
        # Check for obviously fake patterns
        fake_patterns = ['example', 'sample', 'test', 'fake', 'placeholder', 'xxx', 'yyy', 'abc123', 'user123']
        if any(pattern in profile_slug.lower() for pattern in fake_patterns):
            print(f"[LinkedIn] Filtered fake pattern URL: {url}")
            return None
            
    except Exception:
        return None
    
    # Note: We no longer check grounding_urls because Google returns redirect URLs
    # that don't contain the actual LinkedIn URLs
    return url


def _profile_from_dict(profile_data: dict[str, Any], *, raw_text: str) -> ProfileBase:
    return ProfileBase(
        name=_require_field(profile_data, "name", "extracted profile"),
        raw_text=raw_text,
        education=_load_str_list(profile_data, "education", "extracted profile"),
        experiences=_load_str_list(profile_data, "experiences", "extracted profile"),
        skills=_load_str_list(profile_data, "skills", "extracted profile"),
        projects=_load_str_list(profile_data, "projects", "extracted profile"),
    )


def _configure_gemini() -> None:
    """Configure Gemini API with the API key from environment."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable."
        )
    genai.configure(api_key=api_key)


def _call_gemini(prompt: str, *, model: str = DEFAULT_MODEL, json_mode: bool = False) -> str:
    """Call Gemini API and return the response text."""
    _configure_gemini()
    
    generation_config = {}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"
    
    gemini_model = genai.GenerativeModel(model, generation_config=generation_config or None)
    response = gemini_model.generate_content(prompt)
    
    if not response.text:
        raise RuntimeError("Gemini response did not contain any content")
    return response.text


def _extract_json_from_text(text: str) -> str:
    """
    Extract JSON from text that may contain markdown code blocks or other content.
    """
    import re
    
    # Try to find JSON in markdown code blocks
    json_block_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
    matches = re.findall(json_block_pattern, text)
    if matches:
        for match in matches:
            try:
                json.loads(match.strip())
                return match.strip()
            except json.JSONDecodeError:
                continue
    
    # Try to find raw JSON object
    # Look for outermost { ... }
    brace_start = text.find('{')
    if brace_start != -1:
        depth = 0
        for i, char in enumerate(text[brace_start:], brace_start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    try:
                        candidate = text[brace_start:i+1]
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        continue
    
    # Return original text if no JSON found
    return text


def _call_gemini_with_search(prompt: str, *, model: str = GEMINI_SEARCH_MODEL, json_mode: bool = False, return_grounding_urls: bool = False) -> str | tuple[str, list[str]]:
    """
    Call Gemini API with Google Search grounding enabled using the new google-genai package.
    This allows the model to search the web for real-time information.
    
    NOTE: Google Search grounding does NOT support JSON mode, so we always use text mode
    and manually extract JSON from the response.
    
    Args:
        prompt: The prompt to send
        model: The model to use
        json_mode: Whether the response should be JSON (we'll extract it manually)
        return_grounding_urls: If True, also return list of grounding source URLs
    
    Returns:
        If return_grounding_urls is False: response text
        If return_grounding_urls is True: tuple of (response text, list of grounding URLs)
    """
    # Use new google-genai package for search capability
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required")
    
    client = genai_new.Client(api_key=api_key)
    
    # Create GoogleSearch tool
    google_search_tool = genai_types.Tool(
        google_search=genai_types.GoogleSearch()
    )
    
    # Generate content with search
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            tools=[google_search_tool]
        )
    )
    
    if not response.text:
        raise RuntimeError("Gemini response with search did not contain any content")
    
    # Extract JSON if requested
    result_text = response.text
    if json_mode:
        result_text = _extract_json_from_text(response.text)
    
    if return_grounding_urls:
        grounding_urls = []
        try:
            # Extract grounding metadata from response (new API structure)
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    metadata = candidate.grounding_metadata
                    # Try to get grounding chunks/sources
                    if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                        for chunk in metadata.grounding_chunks:
                            if hasattr(chunk, 'web') and chunk.web:
                                if hasattr(chunk.web, 'uri') and chunk.web.uri:
                                    grounding_urls.append(chunk.web.uri)
                    # Try grounding_supports
                    if hasattr(metadata, 'grounding_supports') and metadata.grounding_supports:
                        for support in metadata.grounding_supports:
                            if hasattr(support, 'grounding_chunk_indices'):
                                pass  # These reference the chunks above
                    # Try web_search_queries to see what was searched
                    if hasattr(metadata, 'web_search_queries') and metadata.web_search_queries:
                        print(f"[Grounding] Search queries: {metadata.web_search_queries}")
        except Exception as e:
            print(f"[Grounding] Could not extract grounding URLs: {e}")
        
        print(f"[Grounding] Found {len(grounding_urls)} source URLs from search")
        return result_text, grounding_urls
    
    return result_text


def _get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI models")
    return OpenAI(api_key=api_key)


def _call_openai_json(prompt: str, *, model: str) -> str:
    """Call OpenAI chat completion and return the response text."""
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a concise assistant that returns strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI response did not contain any content")
    return content


def _call_openai_json_with_web_search(prompt: str, *, model: str) -> str:
    """
    Call OpenAI chat completion with built-in web_search tool support.
    """
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a concise research assistant. "
                    "Use the web_search tool to gather real names and facts before answering. "
                    "Respond with strict JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        tools=[{"type": "web_search"}],
        tool_choice="auto",
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI response did not contain any content")
    return content


def extract_profile_from_text(
    resume_text: str, *, model: str = DEFAULT_MODEL
) -> ProfileBase:
    cleaned_text = resume_text.strip()
    if not cleaned_text:
        raise ValueError("Resume text must be a non-empty string")

    prompt = (
        "Extract a structured profile from the provided resume text. "
        "Return strict JSON with the keys: name (string), education (list of strings), "
        "experiences (list of strings), skills (list of strings), projects (list of strings).\n\n"
        f"Resume text:\n{cleaned_text}\n\nReturn JSON only."
    )

    content = _call_gemini(prompt, model=model, json_mode=True)
    
    try:
        profile_data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse profile extraction response as JSON: {exc}") from exc

    return _profile_from_dict(profile_data, raw_text=cleaned_text)


def extract_profile_from_pdf(
    pdf_path: Path, *, model: str = DEFAULT_MODEL
) -> ProfileBase:
    pdf_text = extract_text_from_pdf(pdf_path)
    return extract_profile_from_text(pdf_text, model=model)


def build_prompt(
    sender: SenderProfile,
    receiver: ReceiverProfile,
    goal: str,
    template: str | None = None,
) -> list[dict[str, str]]:
    goal_text = goal.strip()
    if not goal_text:
        raise ValueError("Goal must be a non-empty string")

    def _format_section(title: str, items: list[str]) -> str:
        if not items:
            return f"- {title}: (not specified)\n"
        bullet_points = "\n".join(f"  • {item}" for item in items)
        return f"- {title}:\n{bullet_points}\n"

    # Base system instruction
    system_content = (
        "You craft sincere, concise first-contact cold emails that help two people build a genuine connection. "
        "Use only facts present in the sender/receiver details or explicitly provided evidence; do not invent relationships, meetings, achievements, or affiliations. "
        "If information is missing, keep it generic rather than guessing. "
        "Follow this structure: Subject -> opening reason based on receiver evidence -> brief common ground -> value the sender can offer -> one clear ask (with time or a lightweight option) -> polite opt-out -> sign-off. "
        "Output a complete email with a Subject line and body that is ready to paste into an email client."
    )

    # If a user template is provided, tell the model how to use it
    if template and template.strip():
        system_content += (
            " When a user-provided email template is included, you must use it as the primary structure and tone: "
            "keep its overall flow and key phrases where reasonable, but adapt and fill in details using the sender "
            "and receiver information so the result is a polished, ready-to-send cold email."
        )

    system_message = {
        "role": "system",
        "content": system_content,
    }

    # Core content describing profiles and goal
    base_user_content = (
        "Sender profile:\n"
        f"- Name: {sender.name}\n"
        f"- Motivation: {sender.motivation}\n"
        f"- Ask: {sender.ask}\n"
        + _format_section("Education", sender.education)
        + _format_section("Experiences", sender.experiences)
        + _format_section("Skills", sender.skills)
        + _format_section("Projects", sender.projects)
        + "Sender background (free text):\n"
        + f"{sender.raw_text}\n\n"
        + "Receiver profile:\n"
        + f"- Name: {receiver.name}\n"
        + (f"- Context: {receiver.context}\n" if receiver.context else "")
        + (f"- Sources: {', '.join(receiver.sources)}\n" if receiver.sources else "")
        + _format_section("Education", receiver.education)
        + _format_section("Experiences", receiver.experiences)
        + _format_section("Skills", receiver.skills)
        + _format_section("Projects", receiver.projects)
        + "Receiver background (free text):\n"
        + f"{receiver.raw_text}\n\n"
        + f"Goal: {goal_text}\n\n"
    )

    if template and template.strip():
        # Template-guided generation
        user_content = (
            base_user_content
            + "The user has provided an email template they'd like to base the message on.\n"
            + "Use this template as the main structure and tone. Keep the subject and body well-formed and ready to send.\n\n"
            + "User email template (between <template> tags):\n"
            + "<template>\n"
            + template.strip()
            + "\n</template>\n\n"
            + "Please return a single finished email with:\n"
            + "1) A subject line (you may adapt the template subject if present)\n"
            + "2) A body (max ~250 words) that follows the template's flow while integrating specific, relevant details from the profiles above."
        )
    else:
        # Default smart generation (current behavior)
        user_content = (
            base_user_content
            + "Please return:\n"
            + "1) A concise, specific subject line\n"
            + "2) A short email body (max ~200 words) that feels human, references shared interests or context, and ends with a clear but polite call to action."
        )

    user_message = {
        "role": "user",
        "content": user_content,
    }

    return [system_message, user_message]


def generate_email(
    sender: SenderProfile,
    receiver: ReceiverProfile,
    goal: str,
    *,
    model: str = DEFAULT_MODEL,
    template: str | None = None,
    session_id: str | None = None,  # 用于数据收集
) -> str:
    messages = build_prompt(sender, receiver, goal, template=template)
    
    # Combine system and user messages into a single prompt for Gemini
    system_content = messages[0]["content"]
    user_content = messages[1]["content"]
    prompt = f"System instruction: {system_content}\n\nUser request:\n{user_content}"
    
    content = _call_gemini(prompt, model=model)
    result = content.strip()
    
    # 收集 prompt 数据
    if PROMPT_COLLECTOR_AVAILABLE and prompt_collector and session_id:
        prompt_collector.record_generate_email(
            session_id=session_id,
            prompt=prompt,
            output=result,
            metadata={"model": model, "goal": goal}
        )
    
    return result


def generate_questionnaire(purpose: str, field: str, *, model: str = DEFAULT_MODEL) -> list[dict]:
    """
    Generate 5 questionnaire questions to quickly build a user profile.
    Each question has 4 options, with the last option being a custom input.
    
    Args:
        purpose: The user's purpose (academic, job seeking, coffee chat, etc.)
        field: The user's field of interest
        model: Gemini model to use
        
    Returns:
        List of question dictionaries with 'question' and 'options' keys
    """
    prompt = f"""You are helping create a quick profile questionnaire for someone who wants to write cold emails.

Their purpose: {purpose}
Their field of interest: {field}

Generate exactly 5 questions that will help understand this person's background and qualifications.
Each question should have exactly 4 options, where the 4th option is always "Other (please specify)" for custom input.

The questions should cover:
1. Educational background
2. Work experience level
3. Key skills or expertise
4. Notable achievements or projects
5. What they're looking for (specific goals)

Return a JSON array with this exact structure:
[
    {{
        "question": "What is your highest level of education?",
        "options": ["Bachelor's degree", "Master's degree", "PhD", "Other (please specify)"]
    }},
    ...
]

Return JSON only, no other text."""

    content = _call_gemini(prompt, model=model, json_mode=True)
    
    try:
        questions = json.loads(content)
        return questions
    except json.JSONDecodeError:
        # Return default questions if parsing fails
        return [
            {
                "question": "What is your highest level of education?",
                "options": ["Bachelor's degree", "Master's degree", "PhD", "Other (please specify)"]
            },
            {
                "question": "How many years of experience do you have?",
                "options": ["0-2 years", "3-5 years", "5+ years", "Other (please specify)"]
            },
            {
                "question": "What is your primary skill area?",
                "options": ["Technical/Engineering", "Research/Academic", "Business/Management", "Other (please specify)"]
            },
            {
                "question": "What is your most notable achievement?",
                "options": ["Published research", "Successful project", "Industry recognition", "Other (please specify)"]
            },
            {
                "question": "What are you hoping to achieve?",
                "options": ["Research opportunity", "Job/internship", "Mentorship", "Other (please specify)"]
            }
        ]


def generate_next_question(
    purpose: str,
    field: str,
    history: list[dict[str, str]],
    *,
    max_questions: int = 5,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Generate the next questionnaire question interactively based on previous Q&A.
    
    Args:
        purpose: The user's purpose
        field: The user's field of interest
        history: List of {"question": str, "answer": str} for previous turns
        max_questions: Soft cap on total questions before suggesting to stop
        model: Gemini model to use
        
    Returns:
        Dict with either:
          {"done": True, "reason": "..."} or
          {"done": False, "question": "...", "meta": {"reason": "..." }}
    """
    asked_count = sum(
        1
        for qa in (history or [])
        if isinstance(qa, dict) and str(qa.get("question", "") or "").strip()
    )
    if max_questions is not None and int(max_questions) > 0 and asked_count >= int(max_questions):
        return {
            "done": True,
            "reason": f"Reached the maximum of {int(max_questions)} questions.",
        }

    # Build history text
    history_lines: list[str] = []
    for idx, qa in enumerate(history, start=1):
        q = str(qa.get("question", "") or "").strip()
        a = str(qa.get("answer", "") or "").strip()
        if not q:
            continue
        history_lines.append(f"Q{idx}: {q}\nA{idx}: {a or '(no answer)'}")
    history_text = "\n\n".join(history_lines) if history_lines else "None yet."

    prompt = f"""You are designing an interactive questionnaire to quickly understand a person who wants to send cold emails.

Their outreach purpose: {purpose or 'Not specified'}
Their field of interest: {field or 'Not specified'}

You ask ONE question at a time.
You can see the history of questions already asked and the user's answers:

{history_text}

Goal of the questionnaire:
- In at most {max_questions} questions total, collect enough information to build a basic professional profile for writing a personalized cold email.
- The profile should cover: education, experience level, key skills, notable projects/achievements, and what they are looking for (goals).
- Each new question should try to fill in missing or weakly covered areas based on the history.

INSTRUCTIONS:
1. First decide if you need to ask another question.
   - If you already have enough information for a basic profile OR
     you have already asked {max_questions} questions, you should stop.
2. If you need another question:
   - Ask exactly ONE clear question.
   - Provide 3-5 answer options for this question as a list of short phrases.
   - The LAST option must always be "Other (please specify)" to allow a custom answer.
   - Do NOT repeat previous questions.
   - Tailor the question to the given purpose and field and the previous answers.

Return STRICT JSON with this schema:

If you want to stop asking:
{{
  "done": true,
  "reason": "short explanation of why no more questions are needed"
}}

If you want to ask another question:
{{
  "done": false,
  "question": "Your next question here",
  "options": ["option 1", "option 2", "option 3", "Other (please specify)"],
  "meta": {{
    "reason": "short explanation of what this question is trying to capture (e.g., skills, projects, goals)"
  }}
}}

Return JSON only, with no additional text."""

    content = _call_gemini(prompt, model=model, json_mode=True)
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object for next question")
        # Minimal normalization
        if "done" not in data:
            data["done"] = False
        return data
    except (json.JSONDecodeError, ValueError):
        # Fallback: ask a generic question with simple options
        return {
            "done": False,
            "question": "Which aspect of your background do you think is most relevant for this outreach?",
            "options": [
                "My education",
                "My work experience",
                "My projects or achievements",
                "Other (please specify)",
            ],
            "meta": {"reason": "generic fallback question"},
        }


def generate_next_target_question(
    purpose: str,
    field: str,
    sender_profile: dict | None,
    history: list[dict[str, str]],
    *,
    max_questions: int = 5,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Generate the next interactive preference question for finding target contacts.
    
    Args:
        purpose: User's outreach purpose
        field: Target field/specialization
        sender_profile: Optional sender profile dict for context
        history: List of {"question": str, "answer": str} for previous preference questions
        max_questions: Soft cap on total preference questions
        model: Gemini model to use
    """
    asked_count = sum(
        1
        for qa in (history or [])
        if isinstance(qa, dict) and str(qa.get("question", "") or "").strip()
    )
    if max_questions is not None and int(max_questions) > 0 and asked_count >= int(max_questions):
        return {
            "done": True,
            "reason": f"Reached the maximum of {int(max_questions)} questions.",
        }

    history_lines: list[str] = []
    for idx, qa in enumerate(history, start=1):
        q = str(qa.get("question", "") or "").strip()
        a = str(qa.get("answer", "") or "").strip()
        if not q:
            continue
        history_lines.append(f"Q{idx}: {q}\nA{idx}: {a or '(no answer)'}")
    history_text = "\n\n".join(history_lines) if history_lines else "None yet."

    sender_summary = ""
    if sender_profile:
        sender_summary = _build_sender_context(sender_profile)

    prompt = f"""You are designing an interactive preference questionnaire to help select ideal targets for cold outreach.

User's outreach purpose: {purpose or 'Not specified'}
User's primary field/interest: {field or 'Not specified'}

Here is a brief summary of the sender's background (may be empty):
{sender_summary or 'Not available.'}

You ask ONE preference question at a time to clarify what kind of people we should recommend (targets).
You can see the history of preference questions already asked and the user's answers:

{history_text}

Goal of this preference questionnaire:
- In at most {max_questions} questions total, collect enough information about the user's targeting preferences.
- Preferences may include: desired seniority, organization type, specific subfields, type of opportunity (mentorship, job, collaboration, etc.), desired prominence (global leader vs. more accessible), geography, or other relevant filters.
- Each new question should focus on ONE dimension and avoid repeating covered dimensions unless genuinely needed.

INSTRUCTIONS:
1. First decide if you need to ask another preference question.
   - If you already have enough information for reasonable targeting OR
     you have already asked {max_questions} questions, you should stop.
2. If you need another question:
   - Ask exactly ONE clear preference question.
   - Provide 3-5 answer options as short phrases.
   - The LAST option must always be "Other (please specify)" to allow a custom answer.
   - Do NOT repeat previous questions.
   - Tailor the question to the user's purpose, field, sender background (if available), and previous answers.

Return STRICT JSON with this schema:

If you want to stop asking:
{{
  "done": true,
  "reason": "short explanation of why no more preference questions are needed"
}}

If you want to ask another question:
{{
  "done": false,
  "question": "Your next preference question here",
  "options": ["option 1", "option 2", "option 3", "Other (please specify)"],
  "meta": {{
    "dimension": "short label for what this question is about (e.g., seniority, org_type, prominence, outreach_goal, geography, subfield, other)",
    "reason": "short explanation of why this preference matters"
  }}
}}

Return JSON only, with no additional text."""

    content = _call_gemini(prompt, model=model, json_mode=True)
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object for next target preference question")
        if "done" not in data:
            data["done"] = False
        return data
    except (json.JSONDecodeError, ValueError):
        return {
            "done": False,
            "question": "What type of target would you most like to reach (for example, seniority or role)?",
            "options": [
                "Senior IC (Staff/Principal level)",
                "Leadership (Director/VP/C-level)",
                "Peers at a similar level to me",
                "Other (please specify)",
            ],
            "meta": {
                "dimension": "seniority",
                "reason": "fallback question about target seniority",
            },
        }

def build_profile_from_answers(
    purpose: str,
    field: str,
    answers: list[str],
    *,
    model: str = DEFAULT_MODEL
) -> dict:
    """
    Build a sender profile from questionnaire answers.
    
    Args:
        purpose: The user's purpose
        field: The user's field of interest
        answers: List of answers to the questionnaire
        model: Gemini model to use
        
    Returns:
        Dictionary with profile information
    """
    answers_text = "\n".join(f"- {answer}" for answer in answers if answer)
    
    prompt = f"""Based on the following questionnaire answers, create a professional profile summary.

Purpose: {purpose}
Field: {field}

Answers:
{answers_text}

Return a JSON object with:
{{
    "name": "User",
    "summary": "A brief professional summary based on the answers",
    "education": ["list of educational background items"],
    "experiences": ["list of experience items"],
    "skills": ["list of relevant skills"],
    "projects": ["list of notable projects or achievements"]
}}

Infer reasonable details from the answers. Be professional and concise.
Return JSON only."""

    content = _call_gemini(prompt, model=model, json_mode=True)
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "name": "User",
            "summary": f"Professional interested in {field} for {purpose}",
            "education": [],
            "experiences": [],
            "skills": [field],
            "projects": []
        }


def _build_sender_context(sender_profile: dict | None) -> str:
    if not sender_profile:
        return ""

    def _join_list(key: str, *, limit: int) -> str:
        value = sender_profile.get(key) or []
        if not isinstance(value, list):
            return ""
        cleaned = [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]
        return ", ".join(cleaned[:limit])

    raw_text = str(sender_profile.get("raw_text") or "").strip()
    if raw_text:
        raw_text = " ".join(raw_text.split())
        if len(raw_text) > 400:
            raw_text = raw_text[:400].rstrip() + "..."

    lines = [
        "Sender background:",
        f"- Education: {_join_list('education', limit=3) or 'Not specified'}",
        f"- Experience: {_join_list('experiences', limit=3) or 'Not specified'}",
        f"- Skills: {_join_list('skills', limit=6) or 'Not specified'}",
        f"- Projects: {_join_list('projects', limit=3) or 'Not specified'}",
    ]
    if raw_text:
        lines.append(f"- Summary: {raw_text}")

    return "\n".join(lines) + "\n"


def _build_preference_context(preferences: dict | None) -> str:
    if not preferences:
        return ""

    def _format_block(label: str, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return ""
        if "\n" not in cleaned:
            return f"- {label}: {cleaned}"
        indented = "\n".join(f"  {line.strip()}" for line in cleaned.splitlines() if line.strip())
        return f"- {label}:\n{indented}"

    contactability_map = {
        "balanced": "balanced (relevance and reply likelihood)",
        "reply": "prioritize likely to reply (more accessible)",
        "prestige": "prioritize most senior/famous (prestige)",
    }

    pref_blocks: list[str] = []

    track = preferences.get("track")
    if isinstance(track, str) and track.strip():
        pref_blocks.append(_format_block("Track", track))

    search_intent = preferences.get("search_intent")
    if isinstance(search_intent, str) and search_intent.strip():
        pref_blocks.append(_format_block("Ideal target description", search_intent))

    must_have = preferences.get("must_have")
    if isinstance(must_have, str) and must_have.strip():
        pref_blocks.append(_format_block("Must have keywords", must_have))

    must_not = preferences.get("must_not")
    if isinstance(must_not, str) and must_not.strip():
        pref_blocks.append(_format_block("Must not keywords", must_not))

    location = preferences.get("location")
    if isinstance(location, str) and location.strip():
        pref_blocks.append(_format_block("Location language timezone", location))

    contactability = preferences.get("contactability")
    if isinstance(contactability, str) and contactability.strip():
        normalized = contactability_map.get(contactability.strip().lower(), contactability.strip())
        pref_blocks.append(_format_block("Reply vs prestige preference", normalized))

    examples = preferences.get("examples")
    if isinstance(examples, str) and examples.strip():
        pref_blocks.append(_format_block("Examples of ideal targets", examples))

    evidence = preferences.get("evidence")
    if isinstance(evidence, str) and evidence.strip():
        pref_blocks.append(_format_block("Evidence links or snippets", evidence))

    pref_map = {
        "seniority": "Seniority target",
        "org_type": "Organization type",
        "outreach_goal": "Outreach goal",
        "prominence": "Desired prominence",
        "extra": "Additional targeting notes",
    }
    for key, label in pref_map.items():
        value = preferences.get(key)
        if isinstance(value, str) and value.strip():
            pref_blocks.append(_format_block(label, value))

    pref_blocks = [block for block in pref_blocks if block]
    if not pref_blocks:
        return ""
    return "Targeting preferences:\n" + "\n".join(pref_blocks) + "\n"


def _build_recommendation_prompt(
    *,
    purpose: str,
    field: str,
    profile_context: str,
    pref_context: str,
    count: int,
    web_text: str = "",
    sources: list[str] | None = None,
    include_web_section: bool = True,
    require_tool_use: bool = False,
) -> str:
    source_block = ""
    if include_web_section and web_text:
        source_block = f"\nUse the following web research snippets to ground your recommendations (cite sources when relevant):\n{web_text}"
    if include_web_section and sources:
        sources_list = "\n".join(f"- {s}" for s in sources)
        source_block = f"{source_block}\nKnown source URLs:\n{sources_list}"

    tool_hint = ""
    if require_tool_use:
        tool_hint = (
            "\nYou have access to a web_search tool. "
            "Search the web to find real, recent people that fit the criteria. "
            "Do not rely only on prior knowledge; prefer names that appear in search results."
        )

    return f"""You are a networking advisor helping someone find the best people to reach out to.

Purpose: {purpose}
Field: {field}
{profile_context}
{pref_context}{source_block}{tool_hint}

Return a JSON object with key "recommendations" containing a list of {count} people. Each item must have:
- name (string)
- position (string)
- field (string)
- linkedin_url (string, the person's LinkedIn profile URL if found, e.g., "https://www.linkedin.com/in/username")
- match_score (integer 60-95)
- match_reason (short string)
- common_interests (short string)
- evidence (list of 1-3 short strings; each should include a source URL and a grounded fact/snippet)
- sources (list of URLs; can be empty only if you explicitly set uncertainty to high)
- uncertainty (string: low, medium, or high, plus a short reason if needed)

IMPORTANT: Prioritize finding LinkedIn profiles. Search "[name] [company] LinkedIn" to find their LinkedIn URL.
Return up to {count} people. Prefer candidates you can verify with evidence and have LinkedIn profiles.
If you cannot find at least one credible source URL for a person, either omit them or mark uncertainty as high and keep claims minimal.
Rank candidates by: fit to purpose/field/preferences, likely contactability (if specified), and strength of evidence.
Be diverse and mix accessible profiles, not only famous leaders.
Return JSON only."""


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _generate_linkedin_search_url(name: str, company: str = "") -> str:
    """
    Generate a LinkedIn search URL for a person.
    This is more reliable than trying to guess their profile URL.
    
    Args:
        name: Person's full name
        company: Optional company name for better search results
        
    Returns:
        LinkedIn search URL
    """
    import urllib.parse
    search_query = name
    if company:
        search_query = f"{name} {company}"
    encoded_query = urllib.parse.quote(search_query)
    return f"https://www.linkedin.com/search/results/people/?keywords={encoded_query}"


def _lookup_linkedin_via_serpapi(name: str, company: str = "", additional_context: str = "") -> str | None:
    """
    Use SerpAPI to search Google for a person's LinkedIn profile URL.
    
    This provides more accurate LinkedIn URLs by searching Google with site:linkedin.com/in/
    and returning the actual profile URL from the search results.
    
    Args:
        name: Person's full name
        company: Optional company name for better search accuracy
        additional_context: Optional additional context (title, field, etc.)
        
    Returns:
        LinkedIn profile URL if found, None otherwise
        
    Requires:
        SERPAPI_KEY environment variable to be set
    """
    import urllib.request
    import urllib.parse
    
    api_key = os.environ.get("SERPAPI_KEY") or os.environ.get("SERP_API_KEY")
    if not api_key:
        return None
    
    # Build search query
    query_parts = [f'site:linkedin.com/in/', f'"{name}"']
    if company:
        query_parts.append(f'"{company}"')
    if additional_context:
        query_parts.append(additional_context)
    
    query = " ".join(query_parts)
    
    params = urllib.parse.urlencode({
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 3,  # Only need top few results
    })
    
    url = f"https://serpapi.com/search.json?{params}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        if "organic_results" not in data or not data["organic_results"]:
            print(f"[SerpAPI] No results found for: {name}")
            return None
        
        # Look through results for a valid LinkedIn profile URL
        for result in data["organic_results"]:
            link = result.get("link", "")
            if not link:
                continue
            
            # Verify it's a LinkedIn personal profile URL
            if "/in/" in link and ("linkedin.com/in/" in link.lower()):
                # Clean up the URL (remove tracking params)
                clean_url = link.split("?")[0].rstrip("/")
                
                # Validate format
                if _validate_linkedin_url(clean_url):
                    # CRITICAL: Verify the name appears in the result title
                    # This prevents returning URLs for completely different people
                    title = result.get("title", "").lower()
                    name_parts = name.lower().split()
                    
                    # Check if at least first name OR last name appears in the title
                    # (for names with 2+ parts, at least one meaningful part should match)
                    matching_parts = [part for part in name_parts if len(part) > 2 and part in title]
                    
                    if matching_parts:
                        print(f"[SerpAPI] Found LinkedIn URL for {name}: {clean_url} (matched: {matching_parts})")
                        return clean_url
                    else:
                        # Name doesn't match - skip this result
                        print(f"[SerpAPI] Skipping {clean_url} - name '{name}' not found in title: '{title[:50]}'")
                        continue
        
        print(f"[SerpAPI] No matching LinkedIn profile found for: {name}")
        return None
        
    except urllib.error.URLError as e:
        print(f"[SerpAPI] Network error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[SerpAPI] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"[SerpAPI] Unexpected error: {e}")
        return None


def _build_serpapi_search_query(
    preferences: dict | None = None,
    field: str = "",
    purpose: str = "",
) -> str:
    """
    将用户的 preferences 转化为 SerpAPI LinkedIn 搜索词
    
    Args:
        preferences: 用户偏好设置
        field: 领域
        purpose: 目的
        
    Returns:
        构建好的搜索词
    """
    parts = ['site:linkedin.com/in/']
    prefs = preferences or {}
    
    # 1. 职位/级别关键词
    seniority = str(prefs.get("seniority", "") or "").strip()
    target_titles = prefs.get("target_role_titles", [])
    
    if target_titles and isinstance(target_titles, list):
        # ["Analyst", "Associate"] → ("Analyst" OR "Associate")
        titles = [t.strip() for t in target_titles if t.strip()]
        if len(titles) > 1:
            parts.append("(" + " OR ".join(f'"{t}"' for t in titles[:3]) + ")")
        elif titles:
            parts.append(f'"{titles[0]}"')
    elif seniority:
        parts.append(f'"{seniority}"')
    
    # 2. 公司/机构关键词
    must_have = str(prefs.get("must_have", "") or "").strip()
    org_type = str(prefs.get("org_type", "") or "").strip()
    
    if must_have:
        # "Goldman Sachs, Morgan Stanley, M&A" → 提取公司名
        keywords = [k.strip() for k in must_have.split(",") if k.strip()]
        # 识别公司名（通常首字母大写且多个单词）
        companies = [k for k in keywords if len(k.split()) >= 2 or k[0].isupper()]
        if companies:
            if len(companies) > 1:
                parts.append("(" + " OR ".join(f'"{c}"' for c in companies[:3]) + ")")
            else:
                parts.append(f'"{companies[0]}"')
    elif org_type:
        # "Investment Bank" → 搜索投行相关
        parts.append(f'"{org_type}"')
    
    # 3. 领域/方向关键词
    search_intent = str(prefs.get("search_intent", "") or "").strip()
    group = str(prefs.get("group", "") or "").strip()  # e.g., "M&A", "TMT"
    sector = str(prefs.get("sector", "") or "").strip()
    
    if group:
        parts.append(f'"{group}"')
    elif sector:
        parts.append(f'"{sector}"')
    elif search_intent:
        # 从 search_intent 提取关键词（简单实现）
        # 例如 "找投行 M&A 方向的 Associate" → 提取 M&A
        for keyword in ["M&A", "PE", "VC", "IB", "AM", "HF", "TMT", "Healthcare", "FIG", "Tech"]:
            if keyword.lower() in search_intent.lower():
                parts.append(f'"{keyword}"')
                break
    
    # 如果没有从 preferences 提取到足够信息，使用 field
    if len(parts) <= 2 and field:
        parts.append(f'"{field}"')
    
    # 4. 地区
    location = str(prefs.get("location", "") or "").strip()
    if location:
        # 只取主要城市/地区
        loc_parts = location.split(",")
        if loc_parts:
            parts.append(f'"{loc_parts[0].strip()}"')
    
    # 5. 排除词
    must_not = str(prefs.get("must_not", "") or "").strip()
    if must_not:
        excludes = [e.strip() for e in must_not.split(",") if e.strip()]
        for ex in excludes[:2]:  # 最多排除2个词
            parts.append(f'-"{ex}"')
    
    return " ".join(parts)


def _search_linkedin_via_serpapi(
    preferences: dict | None = None,
    field: str = "",
    purpose: str = "",
    count: int = 10,
) -> list[dict[str, Any]]:
    """
    直接使用 SerpAPI 搜索 LinkedIn 找到符合条件的真实的人
    
    不依赖 AI 生成名字，而是从 Google 搜索结果中提取真实存在的 LinkedIn 用户
    
    Args:
        preferences: 用户偏好设置
        field: 领域
        purpose: 目的
        count: 需要返回的人数
        
    Returns:
        包含真实 LinkedIn 用户信息的列表
    """
    import urllib.request
    import urllib.parse
    
    api_key = os.environ.get("SERPAPI_KEY") or os.environ.get("SERP_API_KEY")
    if not api_key:
        print("[SerpAPI Search] No API key configured")
        return []
    
    # 构建搜索词
    query = _build_serpapi_search_query(preferences, field, purpose)
    print(f"[SerpAPI Search] Query: {query}")
    
    params = urllib.parse.urlencode({
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": min(count * 2, 20),  # 搜索多一些，因为可能有些结果不是个人主页
    })
    
    url = f"https://serpapi.com/search.json?{params}"
    
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode())
        
        if "organic_results" not in data or not data["organic_results"]:
            print(f"[SerpAPI Search] No results found")
            return []
        
        results = []
        for result in data["organic_results"]:
            link = result.get("link", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            
            # 验证是 LinkedIn 个人主页
            if not link or "/in/" not in link or "linkedin.com/in/" not in link.lower():
                continue
            
            # 清理 URL
            clean_url = link.split("?")[0].rstrip("/")
            if not _validate_linkedin_url(clean_url):
                continue
            
            # 从标题中提取姓名和职位
            # LinkedIn 标题格式通常是: "Name - Title at Company | LinkedIn"
            # 或: "Name - Title - Company | LinkedIn"
            name, position = _parse_linkedin_title(title)
            
            if not name:
                continue
            
            # 从 snippet 中提取更多信息
            evidence = []
            if snippet:
                evidence.append(snippet[:200])
            
            results.append({
                "name": name,
                "position": position,
                "field": field,
                "linkedin_url": clean_url,
                "match_score": 75,  # 默认分数，后续可以用 AI 评分
                "match_reason": f"Found via LinkedIn search for {field}",
                "common_interests": "",
                "evidence": evidence,
                "sources": [clean_url],
                "uncertainty": "low",  # 真实存在的人
            })
            
            if len(results) >= count:
                break
        
        print(f"[SerpAPI Search] Found {len(results)} real LinkedIn profiles")
        return results
        
    except urllib.error.URLError as e:
        print(f"[SerpAPI Search] Network error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"[SerpAPI Search] JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"[SerpAPI Search] Unexpected error: {e}")
        return []


def _parse_linkedin_title(title: str) -> tuple[str, str]:
    """
    从 LinkedIn 搜索结果标题中提取姓名和职位
    
    常见格式:
    - "John Smith - VP at Goldman Sachs | LinkedIn"
    - "Jane Doe - Associate - Morgan Stanley | LinkedIn"
    - "Mike Chen, CFA - Portfolio Manager | LinkedIn"
    
    Args:
        title: LinkedIn 搜索结果标题
        
    Returns:
        (name, position) 元组
    """
    if not title:
        return "", ""
    
    # 移除 " | LinkedIn" 或 "- LinkedIn" 后缀
    title = title.replace(" | LinkedIn", "").replace("- LinkedIn", "").strip()
    
    # 尝试按 " - " 分割
    if " - " in title:
        parts = title.split(" - ", 1)
        name = parts[0].strip()
        position = parts[1].strip() if len(parts) > 1 else ""
        
        # 处理 "Name, CFA" 或 "Name, MBA" 格式
        if "," in name:
            name_parts = name.split(",")
            name = name_parts[0].strip()
        
        return name, position
    
    # 尝试按 " at " 分割（某些格式）
    if " at " in title.lower():
        idx = title.lower().find(" at ")
        return title[:idx].strip(), title[idx:].strip()
    
    # 无法解析，返回整个标题作为名字
    return title.strip(), ""


def _ai_score_and_analyze_candidates(
    candidates: list[dict[str, Any]],
    sender_profile: dict | None = None,
    preferences: dict | None = None,
    purpose: str = "",
    field: str = "",
    model: str = DEFAULT_MODEL,
) -> list[dict[str, Any]]:
    """
    使用 AI 对候选人进行评分、排序和匹配度分析
    
    Args:
        candidates: SerpAPI 搜索到的候选人列表
        sender_profile: 发送者画像
        preferences: 用户偏好
        purpose: 目的
        field: 领域
        model: 使用的模型
        
    Returns:
        包含 AI 评分和分析的候选人列表
    """
    if not candidates:
        return candidates
    
    # 构建发送者信息
    sender_info = ""
    if sender_profile:
        sender_name = sender_profile.get("name", "")
        sender_edu = sender_profile.get("education", [])
        sender_exp = sender_profile.get("experiences", [])
        sender_skills = sender_profile.get("skills", [])
        
        sender_parts = []
        if sender_name:
            sender_parts.append(f"Name: {sender_name}")
        if sender_edu:
            sender_parts.append(f"Education: {', '.join(sender_edu[:3])}")
        if sender_exp:
            sender_parts.append(f"Experience: {', '.join(sender_exp[:3])}")
        if sender_skills:
            sender_parts.append(f"Skills: {', '.join(sender_skills[:5])}")
        
        if sender_parts:
            sender_info = "\n".join(sender_parts)
    
    # 构建偏好信息
    pref_info = ""
    if preferences:
        pref_parts = []
        if preferences.get("search_intent"):
            pref_parts.append(f"Looking for: {preferences['search_intent']}")
        if preferences.get("seniority"):
            pref_parts.append(f"Seniority: {preferences['seniority']}")
        if preferences.get("org_type"):
            pref_parts.append(f"Organization type: {preferences['org_type']}")
        if preferences.get("must_have"):
            pref_parts.append(f"Must have: {preferences['must_have']}")
        if preferences.get("must_not"):
            pref_parts.append(f"Must not: {preferences['must_not']}")
        if preferences.get("location"):
            pref_parts.append(f"Location: {preferences['location']}")
        
        if pref_parts:
            pref_info = "\n".join(pref_parts)
    
    # 构建候选人列表
    candidates_text = ""
    for i, c in enumerate(candidates, 1):
        candidates_text += f"""
{i}. {c.get('name', 'Unknown')}
   Position: {c.get('position', 'N/A')}
   LinkedIn: {c.get('linkedin_url', 'N/A')}
   Evidence: {'; '.join(c.get('evidence', [])[:2]) if c.get('evidence') else 'N/A'}
"""
    
    # 构建 AI 评分 prompt
    prompt = f"""You are a networking advisor. Analyze and score these LinkedIn candidates for a cold outreach.

PURPOSE: {purpose}
FIELD: {field}

SENDER PROFILE:
{sender_info if sender_info else "Not provided"}

PREFERENCES:
{pref_info if pref_info else "Not provided"}

CANDIDATES:
{candidates_text}

For each candidate, provide:
1. match_score (60-95): How well they match the sender's goals and preferences
2. match_reason (1-2 sentences): Why they are a good/poor match
3. common_interests (1 sentence): Potential common ground or talking points
4. outreach_angle (1 sentence): Suggested angle for cold email
5. response_likelihood (low/medium/high): How likely they are to respond

Return a JSON object with key "scored_candidates" containing a list in the same order as input.
Each item should have: name, match_score, match_reason, common_interests, outreach_angle, response_likelihood.

Focus on:
- Seniority alignment (not too senior, not too junior)
- Industry/sector relevance
- Potential shared background (education, previous companies)
- Accessibility (people who are active and might respond)

Return JSON only."""

    try:
        content = _call_gemini(prompt, model=model, json_mode=True)
        result = json.loads(content)
        scored_list = result.get("scored_candidates", [])
        
        # 合并 AI 分析结果到原始候选人
        for i, candidate in enumerate(candidates):
            if i < len(scored_list):
                scored = scored_list[i]
                candidate["match_score"] = scored.get("match_score", 75)
                candidate["match_reason"] = scored.get("match_reason", "")
                candidate["common_interests"] = scored.get("common_interests", "")
                candidate["outreach_angle"] = scored.get("outreach_angle", "")
                candidate["response_likelihood"] = scored.get("response_likelihood", "medium")
        
        # 按分数排序
        candidates.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        print(f"[AI Scoring] Successfully scored {len(candidates)} candidates")
        return candidates
        
    except Exception as e:
        print(f"[AI Scoring] Error: {e}")
        # 返回原始列表，使用默认分数
        return candidates


def _normalize_recommendations(items: Any, grounding_urls: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Normalize recommendation items into a consistent format.
    
    Args:
        items: List of raw recommendation items
        grounding_urls: Optional list of URLs from Gemini grounding (not used anymore)
        
    Returns:
        List of normalized recommendation dictionaries
    """
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "") or "").strip()
        if not name:
            continue

        position = str(item.get("position", "") or "").strip()
        field = str(item.get("field", "") or "").strip()
        match_reason = str(item.get("match_reason", "") or "").strip()
        common_interests = str(item.get("common_interests", "") or "").strip()
        uncertainty = str(item.get("uncertainty", "") or "").strip() or "medium"

        match_score = _safe_int(item.get("match_score", 0), default=0)
        match_score = max(0, min(match_score, 100))

        sources_value = item.get("sources", [])
        sources: list[str] = []
        if isinstance(sources_value, list):
            sources = [str(s).strip() for s in sources_value if isinstance(s, str) and s.strip()]
        elif isinstance(sources_value, str) and sources_value.strip():
            sources = [sources_value.strip()]

        evidence_value = item.get("evidence", [])
        evidence: list[str] = []
        if isinstance(evidence_value, list):
            evidence = [str(e).strip() for e in evidence_value if isinstance(e, str) and str(e).strip()]
        elif isinstance(evidence_value, str) and evidence_value.strip():
            evidence = [evidence_value.strip()]

        # Check if model provided a LinkedIn URL (we'll validate it)
        linkedin_url_raw = str(item.get("linkedin_url", "") or "").strip()
        
        # Also check sources for LinkedIn URLs
        if not linkedin_url_raw:
            for src in sources:
                if "linkedin.com/in/" in src.lower():
                    linkedin_url_raw = src
                    break
        
        # Validate the LinkedIn URL format
        linkedin_url = _validate_linkedin_url(linkedin_url_raw)
        
        # Extract company from position if available (used for SerpAPI and fallback)
        company = ""
        if position:
            # Try to extract company name from position (e.g., "VP at Goldman Sachs")
            for keyword in ["at ", "@ ", ", "]:
                if keyword in position:
                    company = position.split(keyword)[-1].strip()
                    break
        
        # If no valid LinkedIn URL from model, try SerpAPI to find the real profile URL
        if not linkedin_url:
            # Try SerpAPI lookup (returns None if SERPAPI_KEY not set or search fails)
            serpapi_url = _lookup_linkedin_via_serpapi(name, company, field)
            if serpapi_url:
                linkedin_url = serpapi_url
        
        # If still no valid LinkedIn URL, fall back to search URL
        if not linkedin_url:
            linkedin_url = _generate_linkedin_search_url(name, company)

        normalized.append(
            {
                "name": name,
                "position": position or field,
                "field": field or position,
                "linkedin_url": linkedin_url,  # Either validated profile URL or search URL
                "match_score": match_score or 70,
                "match_reason": match_reason,
                "common_interests": common_interests,
                "evidence": evidence,
                "sources": sources,
                "uncertainty": uncertainty,
            }
        )

    return normalized


def _gather_recommendation_web_context(
    field: str,
    purpose: str,
    preferences: dict | None,
    max_pages: int = 3,
) -> tuple[str, list[str]]:
    """
    Light web scrape to ground recommendations; uses DuckDuckGo/Bing HTML paths via WebScraper.
    """
    try:
        from .web_scraper import WebScraper
    except ImportError:
        from web_scraper import WebScraper  # type: ignore

    scraper = WebScraper()
    preferences = preferences or {}

    search_intent = str(preferences.get("search_intent") or "").strip()
    must_have = str(preferences.get("must_have") or "").strip()
    location = str(preferences.get("location") or "").strip()
    seniority = str(preferences.get("seniority") or "").strip()
    org_type = str(preferences.get("org_type") or "").strip()
    track = str(preferences.get("track") or "").strip()

    query_name = search_intent or field or purpose or "targets"
    query_field_parts = [purpose, field, track, must_have, location, seniority, org_type]
    query_field = " ".join(part.strip() for part in query_field_parts if isinstance(part, str) and part.strip())

    search_results = scraper.search_person(query_name, query_field, max_results=max_pages + 2)
    if not search_results:
        return "", []

    all_text: list[str] = []
    sources: list[str] = []

    snippet_text = "\n".join(
        f"- {r.title}: {r.snippet}"
        for r in search_results
        if r.snippet
    )
    if snippet_text:
        all_text.append(f"Search snippets:\n{snippet_text}")

    pages_fetched = 0
    for result in search_results:
        if pages_fetched >= max_pages:
            break
        content = scraper.fetch_page_content(result.url)
        if content and len(content) > 200:
            all_text.append(f"--- Source: {result.url} ---\n{content[:4000]}")
            sources.append(result.url)
            pages_fetched += 1

    combined_text = "\n\n".join(all_text)
    return combined_text, sources


def find_target_recommendations(
    purpose: str,
    field: str,
    sender_profile: dict | None = None,
    preferences: dict | None = None,
    *,
    model: str = DEFAULT_MODEL,
    count: int = 10,
    session_id: str | None = None,  # 用于数据收集
) -> list[dict]:
    """
    Find recommended target contacts based on user's purpose, field, and profile.
    
    Args:
        purpose: The user's purpose (academic, job seeking, coffee chat)
        field: The field of interest
        sender_profile: Optional sender profile for better matching
        model: Gemini model to use
        count: Number of recommendations to generate
        preferences: Optional targeting preferences (seniority, org type, outreach goal, prominence)
        session_id: Optional session ID for prompt data collection
        
    Returns:
        List of recommendation dictionaries
    """
    pref_context = _build_preference_context(preferences)
    profile_context = _build_sender_context(sender_profile)
    
    # 用于数据收集的变量
    collected_prompt = ""
    collected_output = ""

    # ============================================================
    # PRIMARY: SerpAPI 直接搜索 LinkedIn 找真实的人
    # 不依赖 AI 生成名字，直接从搜索结果中提取真实存在的用户
    # ============================================================
    serpapi_key = os.environ.get("SERPAPI_KEY") or os.environ.get("SERP_API_KEY")
    if serpapi_key:
        try:
            print("[SerpAPI Search] Using SerpAPI to find real LinkedIn profiles...")
            serpapi_results = _search_linkedin_via_serpapi(
                preferences=preferences,
                field=field,
                purpose=purpose,
                count=count,
            )
            
            if serpapi_results and len(serpapi_results) >= 3:
                # 成功找到足够的真实用户
                print(f"[SerpAPI Search] Successfully found {len(serpapi_results)} real profiles")
                
                # 使用 AI 进行评分和匹配度分析
                print("[AI Scoring] Analyzing candidates with AI...")
                scored_results = _ai_score_and_analyze_candidates(
                    candidates=serpapi_results,
                    sender_profile=sender_profile,
                    preferences=preferences,
                    purpose=purpose,
                    field=field,
                    model=model,
                )
                
                # 保存收集的数据
                if PROMPT_COLLECTOR_AVAILABLE and prompt_collector and session_id:
                    search_query = _build_serpapi_search_query(preferences, field, purpose)
                    prompt_collector.record_find_target(
                        session_id=session_id,
                        prompt=f"SerpAPI Search: {search_query}",
                        output=json.dumps(scored_results, ensure_ascii=False),
                        metadata={"method": "serpapi_direct_with_ai_scoring", "count": len(scored_results)}
                    )
                
                return scored_results[:count]
            else:
                print(f"[SerpAPI Search] Only found {len(serpapi_results) if serpapi_results else 0} results, falling back to Gemini")
        except Exception as e:
            print(f"[SerpAPI Search] Error: {e}, falling back to Gemini")

    # ============================================================
    # FALLBACK: Gemini with Google Search grounding
    # 当 SerpAPI 不可用或结果不足时使用
    # ============================================================
    if USE_GEMINI_SEARCH:
        try:
            prompt = _build_recommendation_prompt(
                purpose=purpose,
                field=field,
                profile_context=profile_context,
                pref_context=pref_context,
                count=count,
                web_text="",
                sources=[],
                include_web_section=False,
            )
            # Add instruction for real-time search - DO NOT ask for LinkedIn URLs
            # because the model will fabricate them instead of finding real ones
            search_prompt = (
                f"{prompt}\n\n"
                "CRITICAL SEARCH INSTRUCTIONS:\n"
                "1. Use Google Search to find REAL professionals currently working in this field.\n"
                "2. Search for each person to verify they actually exist and work at the company.\n"
                "3. DO NOT include linkedin_url - leave it as empty string. Users will search LinkedIn themselves.\n"
                "4. Include the sources field with actual news/company/article URLs where you found information.\n"
                "5. Focus on finding people with verifiable public information (news articles, company pages, etc.).\n"
                "6. For Finance/Banking, search for professionals at major institutions like Goldman Sachs, Morgan Stanley, JPMorgan, BlackRock, etc.\n"
                "\n"
                "IMPORTANT: Only include people you can verify exist. Each person MUST have evidence from search results.\n"
                "DO NOT make up or guess LinkedIn profile URLs - the linkedin_url field should always be empty string."
            )
            # Get response with grounding URLs for logging
            result = _call_gemini_with_search(search_prompt, model=GEMINI_SEARCH_MODEL, json_mode=True, return_grounding_urls=True)
            content, grounding_urls = result
            
            print(f"[Search] Retrieved {len(grounding_urls)} grounding source URLs")
            
            # 收集数据
            collected_prompt = search_prompt
            collected_output = content
            
            raw_items = json.loads(content).get("recommendations", [])
            # Normalize and generate LinkedIn search URLs (not profile URLs)
            recommendations = _normalize_recommendations(raw_items, grounding_urls=grounding_urls)
            recommendations.sort(key=lambda x: _safe_int(x.get("match_score", 0), default=0), reverse=True)
            if recommendations:
                print(f"Gemini Search found {len(recommendations)} recommendations")
                # 保存收集的数据
                if PROMPT_COLLECTOR_AVAILABLE and prompt_collector and session_id:
                    prompt_collector.record_find_target(
                        session_id=session_id,
                        prompt=collected_prompt,
                        output=collected_output,
                        metadata={"model": GEMINI_SEARCH_MODEL, "method": "gemini_search", "count": len(recommendations)}
                    )
                return recommendations[:count]
        except Exception as e:
            print(f"Gemini Search recommendation error: {e}")

    # Fallback 1: OpenAI (gpt-5.1) with built-in web_search tool - DISABLED by default
    if USE_OPENAI_WEB_SEARCH and USE_OPENAI_RECOMMENDATIONS:
        try:
            fallback_prompt = _build_recommendation_prompt(
                purpose=purpose,
                field=field,
                profile_context=profile_context,
                pref_context=pref_context,
                count=count,
                include_web_section=False,
                require_tool_use=True,
            )
            content = _call_openai_json_with_web_search(fallback_prompt, model=RECOMMENDATION_MODEL)
            
            # 收集数据
            collected_prompt = fallback_prompt
            collected_output = content
            
            raw_items = json.loads(content).get("recommendations", [])
            recommendations = _normalize_recommendations(raw_items)
            recommendations.sort(key=lambda x: _safe_int(x.get("match_score", 0), default=0), reverse=True)
            if recommendations:
                # 保存收集的数据
                if PROMPT_COLLECTOR_AVAILABLE and prompt_collector and session_id:
                    prompt_collector.record_find_target(
                        session_id=session_id,
                        prompt=collected_prompt,
                        output=collected_output,
                        metadata={"model": RECOMMENDATION_MODEL, "method": "openai_web_search", "count": len(recommendations)}
                    )
                return recommendations[:count]
        except Exception as e:
            print(f"OpenAI recommendation (web_search) error: {e}")

    # Fallback 1: our own web scrape + OpenAI - DISABLED by default
    if USE_OPENAI_RECOMMENDATIONS:
        try:
            web_text, web_sources = _gather_recommendation_web_context(field, purpose, preferences, max_pages=3)
            content = _call_openai_json(
                _build_recommendation_prompt(
                    purpose=purpose,
                    field=field,
                    profile_context=profile_context,
                    pref_context=pref_context,
                    count=count,
                    web_text=web_text,
                    sources=web_sources,
                    include_web_section=True,
                    require_tool_use=False,
                ),
                model=RECOMMENDATION_MODEL,
            )
            raw_items = json.loads(content).get("recommendations", [])
            recommendations = _normalize_recommendations(raw_items)
            recommendations.sort(key=lambda x: _safe_int(x.get("match_score", 0), default=0), reverse=True)
            if recommendations:
                return recommendations[:count]
        except Exception as e:
            print(f"OpenAI recommendation (scrape fallback) error: {e}")

    # Fallback 2: lightweight web scrape + Gemini (keeps evidence grounded even without Gemini Search)
    try:
        web_text, web_sources = _gather_recommendation_web_context(field, purpose, preferences, max_pages=1)
        if web_text or web_sources:
            fallback_prompt = _build_recommendation_prompt(
                purpose=purpose,
                field=field,
                profile_context=profile_context,
                pref_context=pref_context,
                count=count,
                web_text=web_text,
                sources=web_sources,
                include_web_section=True,
                require_tool_use=False,
            )
            content = _call_gemini(
                fallback_prompt,
                model=model,
                json_mode=True,
            )
            raw_items = json.loads(content).get("recommendations", [])
            recommendations = _normalize_recommendations(raw_items)
            recommendations.sort(key=lambda x: _safe_int(x.get("match_score", 0), default=0), reverse=True)
            if recommendations:
                # 保存收集的数据（scrape + Gemini fallback）
                if PROMPT_COLLECTOR_AVAILABLE and prompt_collector and session_id:
                    prompt_collector.record_find_target(
                        session_id=session_id,
                        prompt=fallback_prompt,
                        output=content,
                        metadata={"model": model, "method": "gemini_scrape_fallback", "count": len(recommendations)}
                    )
                return recommendations[:count]
    except Exception as e:
        print(f"Gemini recommendation (scrape fallback) error: {e}")

    # Default: Gemini text-only generation (fast and reliable)
    prompt = _build_recommendation_prompt(
        purpose=purpose,
        field=field,
        profile_context=profile_context,
        pref_context=pref_context,
        count=count,
        web_text="",
        sources=[],
        include_web_section=False,
    )
    content = _call_gemini(prompt, model=model, json_mode=True)
    
    try:
        raw_items = json.loads(content).get("recommendations", [])
        recommendations = _normalize_recommendations(raw_items)
        recommendations.sort(key=lambda x: _safe_int(x.get("match_score", 0), default=0), reverse=True)
        if recommendations:
            # 保存收集的数据（default fallback）
            if PROMPT_COLLECTOR_AVAILABLE and prompt_collector and session_id:
                prompt_collector.record_find_target(
                    session_id=session_id,
                    prompt=prompt,
                    output=content,
                    metadata={"model": model, "method": "gemini_text_only", "count": len(recommendations)}
                )
            return recommendations[:count]
    except json.JSONDecodeError:
        pass

    # Final fallback
    return [
        {
            "name": "Contact in " + field,
            "position": "Professional",
            "field": field,
            "match_score": 70,
            "match_reason": "Relevant to your field",
            "common_interests": "Shared interest in " + field,
            "evidence": [],
            "sources": [],
            "uncertainty": "high: no sources available",
        }
    ]


def parse_text_to_profile(
    text_content: str,
    name: str = "",
    field: str = "",
    *,
    model: str = DEFAULT_MODEL
) -> dict:
    """
    Parse text content (from uploaded TXT/MD file) into a profile structure.
    
    Args:
        text_content: The text content to parse
        name: Optional name (if not in text)
        field: Optional field information
        model: Gemini model to use
        
    Returns:
        Dictionary with profile information
    """
    prompt = f"""Extract a structured profile from the following text content about a person.

Text content:
{text_content[:5000]}

Additional context:
- Name (if not found in text): {name or 'Unknown'}
- Field: {field or 'Not specified'}

Return a JSON object with this structure:
{{
    "name": "Person's name from text or the provided name",
    "field": "Their field/domain",
    "raw_text": "Brief summary of the text content",
    "education": ["list of educational background"],
    "experiences": ["list of work/research experience"],
    "skills": ["list of skills and expertise"],
    "projects": ["list of notable projects or publications"],
    "sources": ["Uploaded document"]
}}

Extract as much relevant information as possible. Return JSON only."""

    content = _call_gemini(prompt, model=model, json_mode=True)
    
    try:
        profile = json.loads(content)
        # Ensure required fields
        profile.setdefault('name', name or 'Unknown')
        profile.setdefault('field', field)
        profile.setdefault('raw_text', text_content[:500])
        profile.setdefault('education', [])
        profile.setdefault('experiences', [])
        profile.setdefault('skills', [])
        profile.setdefault('projects', [])
        profile.setdefault('sources', ['Uploaded document'])
        return profile
    except json.JSONDecodeError:
        return {
            "name": name or "Unknown",
            "field": field,
            "raw_text": text_content[:500],
            "education": [],
            "experiences": [],
            "skills": [],
            "projects": [],
            "sources": ["Uploaded document"]
        }


def regenerate_email_with_style(
    original_email: str,
    style_instruction: str,
    sender_info: dict | None = None,
    receiver_info: dict | None = None,
    *,
    model: str = DEFAULT_MODEL
) -> str:
    """
    Regenerate an email with a different style/tone.
    
    Args:
        original_email: The original generated email
        style_instruction: How to modify the style (e.g., "more professional", "more friendly")
        sender_info: Optional sender information for context
        receiver_info: Optional receiver information for context
        model: Gemini model to use
        
    Returns:
        The regenerated email with the new style
    """
    context = ""
    if sender_info:
        context += f"\nSender: {sender_info.get('name', 'Unknown')}"
    if receiver_info:
        context += f"\nReceiver: {receiver_info.get('name', 'Unknown')}"
    
    prompt = f"""You are an expert email writer. Rewrite the following cold email according to the style instruction.

Original email:
{original_email}

Style instruction: {style_instruction}
{context}

Rewrite the email to match the requested style while:
- Keeping the core message and purpose
- Maintaining professionalism
- Keeping it appropriate for a cold email

Return only the rewritten email with Subject line and body. No explanations."""

    content = _call_gemini(prompt, model=model)
    return content.strip()
