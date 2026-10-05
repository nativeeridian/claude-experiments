"""Web app: a chat page plus a streaming JSON API over the recipe index.

Run locally with `python -m recipe_finder serve`; on Vercel, ../app.py exposes `app`.

Environment variables:
  ANTHROPIC_API_KEY  required for chat
  APP_PASSWORD       visitors must enter this to chat; required when deployed on Vercel,
                     so a public URL can't spend your API credits
  CLAUDE_MODEL       default claude-opus-5-5
  CLAUDE_EFFORT      low | medium | high | xhigh | max (default medium)
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import threading
from pathlib import Path
from urllib.parse import unquote

import anthropic
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from .assistant import DEFAULT_EFFORT, MODEL, run_turn, to_jsonable
from .search import RecipeIndex

log = logging.getLogger(__name__)

PAGE = Path(__file__).parent / "static" / "index.html"
MAX_HISTORY_BYTES = 2_000_000  # Vercel caps request bodies at 4.5 MB

app = FastAPI(title="Recipe Finder", docs_url=None, redoc_url=None, openapi_url=None)

_index: RecipeIndex | None = None
_index_lock = threading.Lock()


def get_index() -> RecipeIndex:
    """Load the recipe index once per server instance, on first use."""
    global _index
    with _index_lock:
        if _index is None:
            _index = RecipeIndex()
    return _index


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _password() -> str:
    return os.environ.get("APP_PASSWORD", "")


def _password_required() -> bool:
    return bool(_password()) or bool(os.environ.get("VERCEL"))


def check_password(request: Request) -> None:
    expected = _password()
    if not expected:
        if os.environ.get("VERCEL"):
            raise HTTPException(503, "Chat is off until APP_PASSWORD is set in the Vercel project settings.")
        return  # running locally without a password
    # The page URL-encodes the password, since headers can't carry non-ASCII text.
    given = unquote(request.headers.get("x-app-password", ""))
    if not hmac.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(401, "Wrong password.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)


@app.get("/", response_class=HTMLResponse)
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


@app.get("/api/status")
def status() -> dict:
    return {"password_required": _password_required()}


@app.post("/api/login", dependencies=[Depends(check_password)])
def login() -> dict:
    return {"ok": True}


def _error_text(exc: Exception) -> str:
    if isinstance(exc, anthropic.AuthenticationError):
        return "The Anthropic API key was rejected. Check ANTHROPIC_API_KEY in the project settings."
    if isinstance(exc, anthropic.RateLimitError):
        return "Too many requests to Claude right now. Wait a moment and try again."
    if isinstance(exc, anthropic.APIStatusError):
        return f"Claude API error {exc.status_code}: {exc.message}"
    if isinstance(exc, anthropic.APIConnectionError):
        return "Couldn't reach the Claude API. Try again in a moment."
    if isinstance(exc, TypeError) and "authentication" in str(exc):
        return "No Anthropic API key is configured. Set ANTHROPIC_API_KEY in the project settings."
    return "Something went wrong. Try again, or start a new chat."


@app.post("/api/chat", dependencies=[Depends(check_password)])
def chat(
    body: ChatRequest,
    index: RecipeIndex = Depends(get_index),
    client: anthropic.Anthropic = Depends(get_client),
) -> StreamingResponse:
    if len(json.dumps(body.history)) > MAX_HISTORY_BYTES:
        raise HTTPException(413, "This chat is too long. Start a new chat.")
    model = os.environ.get("CLAUDE_MODEL", MODEL)
    effort = os.environ.get("CLAUDE_EFFORT", DEFAULT_EFFORT)

    def events():
        history = body.history
        try:
            for event in run_turn(client, index, history, body.message, model, effort):
                yield json.dumps(event, ensure_ascii=False) + "\n"
            # The browser keeps the conversation and sends it back next turn.
            yield json.dumps({"type": "done", "history": to_jsonable(history)}, ensure_ascii=False) + "\n"
        except Exception as exc:  # report every failure to the page instead of a dead stream
            log.exception("chat turn failed")
            yield json.dumps({"type": "error", "text": _error_text(exc)}) + "\n"

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
