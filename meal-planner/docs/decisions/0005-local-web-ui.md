# 0005: A local web UI now; hosting later

- **Status:** Accepted
- **Date:** 2026-11-18

## Context

The terminal chat works, but a web page is easier to use and can show the harness at work as it runs. A private Vercel deployment was considered. The original plan put the web chat at Stage 9.

## Decisions

### 1. A local web app, brought forward from Stage 9

A FastAPI server with one chat page, started with `uv run meal-agent-web`.

- It binds to `127.0.0.1` by default. The server spends the API key on behalf of anyone who can reach it.
- Beside the chat, an inspector shows four tabs:
  - **Trace:** each model call and tool call.
  - **Transcript:** the exact `messages` sent to the API.
  - **Profile:** the household profile the agent reads.
  - **Tools:** the definitions Claude receives.

### 2. One harness, two interfaces

`ChatSession` (`harness/session.py`) holds the conversation, tools, prompt and tracing. Both the terminal and the web server drive it, so neither interface contains agent logic. A turn's events reach the page as server-sent events while it runs.

### 3. Demo mode

`--demo` swaps the model for a scripted client. Everything else is real: the loop, the tools, the transcript and the trace. The UI can be tried without an API key, and the page labels demo replies clearly as scripted.

### 4. No Vercel deployment yet

Serverless hosting doesn't suit the agent as it stands:

- **Conversation state.** It lives in server memory, but serverless instances don't share memory between requests.
- **Long turns.** A planning turn can make several slow model calls, which runs into function time limits.
- **Storage.** The trace files, and later the memory files and database, need storage that persists.
- **The API key.** A public URL connected to the key needs reliable access protection.

## Options considered

- **Private Vercel deployment now.** Each problem above has a workaround: the browser holds the transcript, longer function limits, a hosted database, deployment protection. But building those workarounds would take time away from the agent itself.
- **Terminal only until Stage 9.** Rejected. The inspector panels make the loop, statelessness and tool use visible now, while those ideas are being learned.

## Consequences

- **No hosting work yet.** The web app runs on your own machine, and demo mode runs in any cloud session.
- **One session per server.** The server holds a single conversation, and "New chat" replaces it.
- **Revisit when** long-term memory is in a database (Stage 4). At that point a hosted deployment, on Vercel or a long-running host such as Fly.io or Render, becomes a matter of configuration rather than redesign.
