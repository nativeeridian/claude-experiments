# Meal planner agent

A chat agent that plans a two-person household's weekly dinners and leftover lunches. Both people have health and fitness goals. One eats meat; the other is lacto-ovo vegetarian. Plans have to fit the time actually available each night.

## Design docs

- [`docs/spec/good-week.md`](docs/spec/good-week.md): what a good plan is. These rules drive the validators and the evals.
- [`docs/spec/health-baseline.md`](docs/spec/health-baseline.md): health rules that apply to both people. The agent reads them but can't edit them.
- [`docs/spec/sample-conversations.md`](docs/spec/sample-conversations.md): how the agent should feel to use, and the requirements those conversations imply.
- [`docs/decisions/`](docs/decisions/): design decision records.
- [`docs/notes/`](docs/notes/): one note per build stage, covering what it adds, the key ideas, and experiments to try.

## Running locally

1. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/).** uv also installs Python for you.
2. **Create an Anthropic API key** at [console.anthropic.com](https://console.anthropic.com). API usage is billed separately from a Claude.ai subscription, so the API account needs credits.
3. **Store the key.** From this directory, run `cp .env.example .env` and put your key in `.env`. Git ignores `.env`; never commit the key.
4. **Install dependencies:** `uv sync`
5. **Run the tests:** `uv run pytest`. No API key is needed, because a scripted fake stands in for the model.
6. **Chat:** `uv run meal-agent`

The warm-up exercise needs the key exported in your shell. Run `export ANTHROPIC_API_KEY=...` first (Windows PowerShell: `$env:ANTHROPIC_API_KEY="..."`), then:

```
uv run --with anthropic python exercises/01_first_call.py
```

## Layout

| Path | What's there |
|---|---|
| `src/meal_agent/harness/` | The harness: client, loop, tools registry, tracing, system prompt |
| `src/meal_agent/tools/` | Domain tools the agent can call |
| `tests/` | Tests, with a scripted fake model client |
| `docs/notes/` | One design note per stage |
| `data/` | Personal runtime state: profile, traces. Git ignores it. |

## Build stages

The code arrives stage by stage: the agent loop, domain tools, short-term memory, long-term memory, MCP, the harness, evals, vector recall, and a web chat.
