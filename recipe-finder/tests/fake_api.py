"""A fake Claude Messages API that streams scripted replies, for tests."""

import json

import anthropic
import httpx2


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


def fake_client(requests, script=None, status=200):
    """An Anthropic client whose requests are recorded in `requests` and answered from
    `script` (default SCRIPT); with status != 200 every request fails with that status."""
    replies = iter(script or SCRIPT)

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append((request.headers, json.loads(request.content)))
        if status != 200:
            error = {"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}}
            return httpx2.Response(status, json=error)
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=next(replies))

    return anthropic.Anthropic(
        api_key="test-key",
        base_url="http://fake-api.test",
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )
