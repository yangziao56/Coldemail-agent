from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openai import OpenAI


@dataclass
class SenderProfile:
    name: str
    raw_text: str
    motivation: str
    ask: str

    @classmethod
    def from_json(cls, path: Path) -> "SenderProfile":
        data = _load_json(path)
        return cls(
            name=_require_field(data, "name", path),
            raw_text=_require_field(data, "raw_text", path),
            motivation=_require_field(data, "motivation", path),
            ask=_require_field(data, "ask", path),
        )


@dataclass
class ReceiverProfile:
    name: str
    raw_text: str
    context: str | None = None

    @classmethod
    def from_json(cls, path: Path) -> "ReceiverProfile":
        data = _load_json(path)
        return cls(
            name=_require_field(data, "name", path),
            raw_text=_require_field(data, "raw_text", path),
            context=data.get("context"),
        )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON in {path}: {exc}") from exc


def _require_field(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Field '{key}' is required and must be a non-empty string in {path}")
    return value.strip()


def _require_text(value: str | None, field: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"Field '{field}' is required and must be a non-empty string")
    return value.strip()


def build_prompt(sender: SenderProfile, receiver: ReceiverProfile, goal: str) -> list[dict[str, str]]:
    goal_text = goal.strip()
    if not goal_text:
        raise ValueError("Goal must be a non-empty string")

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
            "Sender background (free text):\n"
            f"{sender.raw_text}\n\n"
            "Receiver profile:\n"
            f"- Name: {receiver.name}\n"
            + (f"- Context: {receiver.context}\n" if receiver.context else "")
            + "Receiver background (free text):\n"
            f"{receiver.raw_text}\n\n"
            f"Goal: {goal_text}\n\n"
            "Please return:\n"
            "1) A concise, specific subject line\n"
            "2) A short email body (max ~200 words) that feels human, references shared interests or context, and ends with a clear but polite call to action."
        ),
    }

    return [system_message, user_message]


def _complete_json(
    messages: list[dict[str, str]], *, model: str, client: "OpenAI" | None = None
) -> dict[str, Any]:
    from openai import OpenAI

    api_client = client or OpenAI()
    completion = api_client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI response did not contain any content")

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI response was not valid JSON") from exc


def summarize_sender_resume(
    resume_text: str,
    *,
    motivation: str | None = None,
    ask: str | None = None,
    model: str = "gpt-4o-mini",
    client: "OpenAI" | None = None,
) -> SenderProfile:
    """Use an LLM to build a sender profile directly from a resume string."""

    trimmed_resume = _require_text(resume_text, "resume_text")

    system_message = {
        "role": "system",
        "content": (
            "Extract concise sender profile fields from the provided resume. "
            "Always return a JSON object with keys: name, motivation, ask. "
            "Use short sentences written in the sender's own voice."
        ),
    }
    user_message = {
        "role": "user",
        "content": (
            "Resume text (can include Chinese or English):\n"
            f"{trimmed_resume}\n\n"
            "Fill missing motivation/ask with the most plausible outreach intent based on the resume."
        ),
    }

    raw_data = _complete_json([system_message, user_message], model=model, client=client)

    name = _require_text(raw_data.get("name"), "name")
    motivation_value = motivation or raw_data.get("motivation")
    ask_value = ask or raw_data.get("ask")

    return SenderProfile(
        name=name,
        raw_text=trimmed_resume,
        motivation=_require_text(motivation_value, "motivation"),
        ask=_require_text(ask_value, "ask"),
    )


def summarize_receiver_resume(
    resume_text: str,
    *,
    context: str | None = None,
    model: str = "gpt-4o-mini",
    client: "OpenAI" | None = None,
) -> ReceiverProfile:
    """Use an LLM to build a receiver profile directly from a resume or bio string."""

    trimmed_resume = _require_text(resume_text, "resume_text")

    system_message = {
        "role": "system",
        "content": (
            "Summarize the receiver's profile from the given text. "
            "Return a JSON object with keys: name. Keep the name concise."
        ),
    }
    user_message = {
        "role": "user",
        "content": (
            "Receiver background text (can include Chinese or English):\n"
            f"{trimmed_resume}\n\n"
            "Use one or two sentences for the inferred context field (e.g., shared interests)."
        ),
    }

    raw_data = _complete_json([system_message, user_message], model=model, client=client)

    return ReceiverProfile(
        name=_require_text(raw_data.get("name"), "name"),
        raw_text=trimmed_resume,
        context=(context or raw_data.get("context")) or None,
    )


def generate_email(
    sender: SenderProfile,
    receiver: ReceiverProfile,
    goal: str,
    *,
    model: str = "gpt-4o-mini",
    client: "OpenAI" | None = None,
) -> str:
    messages = build_prompt(sender, receiver, goal)
    from openai import OpenAI

    api_client = client or OpenAI()
    completion = api_client.chat.completions.create(model=model, messages=messages)
    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI response did not contain any content")
    return content.strip()
