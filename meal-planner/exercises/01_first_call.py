"""Warm-up: two raw calls to the Claude API, printed as JSON.

Run from the meal-planner/ directory:

    uv run --with anthropic python exercises/01_first_call.py

Requires ANTHROPIC_API_KEY in your environment. Costs a fraction of a cent.

While reading the output, note:
  (a) the block types inside `content` for each call
  (b) the `stop_reason` for each call
  (c) what's in `usage`
  (d) call 2: what is the model waiting for, and who is supposed to provide it?
"""

import json
import os
import sys

import anthropic

MODEL = "claude-opus-5-5"


def show(title: str, response: anthropic.types.Message) -> None:
    print(f"\n{'=' * 20} {title} {'=' * 20}")
    print(json.dumps(response.model_dump(mode="json"), indent=2))


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. See the setup steps in the chat or README.")

    client = anthropic.Anthropic()

    # Call 1: a plain question, no tools.
    r1 = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": "Suggest one 30-minute vegetarian dinner."}],
    )
    show("CALL 1: no tools", r1)

    # Call 2: the same kind of question, but the model can ask for a tool.
    r2 = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"effort": "low"},
        tools=[
            {
                "name": "get_today",
                "description": "Returns today's date and day of the week.",
                "input_schema": {"type": "object", "properties": {}},
            }
        ],
        messages=[{"role": "user", "content": "What day is it, and what should I cook tonight?"}],
    )
    show("CALL 2: with a tool", r2)


if __name__ == "__main__":
    main()
