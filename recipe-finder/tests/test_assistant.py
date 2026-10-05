"""Drive RecipeChat against a fake Messages API that streams scripted replies."""

import io
import json

from fake_api import fake_client as _fake_client
from recipe_finder.assistant import RecipeChat, run_turn, to_jsonable


def test_chat_runs_tools_and_keeps_append_only_history(index):
    requests = []
    out, status = io.StringIO(), io.StringIO()
    chat = RecipeChat(index, client=_fake_client(requests), out=out, status=status)

    reply = chat.send("I have chicken thighs, lemon and feta. What should I make?")

    assert reply == "Make the **Greek Chicken With Feta**."
    assert "Greek Chicken With Feta" in out.getvalue()
    assert "Searching recipes with chicken thighs, lemon, feta" in status.getvalue()
    assert "Reading reviews of Greek Chicken With Feta" in status.getvalue()
    assert len(requests) == 3

    headers, first = requests[0]
    assert "server-side-fallback-2026-07-01" in headers["anthropic-beta"]
    assert first["fallbacks"] == "default"
    assert first["model"] == "claude-opus-5-5"
    assert first["output_config"] == {"effort": "medium"}
    assert first["stream"] is True
    assert {t["name"] for t in first["tools"]} == {"search_recipes", "get_recipe"}
    assert all(t["eager_input_streaming"] for t in first["tools"])

    # The search ran against the real index and its results went back to Claude.
    _, second = requests[1]
    assert second["messages"][1]["content"][0] == {"type": "thinking", "thinking": "", "signature": "sig-1"}
    result = second["messages"][2]["content"][0]
    assert result["tool_use_id"] == "toolu_1"
    found = json.loads(result["content"][0]["text"] if isinstance(result["content"], list) else result["content"])
    assert [r["id"] for r in found["recipes"]][:2] == [2, 1]

    _, third = requests[2]
    recipe = third["messages"][4]["content"][0]
    assert recipe["tool_use_id"] == "toolu_2"
    assert "review_snippets" in json.dumps(recipe)

    # A follow-up turn resends the earlier turn unchanged, plus Claude's answer.
    chat.send("Great, give me the full recipe.")
    _, fourth = requests[3]
    assert fourth["messages"][:5] == third["messages"]
    assert fourth["messages"][5]["role"] == "assistant"
    assert fourth["messages"][6] == {"role": "user", "content": "Great, give me the full recipe."}


def test_run_turn_events_and_json_history(index):
    requests = []
    client = _fake_client(requests)
    messages: list = []
    events = list(run_turn(client, index, messages, "chicken thighs, lemon, feta?"))

    kinds = [e["type"] for e in events]
    assert kinds.count("status") == 2 and "text" in kinds
    assert events[-1]["type"] == "recipes"
    card = events[-1]["recipes"][0]
    assert card["id"] == 2 and card["name"] == "Greek Chicken With Feta"
    assert card["url"].endswith("-2")

    # History survives a JSON round trip (as the web app stores it in the browser) and
    # matches what the SDK itself sent, so the next turn resends it byte-for-byte.
    history = json.loads(json.dumps(to_jsonable(messages)))
    assert history[:5] == requests[2][1]["messages"]
    list(run_turn(client, index, history, "Full recipe please."))
    assert requests[3][1]["messages"][:6] == json.loads(json.dumps(to_jsonable(messages)))
