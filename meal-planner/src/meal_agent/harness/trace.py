"""Tracing: every request, response and tool call, appended to a JSONL file.

Each request event holds the *entire* `messages` list that was sent. The file grows quickly, and
that is the point: it shows that the API keeps no state and the harness resends the whole
conversation on every call.

`TracingModelClient` wraps any `ModelClient`, so the loop never has to know tracing exists.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from anthropic.types.beta import BetaMessage
from pydantic import BaseModel

from meal_agent.harness.client import ModelClient
from meal_agent.harness.tools import ToolCall


def to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(v) for v in value]
    return value


@dataclass
class TurnStats:
    user_text: str = ""
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def input_tokens(self) -> int:
        return sum(c["input_tokens"] for c in self.model_calls)

    @property
    def output_tokens(self) -> int:
        return sum(c["output_tokens"] for c in self.model_calls)


class Tracer:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.last_turn = TurnStats()

    @classmethod
    def for_new_session(cls, traces_dir: Path) -> "Tracer":
        stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        return cls(traces_dir / f"{stamp}.jsonl")

    def record(self, event: str, **data: Any) -> None:
        line = {"ts": datetime.now().isoformat(timespec="milliseconds"), "event": event, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(to_jsonable(line)) + "\n")

    def start_turn(self, user_text: str) -> None:
        self.last_turn = TurnStats(user_text=user_text)
        self.record("turn_start", user_text=user_text)

    def record_response(self, response: BetaMessage, duration_ms: float) -> None:
        self.last_turn.model_calls.append(
            {
                "stop_reason": response.stop_reason,
                "blocks": [block.type for block in response.content],
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_tokens": response.usage.cache_read_input_tokens or 0,
                "duration_ms": duration_ms,
            }
        )
        self.record("response", duration_ms=round(duration_ms), response=response)

    def record_tool_call(self, call: ToolCall) -> None:
        self.last_turn.tool_calls.append(call)
        self.record(
            "tool_call",
            name=call.name,
            input=call.input,
            content=call.outcome.content,
            is_error=call.outcome.is_error,
            duration_ms=round(call.duration_ms),
        )


class TracingModelClient:
    def __init__(self, inner: ModelClient, tracer: Tracer):
        self._inner = inner
        self._tracer = tracer

    async def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> BetaMessage:
        self._tracer.record("request", system=system, tools=tools, messages=messages)
        start = time.perf_counter()
        response = await self._inner.create(system=system, messages=messages, tools=tools)
        self._tracer.record_response(response, (time.perf_counter() - start) * 1000)
        return response
