from __future__ import annotations

import argparse
import json
from pathlib import Path

from .email_agent import (
    ReceiverProfile,
    SenderProfile,
    generate_email,
    summarize_receiver_resume,
    summarize_sender_resume,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a sincere first-contact cold email using sender and receiver profiles via the OpenAI API."
        )
    )
    sender_group = parser.add_mutually_exclusive_group(required=True)
    sender_group.add_argument(
        "--sender", type=Path, help="Path to sender JSON profile"
    )
    sender_group.add_argument(
        "--sender-resume", type=Path, help="Path to sender resume or bio text file"
    )

    receiver_group = parser.add_mutually_exclusive_group(required=True)
    receiver_group.add_argument(
        "--receiver", type=Path, help="Path to receiver JSON profile"
    )
    receiver_group.add_argument(
        "--receiver-resume", type=Path, help="Path to receiver resume or bio text file"
    )

    parser.add_argument(
        "--sender-motivation",
        help="Optional override for sender motivation when generating from resume",
    )
    parser.add_argument(
        "--sender-ask",
        help="Optional override for sender ask when generating from resume",
    )
    parser.add_argument(
        "--receiver-context",
        help="Optional override for receiver context when generating from resume",
    )
    parser.add_argument(
        "--sender-output",
        type=Path,
        help="Where to save generated sender profile JSON (only when using --sender-resume)",
    )
    parser.add_argument(
        "--receiver-output",
        type=Path,
        help="Where to save generated receiver profile JSON (only when using --receiver-resume)",
    )
    parser.add_argument("--goal", required=True, help="Goal for this email (e.g., request for a 20-min chat)")
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI chat completion model to use (default: gpt-4o-mini)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    sender = (
        SenderProfile.from_json(args.sender)
        if args.sender
        else _sender_from_resume(args)
    )
    receiver = (
        ReceiverProfile.from_json(args.receiver)
        if args.receiver
        else _receiver_from_resume(args)
    )

    email_text = generate_email(sender, receiver, args.goal, model=args.model)
    print(email_text)


def _sender_from_resume(args: argparse.Namespace) -> SenderProfile:
    resume_text = args.sender_resume.read_text(encoding="utf-8")
    profile = summarize_sender_resume(
        resume_text,
        motivation=args.sender_motivation,
        ask=args.sender_ask,
        model=args.model,
    )
    if args.sender_output:
        _write_profile(args.sender_output, profile)
    return profile


def _receiver_from_resume(args: argparse.Namespace) -> ReceiverProfile:
    resume_text = args.receiver_resume.read_text(encoding="utf-8")
    profile = summarize_receiver_resume(
        resume_text,
        context=args.receiver_context,
        model=args.model,
    )
    if args.receiver_output:
        _write_profile(args.receiver_output, profile)
    return profile


def _write_profile(path: Path, profile: SenderProfile | ReceiverProfile) -> None:
    payload = {field: getattr(profile, field) for field in profile.__dataclass_fields__}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
