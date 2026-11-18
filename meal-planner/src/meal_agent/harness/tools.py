"""Tool registry.

Each tool is an async function plus a Pydantic model for its arguments. The same model produces
the JSON schema Claude sees and validates the input Claude sends back, so the two can't drift
apart (decision 0004).

`dispatch` never raises. Unknown tools, invalid input, and exceptions inside a tool all come
back as a `ToolOutcome` with `is_error=True`, so the loop can hand the error to Claude and Claude
can retry or work around it.
"""

import inspect
import json
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError


class NoArgs(BaseModel):
    """Argument model for tools that take no input."""

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class ToolOutcome:
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class ToolCall:
    """What listeners (tracing, the chat display) hear about each dispatched call."""

    name: str
    input: dict[str, Any]
    outcome: ToolOutcome
    duration_ms: float


Handler = Callable[[Any], Awaitable[Any]]
Listener = Callable[[ToolCall], None]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Handler

    def definition(self) -> dict[str, Any]:
        schema = self.args_model.model_json_schema()
        # The tool's own description is what Claude reads; the args model's name and docstring
        # are for developers.
        schema.pop("title", None)
        schema.pop("description", None)
        return {"name": self.name, "description": self.description, "input_schema": schema}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._listeners: list[Listener] = []

    def tool(
        self, args: type[BaseModel] = NoArgs, name: str | None = None
    ) -> Callable[[Handler], Handler]:
        """Register an async function as a tool. Its docstring becomes the description."""

        def decorator(fn: Handler) -> Handler:
            tool_name = name or fn.__name__
            if tool_name in self._tools:
                raise ValueError(f"Tool {tool_name!r} is already registered")
            # Unwrap hard line breaks inside paragraphs; keep blank lines between them.
            description = re.sub(r"(?<!\n)\n(?!\n)", " ", inspect.cleandoc(fn.__doc__ or ""))
            if not description:
                raise ValueError(f"Tool {tool_name!r} needs a docstring: it's what Claude reads")
            self._tools[tool_name] = Tool(tool_name, description, args, fn)
            return fn

        return decorator

    def definitions(self) -> list[dict[str, Any]]:
        """Tool definitions in registration order, ready for the API's `tools` parameter."""
        return [tool.definition() for tool in self._tools.values()]

    def add_listener(self, listener: Listener) -> None:
        self._listeners.append(listener)

    async def dispatch(self, name: str, raw_input: dict[str, Any]) -> ToolOutcome:
        start = time.perf_counter()
        outcome = await self._run(name, raw_input)
        call = ToolCall(name, raw_input, outcome, (time.perf_counter() - start) * 1000)
        for listener in self._listeners:
            listener(call)
        return outcome

    async def _run(self, name: str, raw_input: dict[str, Any]) -> ToolOutcome:
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(self._tools) or "none"
            return ToolOutcome(f"Unknown tool {name!r}. Available tools: {available}.", True)
        try:
            args = tool.args_model.model_validate(raw_input)
        except ValidationError as e:
            problems = "; ".join(
                f"{'.'.join(map(str, err['loc'])) or 'input'}: {err['msg']}" for err in e.errors()
            )
            return ToolOutcome(f"Invalid input for {name}: {problems}", True)
        try:
            result = await tool.handler(args)
        except Exception as e:  # noqa: BLE001 - any tool failure goes back to Claude
            return ToolOutcome(f"{name} failed: {type(e).__name__}: {e}", True)
        return ToolOutcome(_to_text(result))


def _to_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, default=str)
