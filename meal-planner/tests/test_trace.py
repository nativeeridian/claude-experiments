import json

from meal_agent.harness.tools import ToolCall, ToolOutcome
from meal_agent.harness.trace import Tracer, TracingModelClient
from tests.fakes import FakeModelClient, message, text, thinking, tool_use


async def test_tracing_client_records_full_requests_and_responses(tmp_path):
    tracer = Tracer(tmp_path / "trace.jsonl")
    response = message(thinking("hmm"), text("hi"), tool_use("get_today"), stop_reason="tool_use")
    client = TracingModelClient(FakeModelClient(response), tracer)
    messages = [{"role": "user", "content": "hello"}]

    tracer.start_turn("hello")
    returned = await client.create(system="sys", messages=messages, tools=[])
    tracer.record_tool_call(ToolCall("get_today", {}, ToolOutcome("Wed"), 1.0))

    assert returned is response
    events = [json.loads(line) for line in tracer.path.read_text().splitlines()]
    assert [e["event"] for e in events] == ["turn_start", "request", "response", "tool_call"]
    assert events[1]["messages"] == messages
    assert events[2]["response"]["content"][0]["type"] == "thinking"

    turn = tracer.last_turn
    assert turn.model_calls[0]["blocks"] == ["thinking", "text", "tool_use"]
    assert (turn.input_tokens, turn.output_tokens) == (100, 20)
    assert [c.name for c in turn.tool_calls] == ["get_today"]
