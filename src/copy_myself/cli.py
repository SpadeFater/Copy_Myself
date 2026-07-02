from __future__ import annotations

import argparse
from collections.abc import Mapping
from typing import Any

from copy_myself.agent.graph import run_agent
from copy_myself.config import load_settings
from copy_myself.logging import configure_logging


def format_response(state: Mapping[str, Any]) -> str:
    return f"Copy_Myself: {state.get('response') or '暂无回复。'}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Copy_Myself personal butler agent.")
    parser.add_argument("message", nargs="*", help="Message to send to the agent.")
    return parser


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    parser = build_parser()
    args = parser.parse_args()
    user_input = " ".join(args.message).strip()
    if not user_input:
        user_input = input("You: ").strip()
    state = run_agent(user_input)
    print(format_response(state))


if __name__ == "__main__":
    main()
