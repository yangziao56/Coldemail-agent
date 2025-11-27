from __future__ import annotations

import argparse
from pathlib import Path

from .email_agent import ReceiverProfile, SenderProfile, generate_email


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a sincere first-contact cold email using sender and receiver profiles via the OpenAI API."
        )
    )
    parser.add_argument("--sender", required=True, type=Path, help="Path to sender JSON profile")
    parser.add_argument("--receiver", required=True, type=Path, help="Path to receiver JSON profile")
    parser.add_argument("--goal", required=True, help="Goal for this email (e.g., request for a 20-min chat)")
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI chat completion model to use (default: gpt-4o-mini)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    sender = SenderProfile.from_json(args.sender)
    receiver = ReceiverProfile.from_json(args.receiver)

    email_text = generate_email(sender, receiver, args.goal, model=args.model)
    print(email_text)


if __name__ == "__main__":
    main()
