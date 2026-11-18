"""The contract for `run_turn` (src/meal_agent/harness/loop.py).

These tests fail until you implement the loop. Run them with:

    uv run pytest tests/test_loop.py -v

Each test drives the loop with a FakeModelClient that returns scripted responses, then checks
what the loop sent to the model and what it appended to the transcript.
"""

import pytest
from pydantic import BaseModel, ConfigDict

from meal_agent.harness.loop import run_turn
from meal_agent.harness.tools import ToolRegistry
from tests.fakes import FakeModelClient, message, text, thinking, tool_use

SYSTEM = "You are a test assistant."


class EchoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


@pytest.fixture
def registry() -> ToolRegistry:
    registry = ToolRegistry()

    @registry.tool()
    async def get_today(args) -> str:
        """Returns today's date."""
        return "Wednesday 2026-11-18"

    @registry.tool(args=EchoArgs)
    async def echo(args: EchoArgs) -> str:
        """Repeats the text back."""
        return args.text

    @registry.tool()
    async def boom(args) -> str:
        """Always fails."""
        raise RuntimeError("kaboom")

    return registry


def user(content: str) -> dict:
    return {"role": "user", "content": content}


async def turn(client, registry, messages, max_iterations=10):
    return await run_turn(client, registry, messages, system=SYSTEM, max_iterations=max_iterations)


# 1. One call, no tools


async def test_plain_answer_takes_one_call(registry):
    response = message(text("Try a chickpea curry."), stop_reason="end_turn")
    client = FakeModelClient(response)
    messages = [user("Dinner idea?")]

    result = await turn(client, registry, messages)

    assert result.text == "Try a chickpea curry."
    assert result.stop_reason == "end_turn"
    assert result.iterations == 1
    assert messages[-1] == {"role": "assistant", "content": response.content}


async def test_sends_system_prompt_and_tool_definitions(registry):
    client = FakeModelClient(message(text("ok"), stop_reason="end_turn"))

    await turn(client, registry, [user("hi")])

    request = client.requests[0]
    assert request["system"] == SYSTEM
    assert request["tools"] == registry.definitions()


# 2. Tool use: the model asks, your code answers


async def test_tool_call_then_answer(registry):
    asks = message(text("Let me check."), tool_use("get_today"), stop_reason="tool_use")
    answers = message(text("It's Wednesday."), stop_reason="end_turn")
    client = FakeModelClient(asks, answers)
    messages = [user("What day is it?")]

    result = await turn(client, registry, messages)

    assert result.text == "It's Wednesday."
    assert result.iterations == 2
    tool_use_id = asks.content[1].id
    assert messages == [
        user("What day is it?"),
        {"role": "assistant", "content": asks.content},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": "Wednesday 2026-11-18",
                    "is_error": False,
                }
            ],
        },
        {"role": "assistant", "content": answers.content},
    ]


async def test_api_is_stateless_so_each_call_resends_the_whole_conversation(registry):
    asks = message(tool_use("get_today"), stop_reason="tool_use")
    client = FakeModelClient(asks, message(text("done"), stop_reason="end_turn"))
    messages = [user("What day is it?")]

    await turn(client, registry, messages)

    first, second = client.requests
    assert len(first["messages"]) == 1
    assert len(second["messages"]) == 3  # user, assistant tool_use, user tool_result
    assert second["messages"][:1] == first["messages"]


async def test_parallel_tool_calls_go_back_in_one_user_message_in_order(registry):
    asks = message(
        tool_use("echo", {"text": "first"}),
        tool_use("get_today"),
        tool_use("echo", {"text": "third"}),
        stop_reason="tool_use",
    )
    client = FakeModelClient(asks, message(text("done"), stop_reason="end_turn"))
    messages = [user("go")]

    await turn(client, registry, messages)

    results = messages[2]["content"]
    assert messages[2]["role"] == "user"
    assert [r["tool_use_id"] for r in results] == [b.id for b in asks.content]
    assert [r["content"] for r in results] == ["first", "Wednesday 2026-11-18", "third"]


async def test_tool_errors_go_back_to_the_model_and_the_loop_continues(registry):
    asks = message(tool_use("boom"), tool_use("not_a_tool"), stop_reason="tool_use")
    client = FakeModelClient(asks, message(text("Sorry, that failed."), stop_reason="end_turn"))
    messages = [user("go")]

    result = await turn(client, registry, messages)

    boom_result, unknown_result = messages[2]["content"]
    assert boom_result["is_error"] is True
    assert "kaboom" in boom_result["content"]
    assert unknown_result["is_error"] is True
    assert result.text == "Sorry, that failed."


# 3. The transcript is append-only


async def test_history_is_append_only_and_keeps_thinking_blocks(registry):
    earlier = [user("hi"), {"role": "assistant", "content": [text("hello")]}, user("Dinner?")]
    messages = list(earlier)
    response = message(thinking("considering…"), text("Pasta."), stop_reason="end_turn")
    client = FakeModelClient(response)

    await turn(client, registry, messages)

    assert messages[:3] == earlier
    assert messages[3]["content"] is response.content  # appended as received, not rebuilt
    assert messages[3]["content"][0].type == "thinking"


async def test_text_from_several_blocks_is_joined(registry):
    response = message(thinking(), text("Pasta "), text("tonight."), stop_reason="end_turn")
    client = FakeModelClient(response)

    result = await turn(client, registry, [user("Dinner?")])

    assert result.text == "Pasta tonight."


# 4. Other stop reasons end the turn


async def test_max_tokens_returns_the_partial_answer(registry):
    client = FakeModelClient(message(text("Monday: lentil so"), stop_reason="max_tokens"))

    result = await turn(client, registry, [user("Plan the week")])

    assert result.stop_reason == "max_tokens"
    assert result.text == "Monday: lentil so"


async def test_refusal_stops_without_running_tools_or_appending_empty_content(registry):
    client = FakeModelClient(message(stop_reason="refusal"))
    messages = [user("something declined")]

    result = await turn(client, registry, messages)

    assert result.stop_reason == "refusal"
    assert result.text == ""
    assert messages == [user("something declined")]


# 5. The iteration cap


async def test_stops_at_the_iteration_cap(registry):
    client = FakeModelClient(forever=lambda: message(tool_use("get_today"), stop_reason="tool_use"))
    messages = [user("loop forever")]

    result = await turn(client, registry, messages, max_iterations=3)

    assert result.stop_reason == "max_iterations"
    assert result.iterations == 3
    assert len(client.requests) == 3


async def test_every_tool_use_gets_a_tool_result_even_at_the_cap(registry):
    client = FakeModelClient(forever=lambda: message(tool_use("get_today"), stop_reason="tool_use"))
    messages = [user("loop forever")]

    await turn(client, registry, messages, max_iterations=2)

    tool_use_ids = [
        block.id
        for m in messages
        if m["role"] == "assistant"
        for block in m["content"]
        if block.type == "tool_use"
    ]
    tool_result_ids = [
        block["tool_use_id"]
        for m in messages
        if m["role"] == "user" and isinstance(m["content"], list)
        for block in m["content"]
    ]
    assert tool_use_ids == tool_result_ids
    assert messages[-1]["role"] == "user"
