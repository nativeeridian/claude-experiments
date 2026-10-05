import json
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from fake_api import fake_client
from recipe_finder import web


@pytest.fixture
def make_app(index, monkeypatch):
    """A TestClient for the app wired to the test index and a fake Claude API."""
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)

    def make(requests, **fake_kwargs):
        web.app.dependency_overrides[web.get_index] = lambda: index
        web.app.dependency_overrides[web.get_client] = lambda: fake_client(requests, **fake_kwargs)
        return TestClient(web.app)

    yield make
    web.app.dependency_overrides.clear()


def _events(response) -> list[dict]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_page_and_status(make_app):
    client = make_app([])
    assert "Recipe Finder" in client.get("/").text
    status = client.get("/api/status").json()
    assert status["chat"] == "open"  # local run, no password
    assert "repository-url=https%3A%2F%2Fgithub.com%2Fnativeeridian%2Fclaude-experiments%2Ftree%2Fmain%2Frecipe-finder" in status["deploy_url"]
    assert "env=ANTHROPIC_API_KEY,APP_PASSWORD" in status["deploy_url"]


def test_public_search_and_recipe(make_app, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")  # public deployment without a key or password
    client = make_app([])
    response = client.get("/api/search", params={"have": "chicken thighs, lemon, feta", "limit": 5})
    assert response.status_code == 200
    assert "s-maxage" in response.headers["cache-control"]
    recipes = response.json()["recipes"]
    assert recipes[0]["id"] == 2 and recipes[0]["uses"] == ["chicken thighs", "lemon", "feta"]
    assert "image" in recipes[0]
    assert 1 not in [r["id"] for r in recipes]  # only 2 ratings; below the default minimum

    top = client.get("/api/search", params={"sort": "rating"}).json()["recipes"]
    assert [r["id"] for r in top][:2] == [4, 2]
    assert client.get("/api/search", params={"q": "soup"}).json()["recipes"][0]["name"] == "Chicken Noodle Soup"

    assert client.get("/api/recipe/2").json()["name"] == "Greek Chicken With Feta"
    assert client.get("/api/recipe/999").status_code == 404
    assert client.get("/api/search", params={"sort": "bogus"}).status_code == 422
    assert client.get("/api/search", params={"limit": 500}).status_code == 422


def test_chat_streams_events_and_returns_history(make_app):
    requests = []
    client = make_app(requests)
    events = _events(client.post("/api/chat", json={"message": "chicken thighs, lemon, feta?"}))

    assert [e["type"] for e in events] == ["status", "status", "text", "recipes", "done"]
    assert events[1]["text"] == "Reading reviews of Greek Chicken With Feta"
    assert events[3]["recipes"][0]["name"] == "Greek Chicken With Feta"
    history = events[-1]["history"]
    assert [m["role"] for m in history] == ["user", "assistant", "user", "assistant", "user", "assistant"]

    # The browser sends the history back; the API sees the earlier turn unchanged.
    events = _events(client.post("/api/chat", json={"message": "Full recipe?", "history": history}))
    assert events[-1]["type"] == "done"
    assert requests[3][1]["messages"][:6] == history


def test_password_gate(make_app, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "open sesame")
    client = make_app([])
    assert client.get("/api/status").json()["chat"] == "password"
    assert client.post("/api/login").status_code == 401
    assert client.post("/api/login", headers={"X-App-Password": "nope"}).status_code == 401
    assert client.post("/api/login", headers={"X-App-Password": "open sesame"}).json() == {"ok": True}
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 401


def test_non_ascii_password(make_app, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "crème brûlée 🍮")
    client = make_app([])
    encoded = quote("crème brûlée 🍮")
    assert client.post("/api/login", headers={"X-App-Password": encoded}).json() == {"ok": True}


def test_vercel_without_password_refuses_chat(make_app, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    client = make_app([])
    assert client.get("/api/status").json()["chat"] == "off"
    assert client.post("/api/login").status_code == 503
    response = client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 503


def test_bad_api_key_is_reported_in_the_stream(make_app):
    client = make_app([], status=401)
    events = _events(client.post("/api/chat", json={"message": "hi"}))
    assert events == [{"type": "error", "text": web._error_text(_auth_error())}]


def test_rejects_oversized_input(make_app):
    client = make_app([])
    assert client.post("/api/chat", json={"message": "x" * 2001}).status_code == 422
    huge = [{"role": "user", "content": "x" * (web.MAX_HISTORY_BYTES + 1)}]
    assert client.post("/api/chat", json={"message": "hi", "history": huge}).status_code == 413


def _auth_error():
    import anthropic
    import httpx2

    response = httpx2.Response(401, request=httpx2.Request("POST", "http://fake-api.test/v1/messages"))
    return anthropic.AuthenticationError("invalid x-api-key", response=response, body=None)
