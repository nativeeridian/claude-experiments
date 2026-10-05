"""Web app: free recipe search for everyone, plus an optional Claude chat.

Run locally with `python -m recipe_finder serve`; on Vercel, ../app.py exposes `app`.

Search (/api/search, /api/recipe) never calls Claude, so it's open to anyone at no cost.
Chat (/api/chat) spends the deployer's Anthropic credits, so on Vercel it only turns on
when both of these are set; otherwise the page offers a link to deploy your own copy.

Environment variables:
  ANTHROPIC_API_KEY  the deployer's Anthropic API key
  APP_PASSWORD       visitors must enter this to chat (required on Vercel)
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
from typing import Literal
from urllib.parse import quote, unquote

import anthropic
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from .assistant import DEFAULT_EFFORT, MODEL, run_turn, to_jsonable
from .search import MAX_LIMIT, SORTS, RecipeIndex

log = logging.getLogger(__name__)

PAGE = Path(__file__).parent / "static" / "index.html"
MAX_HISTORY_BYTES = 2_000_000  # Vercel caps request bodies at 4.5 MB
MAX_TERMS = 15
MAX_TERM_CHARS = 60

SOURCE_URL = "https://github.com/nativeeridian/claude-experiments/tree/main/recipe-finder"
# Vercel's deploy button: clones this folder into the visitor's own GitHub account and
# asks for their own API key and password while setting up their copy.
DEPLOY_URL = "https://vercel.com/new/clone?" + "&".join(
    f"{k}={quote(v, safe=',')}"
    for k, v in {
        "repository-url": "https://github.com/nativeeridian/claude-experiments/tree/main/recipe-finder",
        "project-name": "recipe-finder",
        "repository-name": "recipe-finder",
        "env": "ANTHROPIC_API_KEY,APP_PASSWORD",
        "envDescription": "Your Anthropic API key (console.anthropic.com), and a password "
        "visitors must enter to chat so others can't spend your credits.",
        "envLink": SOURCE_URL + "#deploy-your-own-copy",
    }.items()
)

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


def chat_mode() -> Literal["open", "password", "off"]:
    """open: anyone can chat (local runs only); password: APP_PASSWORD needed; off: no chat."""
    if os.environ.get("APP_PASSWORD"):
        return "password"
    if os.environ.get("VERCEL"):
        return "off"  # never spend a deployer's credits without a password in front
    return "open"


def check_password(request: Request) -> None:
    mode = chat_mode()
    if mode == "off":
        raise HTTPException(503, "Chat isn't turned on for this site.")
    if mode == "open":
        return
    # The page URL-encodes the password, since headers can't carry non-ASCII text.
    given = unquote(request.headers.get("x-app-password", ""))
    if not hmac.compare_digest(given.encode(), os.environ["APP_PASSWORD"].encode()):
        raise HTTPException(401, "Wrong password.")


def _terms(csv: str) -> list[str]:
    terms = [t.strip()[:MAX_TERM_CHARS] for t in csv.split(",") if t.strip()]
    return terms[:MAX_TERMS]


@app.get("/", response_class=HTMLResponse)
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


@app.get("/api/status")
def status() -> dict:
    return {"chat": chat_mode(), "deploy_url": DEPLOY_URL, "source_url": SOURCE_URL}


@app.get("/api/search")
def search(
    response: Response,
    have: str = "",
    avoid: str = "",
    q: str = Query("", max_length=100),
    max_minutes: int | None = Query(None, ge=1),
    max_missing: int | None = Query(None, ge=0),
    sort: str = Query("best", pattern="^(" + "|".join(SORTS) + ")$"),
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    index: RecipeIndex = Depends(get_index),
) -> dict:
    """Ingredient search without AI; free for anyone to use."""
    result = index.search(
        ingredients=_terms(have),
        exclude=_terms(avoid),
        query=q.strip() or None,
        max_minutes=max_minutes,
        max_missing=max_missing,
        sort=sort,
        limit=limit,
    ).to_dict()
    for recipe in result["recipes"]:
        recipe["image"] = index.card(recipe["id"])["image"]
    # Results only change when the bundle does, so let Vercel's CDN cache them.
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=86400"
    return result


@app.get("/api/recipe/{recipe_id}")
def recipe(recipe_id: int, response: Response, index: RecipeIndex = Depends(get_index)) -> dict:
    found = index.get(recipe_id)
    if found is None:
        raise HTTPException(404, "No such recipe.")
    response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=86400"
    return found


@app.post("/api/login", dependencies=[Depends(check_password)])
def login() -> dict:
    return {"ok": True}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)


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
