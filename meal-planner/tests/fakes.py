"""A scripted stand-in for the Claude API.

`FakeModelClient` returns pre-written responses in order and records every request it receives,
so tests can check exactly what the loop sent. The responses are real SDK objects, so code that
works against the fake works against the API.
"""

import itertools
from collections.abc import Callable
from typing import Any

from anthropic.types.beta import (
    BetaMessage,
    BetaTextBlock,
    BetaThinkingBlock,
    BetaToolUseBlock,
    BetaUsage,
)

_ids = itertools.count(1)


def text(value: str) -> BetaTextBlock:
    return BetaTextBlock(type="text", text=value)


def thinking(value: str = "") -> BetaThinkingBlock:
    return BetaThinkingBlock(type="thinking", thinking=value, signature="fake-signature")


def tool_use(name: str, input: dict[str, Any] | None = None) -> BetaToolUseBlock:
    return BetaToolUseBlock(
        type="tool_use", id=f"toolu_{next(_ids):03d}", name=name, input=input or {}
    )


def message(*blocks: Any, stop_reason: str) -> BetaMessage:
    return BetaMessage(
        id=f"msg_{next(_ids):03d}",
        type="message",
        role="assistant",
        model="claude-opus-5-5",
        content=list(blocks),
        stop_reason=stop_reason,
        usage=BetaUsage(input_tokens=100, output_tokens=20),
    )


class FakeModelClient:
    def __init__(self, *responses: BetaMessage, forever: Callable[[], BetaMessage] | None = None):
        self._responses = list(responses)
        self._forever = forever
        self.requests: list[dict[str, Any]] = []

    async def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> BetaMessage:
        # Copy the list: the loop keeps appending to it after this call returns.
        self.requests.append({"system": system, "messages": list(messages), "tools": tools})
        if self._responses:
            return self._responses.pop(0)
        if self._forever:
            return self._forever()
        raise AssertionError(
            f"The loop made model call #{len(self.requests)}, but the test only scripted "
            f"{len(self.requests) - 1}. It should have stopped earlier."
        )
