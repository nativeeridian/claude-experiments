"""A scripted stand-in for Claude, so the UI can be tried with no API key.

Everything except the model is real. The real loop runs, the real tools are called, and the
transcript and trace are recorded exactly as they would be. Only the replies are canned: the
first call asks for `get_today` and `read_profile`, and the second turns their results into a
suggestion. Include the word "error" in a message to see how a failing tool call looks.
"""

import itertools
import json
from typing import Any

from anthropic.types.beta import (
    BetaMessage,
    BetaTextBlock,
    BetaThinkingBlock,
    BetaToolUseBlock,
    BetaUsage,
)

from meal_agent.harness.trace import to_jsonable

DEMO_NOTE = (
    "*Demo mode: this reply is scripted, not Claude. The tool calls and transcript are real.*"
)


class DemoModelClient:
    def __init__(self) -> None:
        self._ids = itertools.count(1)

    async def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> BetaMessage:
        last = messages[-1]["content"]
        if isinstance(last, str):
            blocks, stop = self._start_turn(last)
        else:
            blocks, stop = self._answer(last), "end_turn"
        sent = json.dumps([system, tools, to_jsonable(messages)])
        return BetaMessage(
            id=f"msg_demo_{next(self._ids)}",
            type="message",
            role="assistant",
            model="demo (scripted)",
            content=blocks,
            stop_reason=stop,
            # Rough token counts (about 4 characters per token), so the trace shows the
            # input growing as the conversation is resent.
            usage=BetaUsage(
                input_tokens=len(sent) // 4,
                output_tokens=sum(len(json.dumps(to_jsonable(b))) for b in blocks) // 4,
            ),
        )

    def _start_turn(self, user_text: str) -> tuple[list[Any], str]:
        thinking = BetaThinkingBlock(type="thinking", thinking="", signature="demo-signature")
        if "error" in user_text.lower():
            return [
                thinking,
                BetaTextBlock(type="text", text="Let me look that recipe up."),
                self._tool_use("lookup_recipe", {"name": "pesto orzo"}),
            ], "tool_use"
        return [
            thinking,
            BetaTextBlock(type="text", text="Let me check today's date and your profile."),
            self._tool_use("get_today", {}),
            self._tool_use("read_profile", {}),
        ], "tool_use"

    def _answer(self, tool_results: list[dict[str, Any]]) -> list[Any]:
        failed = [r for r in tool_results if r.get("is_error")]
        if failed:
            text = (
                f"That lookup failed: {failed[0]['content']}\n\n"
                "In a real session Claude would read this error and try a different approach.\n\n"
                f"{DEMO_NOTE}"
            )
            return [BetaTextBlock(type="text", text=text)]

        found: dict[str, Any] = {}
        for result in tool_results:
            try:
                found.update(json.loads(result["content"]))
            except (json.JSONDecodeError, TypeError):
                pass
        weekday = found.get("weekday", "today")
        minutes = found.get("cooking_minutes", {}).get(weekday.lower(), 45)
        names = {p.get("diet"): p.get("name") for p in found.get("people", [])}
        omnivore = names.get("omnivore", "you")
        vegetarian = names.get("lacto-ovo vegetarian", "your partner")

        if minutes <= 45:
            idea = (
                "**Chickpea and spinach coconut curry over brown rice**, about 30 minutes. "
                "The base uses vegetable stock, so it works for both of you.\n\n"
                f"- **{vegetarian}:** the curry as is.\n"
                f"- **{omnivore}:** the curry plus chicken thighs, seared in a second pan "
                "while it simmers (+10 minutes).\n\n"
                "Make a double batch of the curry and it becomes tomorrow's lunch."
            )
        else:
            idea = (
                "**Sheet-pan harissa tofu with roasted vegetables and farro**, about an hour, "
                "mostly hands-off.\n\n"
                f"- **{vegetarian}:** the tofu tray.\n"
                f"- **{omnivore}:** the tofu tray plus harissa chicken on a second tray in the "
                "same oven."
            )
        text = (
            f"It's **{weekday}**, so you have about **{minutes} minutes** tonight.\n\n"
            f"{idea}\n\n{DEMO_NOTE}"
        )
        return [BetaTextBlock(type="text", text=text)]

    def _tool_use(self, name: str, input: dict[str, Any]) -> BetaToolUseBlock:
        return BetaToolUseBlock(
            type="tool_use", id=f"toolu_demo_{next(self._ids)}", name=name, input=input
        )
