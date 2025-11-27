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
