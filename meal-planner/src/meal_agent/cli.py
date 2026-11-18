"""Terminal chat.

    uv run meal-agent            chat with Claude (needs ANTHROPIC_API_KEY)
    uv run meal-agent --demo     scripted replies, no key needed

Commands:
  /trace    what happened in the last turn: model calls, stop reasons, tokens, tool calls
  /tools    the tool definitions exactly as Claude sees them
  /history  the transcript so far, one line per message
  /system   the system prompt
  /quit     leave
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from meal_agent.config import PROJECT_ROOT, Settings
from meal_agent.harness.session import ChatSession, make_model_client
from meal_agent.harness.tools import ToolCall

STOP_NOTES = {
    "max_tokens": "The answer was cut off (max_tokens).",
    "refusal": "The model declined this request.",
    "max_iterations": "Stopped at the iteration cap before the model finished. See /trace.",
}


def show_tool_call(console: Console, call: ToolCall) -> None:
    args = json.dumps(call.input) if call.input else ""
    if call.outcome.is_error:
        console.print(f"  [red]✗ {call.name}({args})[/] [dim]{call.outcome.content[:200]}[/]")
    else:
        console.print(f"  [dim]→ {call.name}({args})  {call.duration_ms:.0f} ms[/]")


def show_trace(console: Console, session: ChatSession) -> None:
    turn = session.tracer.last_turn
    if not turn.model_calls:
        console.print("[dim]No turn recorded yet.[/]")
        return
    table = Table(title=f"Last turn: {turn.user_text[:60]!r}")
    for column in ("call", "stop_reason", "blocks", "in tok", "out tok", "cache read", "ms"):
        table.add_column(column)
    for i, call in enumerate(turn.model_calls, 1):
        table.add_row(
            str(i),
            str(call["stop_reason"]),
            ", ".join(call["blocks"]),
            str(call["input_tokens"]),
            str(call["output_tokens"]),
            str(call["cache_read_tokens"]),
            f"{call['duration_ms']:.0f}",
        )
    console.print(table)
    for call in turn.tool_calls:
        show_tool_call(console, call)
    console.print(f"[dim]Full requests and responses: {session.tracer.path}[/]")


def show_history(console: Console, messages: list[dict[str, Any]]) -> None:
    for i, message in enumerate(messages):
        content = message["content"]
        if isinstance(content, str):
            summary = repr(content[:70])
        else:
            summary = ", ".join(getattr(b, "type", None) or b.get("type", "?") for b in content)
        console.print(f"[dim]{i:>3}[/] [bold]{message['role']:<9}[/] {summary}")


async def chat(session: ChatSession, *, label: str) -> None:
    console = Console()

    def on_event(event: str, data: Any) -> None:
        if event == "tool_call":
            show_tool_call(console, data)

    session.tracer.add_listener(on_event)
    console.print(f"[bold]Meal planner[/] · {label} · /trace /tools /history /quit\n")

    while True:
        try:
            user_text = (await asyncio.to_thread(console.input, "[bold green]you ›[/] ")).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_text:
            continue
        if user_text in ("/quit", "/exit"):
            break
        if user_text == "/trace":
            show_trace(console, session)
            continue
        if user_text == "/tools":
            console.print_json(json.dumps(session.registry.definitions()))
            continue
        if user_text == "/history":
            show_history(console, session.messages)
            continue
        if user_text == "/system":
            console.print(session.system)
            continue

        try:
            with console.status("thinking…"):
                result = await session.send(user_text)
        except anthropic.APIError as e:
            console.print(f"[red]API error:[/] {e}")
            continue

        console.print(Markdown(result.text or "_(no text)_"))
        if result.stop_reason in STOP_NOTES:
            console.print(f"[yellow]{STOP_NOTES[result.stop_reason]}[/]")
        turn = session.tracer.last_turn
        console.print(
            f"[dim]{result.iterations} model call(s) · "
            f"{turn.input_tokens:,} in / {turn.output_tokens:,} out tokens[/]\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(prog="meal-agent", description="Terminal meal-planning chat")
    parser.add_argument("--demo", action="store_true", help="scripted replies, no API key needed")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    if not args.demo and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set. Put it in meal-planner/.env (see .env.example), "
            "or try `uv run meal-agent --demo`."
        )
    settings = Settings.from_env()
    session = ChatSession(settings, make_model_client(settings, demo=args.demo))
    label = "demo (scripted replies)" if args.demo else settings.model
    asyncio.run(chat(session, label=label))


if __name__ == "__main__":
    main()
