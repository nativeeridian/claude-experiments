# 0004: The agent loop

- **Status:** Accepted
- **Date:** 2026-11-18

## Context

The agent loop is the core of the harness. It calls the model, runs the tools the model asks for, sends the results back, and repeats until the model is done. Four choices shape it, and they are hard to change once tools and memory are built on top.

## Decisions

### 1. Async from the start

The MCP client (Stage 5) and the web chat (Stage 9) both need async code. Writing the loop and tools as async now costs a few keywords. Converting later would mean a refactor across every tool.

### 2. Tool schemas are generated from Pydantic models

Each tool has one Pydantic model for its arguments. That one model does two jobs:

- it produces the JSON schema Claude sees;
- it validates the input Claude sends back.

Because both come from the same model, the schema and the validation can't drift apart. `/tools` shows the generated schemas exactly as Claude receives them.

### 3. Tool errors go to Claude and to the user

A tool can fail in three ways: an unknown tool name, input that fails validation, or an exception inside the tool. In every case the registry returns a `tool_result` with `is_error: true`, so Claude can retry or work around the problem. The chat also prints a short red line. This follows the "notify" preference from decision 0001.

The registry never raises. Error handling sits in one place, not in every tool.

### 4. At most 10 model calls per user message

Planning a week should take roughly 4–8 calls, because tools run in parallel within a call. The cap stops a confused loop before it gets expensive. It is configurable with `MEAL_AGENT_MAX_ITERATIONS`.

When the cap is hit while tools are pending, the loop still records their results before stopping. Every `tool_use` needs a matching `tool_result`, or the next request is rejected.

## Supporting choices

These are plumbing choices, kept separate from the four decisions above:

- **`ModelClient` protocol.** The loop depends on a one-method protocol, not on the SDK. This makes three things possible:
  - tests swap in a scripted fake;
  - tracing wraps the real client;
  - later stages can add compaction and streaming without touching the loop.
- **Tracing is a wrapper, not loop code.** `TracingModelClient` and a registry listener log everything. Logging is a cross-cutting concern, and keeping it out of the loop keeps the loop readable.
- **Frozen system prompt.** The system prompt is read once per session and never edited mid-session. Stage 3 explains why this matters for caching and thinking.
- **Fallbacks are on.** Requests send `fallbacks="default"` (beta `server-side-fallback-2026-07-01`). If the model declines, the API retries on a fallback model within the same call.
- **Effort is set explicitly** to `medium`, the model's current default, so a change in the default can't silently change behaviour.

## Consequences

- **Tools must be async.** Every tool is an `async def`, even ones that don't wait on anything.
- **Docstrings are part of the interface.** A tool without a docstring fails to register, because its docstring is the description Claude reads.
- **Hitting the cap isn't the end.** A turn that hits the cap leaves the transcript ending in tool results. The next user message continues the same conversation, and the API merges the consecutive user messages.
