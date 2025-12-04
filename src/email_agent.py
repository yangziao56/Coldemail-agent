from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import google.generativeai as genai
from openai import OpenAI
from PyPDF2 import PdfReader

from config import DEFAULT_MODEL, RECOMMENDATION_MODEL, USE_OPENAI_WEB_SEARCH


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
    contact_email: str | None = None
    honors: list[str] = field(default_factory=list)
    activities: list[str] = field(default_factory=list)
    papers: list[dict[str, Any]] = field(default_factory=list)

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
            contact_email=str(data.get("contact_email")).strip() if data.get("contact_email") else None,
            honors=_load_str_list(data, "honors", path),
            activities=_load_str_list(data, "activities", path),
            papers=_load_papers(data, "papers", path),
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
            contact_email=scraped_info.contact_email,
            honors=scraped_info.honors,
            activities=scraped_info.activities,
            papers=scraped_info.papers,
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


def _load_papers(data: dict[str, Any], key: str, source: Path | str) -> list[dict[str, Any]]:
    value = data.get(key, [])
    if not isinstance(value, list):
        return []
    papers: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        paper = {
            "title": str(item.get("title", "") or "").strip(),
            "venue": str(item.get("venue", "") or "").strip(),
            "year": str(item.get("year", "") or "").strip(),
            "doi": str(item.get("doi", "") or "").strip(),
            "url": str(item.get("url", "") or "").strip(),
            "abstract": str(item.get("abstract", "") or "").strip(),
        }
        if any(paper.values()):
            papers.append(paper)
    return papers


def extract_text_from_pdf(pdf_path: Path) -> str:
    # Use context manager to ensure Windows releases the file handle before deletion
    with pdf_path.open("rb") as f:
        reader = PdfReader(f)
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


# Override with richer receiver info (web-scraped + papers)
def build_prompt(sender: SenderProfile, receiver: ReceiverProfile, goal: str) -> list[dict[str, str]]:
    goal_text = goal.strip()
    if not goal_text:
        raise ValueError("Goal must be a non-empty string")

    def _format_section(title: str, items: list[str]) -> str:
        if not items:
            return f"- {title}: (not specified)\n"
        bullet_points = "\n".join(f"  - {item}" for item in items)
        return f"- {title}:\n{bullet_points}\n"

    def _format_papers(papers: list[dict[str, Any]]) -> str:
        if not papers:
            return "- Papers: (not specified)\n"
        lines: list[str] = []
        for paper in papers:
            title = str(paper.get("title", "") or "").strip() or "Paper"
            venue = str(paper.get("venue", "") or "").strip()
            year = str(paper.get("year", "") or "").strip()
            doi = str(paper.get("doi", "") or "").strip()
            abstract = str(paper.get("abstract", "") or "").strip()
            meta = " ".join(filter(None, [venue, year]))
            line = f"  - {title}"
            if meta:
                line += f" ({meta})"
            if doi:
                line += f" | DOI: {doi}"
            if abstract:
                line += f"\n    Abstract: {abstract[:400]}"
            lines.append(line)
        return "- Papers:\n" + "\n".join(lines) + "\n"

    system_message = {
        "role": "system",
        "content": (
            "You craft sincere, concise first-contact cold emails that help two people build a genuine connection. "
            "Use the provided sender and receiver details to highlight authentic overlaps and mutual value. "
            "If a specific research area or detail is not present in the receiver info, skip it—never leave placeholder text. "
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
            + (f"- Contact: {receiver.contact_email}\n" if receiver.contact_email else "")
            + (f"- Context: {receiver.context}\n" if receiver.context else "")
            + _format_section("Education", receiver.education)
            + _format_section("Experiences", receiver.experiences)
            + _format_section("Skills", receiver.skills)
            + _format_section("Projects", receiver.projects)
            + _format_section("Honors", receiver.honors)
            + _format_section("Activities", receiver.activities)
            + _format_papers(receiver.papers)
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


def _build_sender_context(sender_profile: dict | None) -> str:
    if not sender_profile:
        return ""
    return f"""
Sender background:
- Education: {', '.join(sender_profile.get('education', [])[:3]) or 'Not specified'}
- Experience: {', '.join(sender_profile.get('experiences', [])[:3]) or 'Not specified'}
- Skills: {', '.join(sender_profile.get('skills', [])[:5]) or 'Not specified'}
"""


def _build_preference_context(preferences: dict | None) -> str:
    if not preferences:
        return ""
    pref_lines: list[str] = []
    pref_map = {
        "seniority": "Seniority target",
        "org_type": "Organization type",
        "outreach_goal": "Outreach goal",
        "prominence": "Desired prominence",
    }
    for key, label in pref_map.items():
        value = preferences.get(key)
        if isinstance(value, str) and value.strip():
            pref_lines.append(f"{label}: {value.strip()}")
    if not pref_lines:
        return ""
    return "Additional targeting hints:\n" + "\n".join(f"- {line}" for line in pref_lines) + "\n"


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
    sources_list = "\n".join(f"- {s}" for s in sources) if sources else ""

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
{"- sources (list of URLs) summarizing where this person appeared in web snippets" if include_web_section else ""}

Focus on people who fit the purpose and preferences; prefer those visible in the web snippets. Be diverse and mix accessible profiles, not only famous leaders.
If unsure about someone, omit them.
Include source URLs when available.
Return JSON only."""


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
    query_name = field or purpose or "targets"
    query_field = purpose or field or ""

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

    # Try OpenAI (gpt-5.1) with built-in web_search tool
    if USE_OPENAI_WEB_SEARCH:
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
            recommendations = json.loads(content).get("recommendations", [])
            recommendations.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            if recommendations:
                return recommendations[:count]
        except Exception as e:
            print(f"OpenAI recommendation (web_search) error: {e}")

    # Fallback 1: our own web scrape + OpenAI
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
        recommendations = json.loads(content).get("recommendations", [])
        recommendations.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        if recommendations:
            return recommendations[:count]
    except Exception as e:
        print(f"OpenAI recommendation (scrape fallback) error: {e}")

    # Fallback 2: Gemini text-only generation
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
        recommendations = json.loads(content).get("recommendations", [])
        recommendations.sort(key=lambda x: x.get('match_score', 0), reverse=True)
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
