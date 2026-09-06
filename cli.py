from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Mapping
from typing import Any

from agent.service import ChatRunResult, ChatService
from app_logging import configure_logging
from config import load_settings
from config import rollback_model_provider_settings
from llm.model_sync import refresh_model_provider


def format_response(state: Mapping[str, Any]) -> str:
    return f"Copy_Myself: {state.get('response') or 'No response.'}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Copy_Myself personal assistant.")
    parser.add_argument("message", nargs="*", help="Message to send to the agent.")
    return parser


def build_models_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="copy-myself models", description="Manage configured model providers.")
    actions = parser.add_subparsers(dest="action", required=True)
    refresh = actions.add_parser("refresh", help="Refresh a provider's upstream model catalog.")
    refresh.add_argument("provider_name")
    refresh.add_argument("--json", action="store_true", dest="as_json")
    rollback = actions.add_parser("rollback", help="Restore the latest model settings backup.")
    rollback.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _refresh_payload(result) -> dict[str, object]:
    return {
        "provider": result.provider.name,
        "models": list(result.models),
        "current_model": result.current_model,
        "current_model_available": result.current_model_available,
        "validation_error": result.validation_error,
    }


def _run_models_command(argv: list[str]) -> int:
    args = build_models_parser().parse_args(argv)
    try:
        if args.action == "refresh":
            payload = _refresh_payload(refresh_model_provider(args.provider_name))
        else:
            providers = rollback_model_provider_settings()
            payload = {"providers": [provider.to_record() for provider in providers]}
    except Exception as exc:
        print(f"模型操作失败: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False))
    elif args.action == "refresh":
        print(f"{payload['provider']}: {', '.join(payload['models'])}")
        if not payload["current_model_available"]:
            print(f"当前模型不可用: {payload['current_model']}")
    else:
        print(f"已回滚 {len(payload['providers'])} 个模型配置")
    return 0


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


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "models":
        settings = load_settings()
        configure_logging(settings.log_level)
        return _run_models_command(arguments[1:])

    settings = load_settings()
    configure_logging(settings.log_level)
    args = build_parser().parse_args(arguments)
    message = " ".join(args.message).strip() or input("You: ").strip()
    result = asyncio.run(_run(message))
    print(format_response({"response": result.response}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
