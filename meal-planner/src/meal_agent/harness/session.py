"""A chat session: the harness pieces wired together, independent of any interface.

The terminal (`cli.py`) and the web app (`web/app.py`) both drive a `ChatSession`, so they run
the same loop, tools, prompt and tracing. Stage 3 adds saving and resuming here.
"""

import asyncio
from typing import Any

from meal_agent.config import Settings
from meal_agent.harness.client import AnthropicModelClient, ModelClient
from meal_agent.harness.loop import TurnResult, run_turn
from meal_agent.harness.prompts import load_system_prompt
from meal_agent.harness.tools import ToolRegistry
from meal_agent.harness.trace import TraceListener, Tracer, TracingModelClient
from meal_agent.tools.basics import register_basic_tools


def make_model_client(settings: Settings, *, demo: bool = False) -> ModelClient:
    if demo:
        from meal_agent.harness.demo import DemoModelClient

        return DemoModelClient()
    return AnthropicModelClient(settings)


class ChatSession:
    def __init__(self, settings: Settings, model_client: ModelClient):
        self.settings = settings
        self.system = load_system_prompt()  # frozen for the whole session
        self.registry = ToolRegistry()
        register_basic_tools(self.registry, settings)
        self.tracer = Tracer.for_new_session(settings.data_dir / "traces")
        self.registry.add_listener(self.tracer.record_tool_call)
        self.client = TracingModelClient(model_client, self.tracer)
        self.messages: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    async def send(self, user_text: str, on_event: TraceListener | None = None) -> TurnResult:
        """Run one turn. `on_event` hears this turn's model calls and tool calls live."""
        async with self._lock:
            turn_start = len(self.messages)
            self.messages.append({"role": "user", "content": user_text})
            self.tracer.start_turn(user_text)
            if on_event:
                self.tracer.add_listener(on_event)
            try:
                return await run_turn(
                    self.client,
                    self.registry,
                    self.messages,
                    system=self.system,
                    max_iterations=self.settings.max_iterations,
                )
            except BaseException:
                # Dropping the unfinished tail is safe: what's left is a prefix the API has
                # already seen, so it doesn't count as editing history.
                del self.messages[turn_start:]
                self.tracer.last_turn.failed = True
                raise
            finally:
                if on_event:
                    self.tracer.remove_listener(on_event)
