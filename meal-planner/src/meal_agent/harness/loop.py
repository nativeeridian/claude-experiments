"""The agent loop.

YOUR TURN: implement `run_turn` below. `tests/test_loop.py` defines what "done" means:

    uv run pytest tests/test_loop.py -v

Everything around the loop already exists: the client that calls Claude (`client.py`), the
tool registry (`tools.py`), tracing (`trace.py`) and the chat UI (`cli.py`). The loop only
connects them.
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

    `messages` is the whole conversation so far. It already ends with the user's new message.

    The contract:

    1. Call `await client.create(system=system, messages=messages,
       tools=registry.definitions())`.

    2. Append the response as an assistant turn, with its content exactly as received:
       `{"role": "assistant", "content": response.content}`. That includes thinking blocks.
       Never edit, reorder or remove anything already in `messages`. The history is append-only.
       One exception: if `response.content` is empty (possible on a refusal), append nothing,
       because the API rejects messages with empty content.

    3. If `response.stop_reason == "tool_use"`, run every block whose `type == "tool_use"`
       through `await registry.dispatch(block.name, block.input)`. Then append ONE user message
       whose content is a list of tool_result blocks, in the same order as the tool_use blocks:

           {"type": "tool_result", "tool_use_id": block.id,
            "content": outcome.content, "is_error": outcome.is_error}

       Then go back to step 1.

    4. Any other stop_reason ends the turn. Return a TurnResult with the joined text of that
       response's `text` blocks, its stop_reason, and the number of model calls made.

    5. Never make more than `max_iterations` model calls. If the cap is reached while Claude
       still wants tools, still run them and append their results, because every tool_use
       needs a matching tool_result. Then return with stop_reason "max_iterations" and the
       text of the last response.
    """
    raise NotImplementedError(
        "Your turn: implement run_turn in src/meal_agent/harness/loop.py "
        "(see its docstring and tests/test_loop.py)."
    )
