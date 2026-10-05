"""Drive RecipeChat against a fake Messages API that streams scripted replies."""

import io
import json

import anthropic
import httpx2

from recipe_finder.assistant import RecipeChat


def _sse(*events) -> bytes:
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


def _reply(blocks, stop_reason):
    events = [
        {
            "type": "message_start",
            "message": {
                "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
                "content": [], "stop_reason": None, "stop_sequence": None,
                "usage": {"input_tokens": 10, "output_tokens": 1},
            },
        }
    ]
    for i, block in enumerate(blocks):
        if block["type"] == "thinking":
            start = {"type": "thinking", "thinking": "", "signature": ""}
            deltas = [{"type": "signature_delta", "signature": block["signature"]}]
        elif block["type"] == "tool_use":
            start = {"type": "tool_use", "id": block["id"], "name": block["name"], "input": {}}
            deltas = [{"type": "input_json_delta", "partial_json": json.dumps(block["input"])}]
        else:
            start = {"type": "text", "text": ""}
            deltas = [{"type": "text_delta", "text": block["text"]}]
        events.append({"type": "content_block_start", "index": i, "content_block": start})
        events += [{"type": "content_block_delta", "index": i, "delta": d} for d in deltas]
        events.append({"type": "content_block_stop", "index": i})
    events.append(
        {"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None},
         "usage": {"output_tokens": 20}}
    )
    events.append({"type": "message_stop"})
    return _sse(*events)


SCRIPT = [
    _reply(
        [
            {"type": "thinking", "signature": "sig-1"},
            {"type": "tool_use", "id": "toolu_1", "name": "search_recipes",
             "input": {"ingredients": ["chicken thighs", "lemon", "feta"], "min_reviews": 0, "limit": 3}},
        ],
        "tool_use",
    ),
    _reply(
        [{"type": "tool_use", "id": "toolu_2", "name": "get_recipe", "input": {"recipe_id": 2}}],
        "tool_use",
    ),
    _reply([{"type": "text", "text": "Make the **Greek Chicken With Feta**."}], "end_turn"),
    _reply([{"type": "text", "text": "Here are the steps."}], "end_turn"),
]


def _fake_client(requests):
    replies = iter(SCRIPT)

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append((request.headers, json.loads(request.content)))
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=next(replies))

    return anthropic.Anthropic(
        api_key="test-key",
        base_url="http://fake-api.test",
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )


def test_chat_runs_tools_and_keeps_append_only_history(index):
    requests = []
    out, status = io.StringIO(), io.StringIO()
    chat = RecipeChat(index, client=_fake_client(requests), out=out, status=status)

    reply = chat.send("I have chicken thighs, lemon and feta. What should I make?")

    assert reply == "Make the **Greek Chicken With Feta**."
    assert "Greek Chicken With Feta" in out.getvalue()
    assert "searching" in status.getvalue() and "opening recipe 2" in status.getvalue()
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
