# LLM-Native Analytics Framework

A reference model for delivering analytics and insights with an LLM as the delivery mechanism: on-demand answers, on-demand artifacts, and reusable artifact templates, connected to disparate systems — a warehouse such as Snowflake, operational systems, and the raw files that live outside the schema.

Built to demonstrate a pattern any organization can adopt, large or small.

## Contents

| Document | What it is | Who it's for |
|---|---|---|
| [`docs/01-research-landscape.md`](docs/01-research-landscape.md) | How organizations are doing this today — the four architectural patterns, measured accuracy results, MCP's real role, standards, security incidents, evaluation practice. With sources. | Practitioners, architects |
| [`docs/02-executive-summary.md`](docs/02-executive-summary.md) | **The Five-Layer Insight Stack** in plain terms, with the actual technology named, cost, a 90-day path, and how to tell it's working. | Senior leadership |
| [`docs/03-reference-architecture.md`](docs/03-reference-architecture.md) | The build specification: component specs, the semantic contract, MCP tool surface, template schema, eval harness, security controls, and three adoption paths by org size. | Implementation team |
| [`demo/insight-stack-demo.html`](demo/insight-stack-demo.html) | Interactive demo — a worked example on a fictional industrial distributor, showing all five layers producing real business artifacts. | Everyone |

## The model in one picture

```
L5  DELIVERY    Artifact templates → answer card · brief · report · watch
L4  REASONING   Agent host + Skills (method) + lane router
L3  MEANING     Semantic contract: metrics · dimensions · grains · policies
L2  ACCESS      MCP servers — one governed door per source
L1  SOURCES     Warehouse · operational systems · files · documents

   spines: TRUST (golden set · evals · provenance) · CONTROL (identity · audit)
```

## The load-bearing idea

The AI never decides what a metric *means*. It decides which agreed metric answers your question, gathers what else is needed — including from files that were never in the warehouse — and writes up the result as a finished artifact, with every number traceable to a definition someone owns.

When it can't answer, it says so. That refusal is the feature that makes the rest usable for decisions that matter.
