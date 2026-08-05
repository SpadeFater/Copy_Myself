from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Mapping
from typing import Any

from agent.service import ChatRunResult, ChatService
from app_logging import configure_logging
from config import load_settings


def format_response(state: Mapping[str, Any]) -> str:
    return f"Copy_Myself: {state.get('response') or 'No response.'}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Copy_Myself personal assistant.")
    parser.add_argument("message", nargs="*", help="Message to send to the agent.")
    return parser


async def _run(message: str) -> ChatRunResult:
    service = ChatService()
    try:
        result = await service.achat(message, "cli")
        while result.status == "pending_approval" and result.pending_approval is not None:
            pending = result.pending_approval
            print(f"Approval required: {pending.service_id} / {pending.tool}\n{pending.summary}")
            if not sys.stdin.isatty():
                approved = False
                print("Non-interactive input: rejecting tool call.")
            else:
                approved = input("Approve? [y/N] ").strip().casefold() == "y"
            result = await service.resume(pending.approval_id, approved, "cli")
        return result
    finally:
        await service.runner.close()


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    args = build_parser().parse_args()
    message = " ".join(args.message).strip() or input("You: ").strip()
    result = asyncio.run(_run(message))
    print(format_response({"response": result.response}))


if __name__ == "__main__":
    main()
