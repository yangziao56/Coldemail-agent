from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import google.generativeai as genai
from PyPDF2 import PdfReader

# Default model for Gemini
DEFAULT_MODEL = "gemini-2.0-flash"


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


def build_prompt(sender: SenderProfile, receiver: ReceiverProfile, goal: str) -> list[dict[str, str]]:
    goal_text = goal.strip()
    if not goal_text:
        raise ValueError("Goal must be a non-empty string")

    def _format_section(title: str, items: list[str]) -> str:
        if not items:
            return f"- {title}: (not specified)\n"
        bullet_points = "\n".join(f"  • {item}" for item in items)
        return f"- {title}:\n{bullet_points}\n"

    system_message = {
        "role": "system",
        "content": (
            "You craft sincere, concise first-contact cold emails that help two people build a genuine connection. "
            "Use the provided sender and receiver details to highlight authentic overlaps and mutual value. "
            "Output a complete email with a Subject line and body that is ready to paste into an email client."
        ),
    }

    user_message = {
        "role": "user",
        "content": (
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
            + _format_section("Education", receiver.education)
            + _format_section("Experiences", receiver.experiences)
            + _format_section("Skills", receiver.skills)
            + _format_section("Projects", receiver.projects)
            + "Receiver background (free text):\n"
            + f"{receiver.raw_text}\n\n"
            + f"Goal: {goal_text}\n\n"
            + "Please return:\n"
            + "1) A concise, specific subject line\n"
            + "2) A short email body (max ~200 words) that feels human, references shared interests or context, and ends with a clear but polite call to action."
        ),
    }

    return [system_message, user_message]


def generate_email(
    sender: SenderProfile,
    receiver: ReceiverProfile,
    goal: str,
    *,
    model: str = DEFAULT_MODEL,
) -> str:
    messages = build_prompt(sender, receiver, goal)
    
    # Combine system and user messages into a single prompt for Gemini
    system_content = messages[0]["content"]
    user_content = messages[1]["content"]
    prompt = f"System instruction: {system_content}\n\nUser request:\n{user_content}"
    
    content = _call_gemini(prompt, model=model)
    return content.strip()


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


def find_target_recommendations(
    purpose: str,
    field: str,
    sender_profile: dict | None = None,
    preferences: dict | None = None,
    *,
    model: str = DEFAULT_MODEL,
    count: int = 10
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
        
    Returns:
        List of recommendation dictionaries
    """
    profile_context = ""
    if sender_profile:
        profile_context = f"""
Sender background:
- Education: {', '.join(sender_profile.get('education', [])[:3]) or 'Not specified'}
- Experience: {', '.join(sender_profile.get('experiences', [])[:3]) or 'Not specified'}
- Skills: {', '.join(sender_profile.get('skills', [])[:5]) or 'Not specified'}
"""

    pref_context = ""
    if preferences:
        pref_lines: list[str] = []
        pref_map = {
            "seniority": "Seniority target",
            "org_type": "Organization type",
            "outreach_goal": "Outreach goal",
            "prominence": "Desired prominence"
        }
        for key, label in pref_map.items():
            value = preferences.get(key)
            if isinstance(value, str) and value.strip():
                pref_lines.append(f"{label}: {value.strip()}")
        if pref_lines:
            pref_context = "Additional targeting hints:\n" + "\n".join(f"- {line}" for line in pref_lines) + "\n"

    prompt = f"""You are a networking advisor helping someone find the best people to reach out to.

Purpose: {purpose}
Field: {field}
{profile_context}
{pref_context}

Generate a list of {count} real, notable people who would be good targets for this outreach.
Focus on well-known figures who are:
- Active and influential in the specified field
- Appropriate for the stated purpose
- Likely to be receptive to professional outreach

Return a JSON array with this structure:
[
    {{
        "name": "Full Name",
        "position": "Current Position/Title",
        "field": "Their specific area",
        "match_score": 85,
        "match_reason": "Why they're a good match",
        "common_interests": "Potential common ground with the sender"
    }},
    ...
]

The match_score should be 60-95 based on how well they fit the purpose and field.
Include a mix of highly prominent and more accessible people.

Return JSON only, no other text."""

    content = _call_gemini(prompt, model=model, json_mode=True)
    
    try:
        recommendations = json.loads(content)
        # Sort by match score
        recommendations.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        return recommendations[:count]
    except json.JSONDecodeError:
        # Return some default recommendations based on field
        return [
            {
                "name": "Contact in " + field,
                "position": "Professional",
                "field": field,
                "match_score": 70,
                "match_reason": "Relevant to your field",
                "common_interests": "Shared interest in " + field
            }
        ]


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
