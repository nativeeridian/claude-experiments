# Stage 1: The agent loop

## What this stage adds

A chat program in the terminal. Claude can call two tools: `get_today` and `read_profile`. Every request and response is written to a trace file. The loop that ties this together (`harness/loop.py`) is the part you write.

```
cli.py ──user text──► run_turn (loop.py) ──► TracingModelClient ──► AnthropicModelClient ──► Claude API
   ▲                      │   ▲                     │
   │                      │   └── tool_results ◄────┼── ToolRegistry.dispatch ──► get_today, read_profile
   └──── TurnResult ◄─────┘                         └── Tracer (data/traces/*.jsonl)
```

| File | Role |
|---|---|
| `harness/client.py` | The only code that calls the API. It sets the model, thinking, effort and refusal fallback. |
| `harness/tools.py` | Tool registry. Pydantic models generate tool schemas and validate inputs. Errors come back as outcomes, not exceptions. |
| `harness/trace.py` | Logs to JSONL. Every request carries the entire transcript, which shows that the API keeps no state between calls. |
| `harness/loop.py` | **Your part:** the loop. |
| `tools/basics.py` | Facts the model can't know otherwise: today's date and the household profile. |
| `cli.py` | The chat UI, plus `/trace`, `/tools`, `/history` and `/system`. |

## Key ideas

- **The model never runs anything.** It returns `stop_reason: "tool_use"` and waits. Your code runs the tool and replies with a `tool_result` that carries the same `id`.
- **The API is stateless.** Each call sends the whole conversation again. `/trace` shows input tokens rising with each call within a turn.
- **The transcript is append-only.** Responses are appended exactly as they arrive, thinking blocks included, and nothing earlier is edited.
- **Stop reasons decide what happens next.** `tool_use` continues the loop. Anything else (`end_turn`, `max_tokens`, `refusal`) ends the turn.
- **Every `tool_use` needs a `tool_result`.** This holds even when the iteration cap is reached.

## Your turn

1. Read the docstring of `run_turn` in `src/meal_agent/harness/loop.py`.
2. Run `uv run pytest tests/test_loop.py -v`. All 12 tests fail.
3. Implement the loop until they pass. It takes about 20–30 lines.
4. Run the chat with `uv run meal-agent` and ask "What day is it, and what should I cook tonight?". Then run `/trace` and `/history`.

## Break it on purpose (needs your API key)

| Experiment | What to look for |
|---|---|
| Skip appending the tool_result message, then call the model again | The API rejects the request: every `tool_use` needs a `tool_result` |
| Comment out the `get_today` registration and ask about tonight | The model guesses the date or asks you. Either way, it doesn't know. |
| Change `read_profile`'s docstring to `"Gets data."` | Whether it still calls the tool when you ask for a dinner idea |
| `MEAL_AGENT_MAX_ITERATIONS=1 uv run meal-agent` | The loop stops after one call with "max_iterations" |
| Compare `in tok` for call 1 and call 2 in `/trace` | Call 2 is larger because it resends call 1's content plus the tool results |
