# Meal planner agent

A chat agent that plans a two-person household's weekly dinners and leftover lunches. One person eats meat and has health and fitness goals. The other is lacto-ovo vegetarian. Plans have to fit the time actually available each night.

## Design docs

- [`docs/spec/good-week.md`](docs/spec/good-week.md): what a good plan is. These rules drive the validators and the evals.
- [`docs/spec/health-baseline.md`](docs/spec/health-baseline.md): health rules that apply to both people. The agent reads them but can't edit them.
- [`docs/spec/sample-conversations.md`](docs/spec/sample-conversations.md): how the agent should feel to use, and the requirements those conversations imply.
- [`docs/decisions/`](docs/decisions/): design decision records.

## Running locally

1. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/).** uv also installs Python for you.
2. **Create an Anthropic API key** at [console.anthropic.com](https://console.anthropic.com). API usage is billed separately from a Claude.ai subscription, so the API account needs credits.
3. **Make the key available to your shell:**
   - macOS or Linux: `export ANTHROPIC_API_KEY="sk-ant-..."`
   - Windows PowerShell: `$env:ANTHROPIC_API_KEY="sk-ant-..."`

   Never commit the key.
4. **Run the warm-up exercise** from this directory:

   ```
   uv run --with anthropic python exercises/01_first_call.py
   ```

## Build stages

The code arrives stage by stage: the agent loop, domain tools, short-term memory, long-term memory, MCP, the harness, evals, vector recall, and a web chat.
