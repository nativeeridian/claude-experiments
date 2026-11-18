"""Local web chat server.

    uv run meal-agent-web            chat with Claude at http://127.0.0.1:8000
    uv run meal-agent-web --demo     scripted replies, no API key needed

The server holds one ChatSession in memory and binds to localhost only, since it spends
your API key on behalf of whoever can reach it.

Endpoints:
  GET  /             the chat page
  GET  /api/state    transcript, trace, profile and tool definitions
  POST /api/chat     run one turn; streams server-sent events as it goes:
                       model_call  each model call (stop reason, blocks, tokens)
                       tool_call   each tool call (input, result, error flag)
                       done        the final text and stop reason
                       error       if the turn failed
  POST /api/reset    start a new session
"""

import argparse
import asyncio
import json
import os
import sys
from collections.abc import AsyncIterator, Callable
from importlib.resources import files
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from meal_agent.config import PROJECT_ROOT, Settings
from meal_agent.harness.client import ModelClient
from meal_agent.harness.session import ChatSession, make_model_client
from meal_agent.harness.tools import ToolCall
from meal_agent.harness.trace import to_jsonable
from meal_agent.tools.basics import load_profile


class ChatRequest(BaseModel):
    message: str


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(to_jsonable(data))}\n\n"


def tool_call_payload(call: ToolCall) -> dict[str, Any]:
    return {
        "name": call.name,
        "input": call.input,
        "content": call.outcome.content,
        "is_error": call.outcome.is_error,
        "duration_ms": round(call.duration_ms),
    }


def create_app(settings: Settings, client_factory: Callable[[], ModelClient], *, label: str):
    app = FastAPI(title="Meal planner")
    state = {"session": ChatSession(settings, client_factory())}
    # Keep running turns referenced, so a closed browser tab can't get one garbage-collected.
    running: set[asyncio.Task] = set()
    page = files("meal_agent.web").joinpath("static/index.html").read_text(encoding="utf-8")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return page

    @app.get("/api/state")
    async def get_state() -> dict[str, Any]:
        session: ChatSession = state["session"]
        return {
            "label": label,
            "demo": label.startswith("demo"),
            "busy": session.busy,
            "system": session.system,
            "messages": to_jsonable(session.messages),
            "turns": [
                {
                    "user_text": turn.user_text,
                    "failed": turn.failed,
                    "model_calls": turn.model_calls,
                    "tool_calls": [tool_call_payload(c) for c in turn.tool_calls],
                    "input_tokens": turn.input_tokens,
                    "output_tokens": turn.output_tokens,
                }
                for turn in session.tracer.turns
            ],
            "trace_file": str(session.tracer.path),
            "profile": load_profile(settings),
            "tools": session.registry.definitions(),
        }

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> StreamingResponse:
        session: ChatSession = state["session"]
        text = request.message.strip()
        if not text:
            raise HTTPException(400, "Empty message")
        if session.busy:
            raise HTTPException(409, "A turn is already running")

        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def on_event(event: str, data: Any) -> None:
            payload = tool_call_payload(data) if event == "tool_call" else data
            queue.put_nowait(sse(event, payload))

        async def run() -> None:
            try:
                result = await session.send(text, on_event=on_event)
                queue.put_nowait(sse("done", result))
            except Exception as e:  # noqa: BLE001 - report any failure to the page
                queue.put_nowait(sse("error", {"message": f"{type(e).__name__}: {e}"}))
            finally:
                queue.put_nowait(None)

        async def stream() -> AsyncIterator[str]:
            task = asyncio.create_task(run())
            running.add(task)
            task.add_done_callback(running.discard)
            while (chunk := await queue.get()) is not None:
                yield chunk
            await task

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/reset")
    async def reset() -> dict[str, bool]:
        if state["session"].busy:
            raise HTTPException(409, "A turn is already running")
        state["session"] = ChatSession(settings, client_factory())
        return {"ok": True}

    return app


def main() -> None:
    parser = argparse.ArgumentParser(prog="meal-agent-web", description="Local meal-planning chat")
    parser.add_argument("--demo", action="store_true", help="scripted replies, no API key needed")
    parser.add_argument("--host", default="127.0.0.1", help="default: localhost only")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    if not args.demo and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set. Put it in meal-planner/.env (see .env.example), "
            "or try `uv run meal-agent-web --demo`."
        )
    settings = Settings.from_env()
    label = "demo (scripted replies)" if args.demo else settings.model
    app = create_app(settings, lambda: make_model_client(settings, demo=args.demo), label=label)
    print(f"Meal planner ({label}) on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
