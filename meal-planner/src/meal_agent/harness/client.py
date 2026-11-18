"""The one place that talks to the Claude API.

The loop depends on the small `ModelClient` protocol, not on the SDK directly. Tests swap in
a scripted fake, tracing wraps it, and later stages add compaction and streaming here.
"""

from typing import Any, Protocol

import anthropic
from anthropic.types.beta import BetaMessage

from meal_agent.config import Settings

# If the model declines a request, the API retries it on a fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ModelClient(Protocol):
    async def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> BetaMessage: ...


class AnthropicModelClient:
    def __init__(self, settings: Settings, client: anthropic.AsyncAnthropic | None = None):
        self._settings = settings
        self._client = client or anthropic.AsyncAnthropic()

    async def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> BetaMessage:
        return await self._client.beta.messages.create(
            model=self._settings.model,
            max_tokens=self._settings.max_tokens,
            system=system,
            messages=messages,
            tools=tools,
            thinking={"type": "adaptive"},
            output_config={"effort": self._settings.effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
