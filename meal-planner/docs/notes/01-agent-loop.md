# Stage 1: The agent loop

## What this stage adds

You chat with the agent in the terminal (`uv run meal-agent`) or in a local web page (`uv run meal-agent-web`). Claude can call two tools, `get_today` and `read_profile`. Every request and response is logged to a trace file. Add `--demo` to either command to use scripted replies instead of Claude, with no API key needed.

```
cli.py / web/app.py ──► ChatSession.send ──► run_turn (loop.py) ──► TracingModelClient ──► Claude API
                                                │   ▲                     │
                                                │   └── tool_results ◄────┼── ToolRegistry.dispatch ──► tools
                                                ▼                         └── Tracer (data/traces/*.jsonl)
                                            TurnResult
```

| File | What it does |
|---|---|
| `harness/client.py` | The only code that calls the API: model, thinking, effort, refusal fallback |
| `harness/loop.py` | The agent loop |
| `harness/tools.py` | Tool registry. Pydantic models generate the schemas and validate inputs. Errors come back as outcomes, not exceptions. |
| `harness/trace.py` | JSONL log. Every request carries the entire transcript. |
| `harness/session.py` | One conversation: prompt, tools, tracing, transcript. Both interfaces use it. |
| `harness/demo.py` | Scripted stand-in for Claude, used by `--demo` |
| `tools/basics.py` | Facts the model can't know: today's date and the household profile |
| `cli.py`, `web/` | The two interfaces. Neither contains any agent logic. |

## The loop, line by line

```python
for iteration in range(1, max_iterations + 1):
```
**A `for` loop, not `while True`.** The cap is built into the loop's shape, so a confused model can't spin forever, whatever it asks for.

```python
    response = await client.create(system=system, messages=messages, tools=registry.definitions())
```
**Send the whole conversation every time.** The API keeps nothing between calls. The transcript panel shows exactly what goes out. `registry.definitions()` is identical on every call; a stable prefix matters for caching in Stage 3.

```python
    if response.content:
        messages.append({"role": "assistant", "content": response.content})
```
**Append the response exactly as it arrived.** Don't extract the text and rebuild the message. The content includes `thinking` blocks with signatures, and the API checks that they come back unchanged. The one exception is empty content (possible on a refusal), which is skipped because the API rejects empty messages.

```python
    text = "".join(block.text for block in response.content if block.type == "text")
    if response.stop_reason != "tool_use":
        return TurnResult(text, response.stop_reason, iteration)
```
**The stop reason decides what happens next, not the content.** A response can contain text and still be waiting on tools ("Let me check…" plus a `tool_use`). Only `stop_reason == "tool_use"` means "run tools and call me again". Every other reason (`end_turn`, `max_tokens`, `refusal`) ends the turn, and the interface explains it.

```python
    results = []
    for block in response.content:
        if block.type == "tool_use":
            outcome = await registry.dispatch(block.name, block.input)
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": outcome.content, "is_error": outcome.is_error})
    messages.append({"role": "user", "content": results})
```
**Tool results go back in one user message.** Several parts of this matter:

- **Matching ids.** Each result names the `tool_use` it answers, so order and ids must match.
- **One message.** Splitting the results across several messages teaches the model to stop calling tools in parallel.
- **Errors are results.** `dispatch` never raises; failures come back with `is_error: true`, and the model decides what to do next.
- **Tools run one at a time.** That's fine for read-only tools. Stage 6 revisits which tools are safe to run concurrently.

```python
return TurnResult(text, "max_iterations", max_iterations)
```
**Hitting the cap.** Here the model still wanted tools. Their results were already appended, so every `tool_use` has its `tool_result`, and the next user message continues the conversation cleanly.

## Things to try

| Experiment | What to look for |
|---|---|
| Ask "What should I cook tonight?" and open the Transcript tab | 4 messages: your text, Claude's `tool_use`, your code's `tool_result`, Claude's answer |
| Compare `in` for call 1 and call 2 in the Trace tab | Call 2 is bigger because it resends call 1's content plus the tool results |
| Delete the `messages.append({"role": "user", "content": results})` line and ask again | The API rejects the request: a `tool_use` without a `tool_result` |
| Comment out the `get_today` registration in `tools/basics.py` | The model guesses the date or asks you, because it can't know |
| Change `read_profile`'s docstring to `"Gets data."` | Whether Claude still thinks to call it when you ask for a dinner idea |
| `MEAL_AGENT_MAX_ITERATIONS=1 uv run meal-agent-web` | The turn stops after one call with the iteration-cap note |
