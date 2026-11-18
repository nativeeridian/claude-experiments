"""The agent loop.

Call the model, run whatever tools it asks for, send the results back, and repeat until it
stops asking. `tests/test_loop.py` is the contract; `docs/notes/01-agent-loop.md` walks through
this file line by line.
"""

from dataclasses import dataclass
from typing import Any

from meal_agent.harness.client import ModelClient
from meal_agent.harness.tools import ToolRegistry


@dataclass(frozen=True)
class TurnResult:
    text: str  # the final response's text blocks, joined ("" if there were none)
    stop_reason: str  # "end_turn", "max_tokens", "refusal", or "max_iterations"
    iterations: int  # model calls made during this turn


async def run_turn(
    client: ModelClient,
    registry: ToolRegistry,
    messages: list[dict[str, Any]],
    *,
    system: str,
    max_iterations: int,
) -> TurnResult:
    """Run one user turn until Claude stops asking for tools.

    `messages` is the whole conversation so far and already ends with the user's new message.
    Every response and every batch of tool results is appended to it. Nothing already in it is
    ever changed.
    """
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")

    for iteration in range(1, max_iterations + 1):
        # The API keeps no state between calls, so every call sends the whole conversation.
        response = await client.create(
            system=system, messages=messages, tools=registry.definitions()
        )

        # Record the reply exactly as received, thinking blocks included. An empty reply
        # (possible on a refusal) is skipped because the API rejects empty messages.
        if response.content:
            messages.append({"role": "assistant", "content": response.content})
        text = "".join(block.text for block in response.content if block.type == "text")

        # Anything other than a tool request ends the turn.
        if response.stop_reason != "tool_use":
            return TurnResult(text, response.stop_reason, iteration)

        # Run each requested tool, in order, and answer all of them in ONE user message.
        # Each result names the tool_use it answers by id.
        results = []
        for block in response.content:
            if block.type == "tool_use":
                outcome = await registry.dispatch(block.name, block.input)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": outcome.content,
                        "is_error": outcome.is_error,
                    }
                )
        messages.append({"role": "user", "content": results})

    # The cap was reached while Claude still wanted tools. The last results are already
    # appended, so every tool_use has its tool_result and the next turn can continue.
    return TurnResult(text, "max_iterations", max_iterations)
