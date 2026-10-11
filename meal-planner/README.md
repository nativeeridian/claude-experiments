# Meal planner agent

A chat agent that plans a two-person household's weekly dinners and leftover lunches. One person eats meat and has health and fitness goals. The other is lacto-ovo vegetarian. Plans have to fit the time actually available each night.

## Design docs

- [`docs/spec/good-week.md`](docs/spec/good-week.md): what a good plan is. These rules drive the validators and the evals.
- [`docs/spec/sample-conversations.md`](docs/spec/sample-conversations.md): how the agent should feel to use, and the requirements those conversations imply.
- [`docs/decisions/`](docs/decisions/): design decision records.

The code arrives stage by stage: the agent loop, domain tools, short-term memory, long-term memory, MCP, the harness, evals, vector recall, and a web chat.
