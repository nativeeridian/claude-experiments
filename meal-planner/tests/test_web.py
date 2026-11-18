import json

import httpx
import pytest

from meal_agent.config import Settings
from meal_agent.harness.demo import DemoModelClient
from meal_agent.web.app import create_app
from tests.fakes import FakeModelClient, message, text


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path)


def client_for(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for chunk in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in chunk.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def test_chat_streams_tool_and_model_events_then_done(settings):
    app = create_app(settings, DemoModelClient, label="demo (scripted replies)")
    async with client_for(app) as http:
        response = await http.post("/api/chat", json={"message": "What should I cook tonight?"})
        events = parse_sse(response.text)

        assert [name for name, _ in events] == [
            "model_call",
            "tool_call",
            "tool_call",
            "model_call",
            "done",
        ]
        assert [data["name"] for name, data in events if name == "tool_call"] == [
            "get_today",
            "read_profile",
        ]
        done = events[-1][1]
        assert done["stop_reason"] == "end_turn"
        assert done["iterations"] == 2

        state = (await http.get("/api/state")).json()
        assert state["demo"] is True
        assert [m["role"] for m in state["messages"]] == ["user", "assistant", "user", "assistant"]
        assert state["turns"][0]["tool_calls"][0]["name"] == "get_today"
        assert state["profile"]["source"].startswith("profile.example.json")
        assert [t["name"] for t in state["tools"]] == ["get_today", "read_profile"]


async def test_failed_turn_reports_an_error_and_rolls_back(settings):
    # A client with no scripted responses fails on the first call.
    app = create_app(settings, FakeModelClient, label="test")
    async with client_for(app) as http:
        response = await http.post("/api/chat", json={"message": "hi"})
        [(name, data)] = parse_sse(response.text)
        assert name == "error"

        state = (await http.get("/api/state")).json()
        assert state["messages"] == []
        assert state["turns"][0]["failed"] is True


async def test_reset_starts_a_new_session(settings):
    app = create_app(
        settings,
        lambda: FakeModelClient(message(text("hello"), stop_reason="end_turn")),
        label="test",
    )
    async with client_for(app) as http:
        await http.post("/api/chat", json={"message": "hi"})
        assert len((await http.get("/api/state")).json()["messages"]) == 2

        await http.post("/api/reset")
        assert (await http.get("/api/state")).json()["messages"] == []


async def test_index_page_and_empty_message(settings):
    app = create_app(settings, DemoModelClient, label="demo (scripted replies)")
    async with client_for(app) as http:
        page = await http.get("/")
        assert page.status_code == 200
        assert "<title>Meal planner</title>" in page.text
        assert (await http.post("/api/chat", json={"message": "  "})).status_code == 400
