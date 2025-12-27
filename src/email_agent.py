from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import google.generativeai as genai
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


def _call_gemini_with_search(prompt: str, *, model: str = GEMINI_SEARCH_MODEL, json_mode: bool = False) -> str:
    """
    Call Gemini API with Google Search grounding enabled.
    This allows the model to search the web for real-time information.
    """
    _configure_gemini()
    
    generation_config = {}
    if json_mode:
        generation_config["response_mime_type"] = "application/json"
    
    # Enable Google Search grounding
    gemini_model = genai.GenerativeModel(
        model,
        generation_config=generation_config or None,
        tools="google_search_retrieval"
    )
    
    response = gemini_model.generate_content(prompt)
    
    if not response.text:
        raise RuntimeError("Gemini response with search did not contain any content")
    return response.text


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
) -> str:
    messages = build_prompt(sender, receiver, goal, template=template)
    
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
- match_score (integer 60-95)
- match_reason (short string)
- common_interests (short string)
- evidence (list of 1-3 short strings; each should include a source URL and a grounded fact/snippet)
- sources (list of URLs; can be empty only if you explicitly set uncertainty to high)
- uncertainty (string: low, medium, or high, plus a short reason if needed)

Return up to {count} people. Prefer candidates you can verify with evidence. If you cannot find at least one credible source URL for a person, either omit them or mark uncertainty as high and keep claims minimal.
Rank candidates by: fit to purpose/field/preferences, likely contactability (if specified), and strength of evidence.
Be diverse and mix accessible profiles, not only famous leaders.
Return JSON only."""


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_recommendations(items: Any) -> list[dict[str, Any]]:
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

        normalized.append(
            {
                "name": name,
                "position": position or field,
                "field": field or position,
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
    pref_context = _build_preference_context(preferences)
    profile_context = _build_sender_context(sender_profile)

    # Primary: Gemini with Google Search grounding (fast and reliable)
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
            # Add instruction for real-time search
            search_prompt = (
                f"{prompt}\n\n"
                "IMPORTANT: Use Google Search to find REAL people who are currently active in this field. "
                "Search for recent faculty, researchers, professionals, or industry leaders. "
                "Include their actual current positions and affiliations. "
                "For each person, include evidence and source URLs from what you found. "
                "Do not make up names - only include people you can verify through search."
            )
            content = _call_gemini_with_search(search_prompt, model=GEMINI_SEARCH_MODEL, json_mode=True)
            raw_items = json.loads(content).get("recommendations", [])
            recommendations = _normalize_recommendations(raw_items)
            recommendations.sort(key=lambda x: _safe_int(x.get("match_score", 0), default=0), reverse=True)
            if recommendations:
                print(f"Gemini Search found {len(recommendations)} recommendations")
                return recommendations[:count]
        except Exception as e:
            print(f"Gemini Search recommendation error: {e}")

    # Fallback 1: OpenAI (gpt-5.1) with built-in web_search tool - DISABLED by default
    if USE_OPENAI_WEB_SEARCH and USE_OPENAI_RECOMMENDATIONS:
        try:
            content = _call_openai_json_with_web_search(
                _build_recommendation_prompt(
                    purpose=purpose,
                    field=field,
                    profile_context=profile_context,
                    pref_context=pref_context,
                    count=count,
                    include_web_section=False,
                    require_tool_use=True,
                ),
                model=RECOMMENDATION_MODEL,
            )
            raw_items = json.loads(content).get("recommendations", [])
            recommendations = _normalize_recommendations(raw_items)
            recommendations.sort(key=lambda x: _safe_int(x.get("match_score", 0), default=0), reverse=True)
            if recommendations:
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
            content = _call_gemini(
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
                model=model,
                json_mode=True,
            )
            raw_items = json.loads(content).get("recommendations", [])
            recommendations = _normalize_recommendations(raw_items)
            recommendations.sort(key=lambda x: _safe_int(x.get("match_score", 0), default=0), reverse=True)
            if recommendations:
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
