from __future__ import annotations

import argparse
from pathlib import Path

from .email_agent import ReceiverProfile, SenderProfile, generate_email
from config import DEFAULT_MODEL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a sincere first-contact cold email using sender and receiver profiles via the Gemini API."
        )
    )
    sender_group = parser.add_mutually_exclusive_group(required=True)
    sender_group.add_argument("--sender-json", type=Path, help="Path to sender JSON profile")
    sender_group.add_argument("--sender-pdf", type=Path, help="Path to sender PDF resume")

    receiver_group = parser.add_mutually_exclusive_group(required=True)
    receiver_group.add_argument("--receiver-json", type=Path, help="Path to receiver JSON profile")
    receiver_group.add_argument("--receiver-pdf", type=Path, help="Path to receiver PDF resume")
    receiver_group.add_argument("--receiver-name", type=str, help="Receiver's name (for web search)")

    parser.add_argument("--motivation", help="Required if --sender-pdf is used: why you want to reach out")
    parser.add_argument("--ask", help="Required if --sender-pdf is used: what you hope the receiver can help with")
    parser.add_argument(
        "--receiver-context",
        help="Optional context about how you know or found the receiver (used with PDFs or JSON profiles)",
    )
    parser.add_argument(
        "--receiver-field",
        help="Required if --receiver-name is used: the field/domain of the receiver (e.g., 'AI research', 'machine learning professor')",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Maximum number of web pages to scrape when using --receiver-name (default: 3)",
    )
    parser.add_argument("--goal", required=True, help="Goal for this email (e.g., request for a 20-min chat)")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Gemini model to use (default: gemini-2.0-flash)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.sender_pdf and (not args.motivation or not args.ask):
        raise SystemExit("--motivation and --ask are required when using --sender-pdf")

    if args.receiver_name and not args.receiver_field:
        raise SystemExit("--receiver-field is required when using --receiver-name")

    if args.sender_pdf:
        sender = SenderProfile.from_pdf(
            args.sender_pdf,
            motivation=args.motivation or "",
            ask=args.ask or "",
            model=args.model,
        )
    else:
        sender = SenderProfile.from_json(args.sender_json)

    if args.receiver_name:
        print(f"🔍 Searching the web for information about '{args.receiver_name}' in field '{args.receiver_field}'...")
        receiver = ReceiverProfile.from_web(
            name=args.receiver_name,
            field=args.receiver_field,
            model=args.model,
            context=args.receiver_context,
            max_pages=args.max_pages,
        )
        print(f"✅ Found information from {len(receiver.sources or [])} sources")
        if receiver.sources:
            print("📚 Sources:")
            for source in receiver.sources:
                print(f"   - {source}")
        print()
    elif args.receiver_pdf:
        receiver = ReceiverProfile.from_pdf(
            args.receiver_pdf,
            model=args.model,
            context=args.receiver_context,
        )
    else:
        receiver = ReceiverProfile.from_json(args.receiver_json)

    email_text = generate_email(sender, receiver, args.goal, model=args.model)
    print(email_text)


if __name__ == "__main__":
    main()
