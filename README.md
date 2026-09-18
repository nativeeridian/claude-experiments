# LLM-Native Analytics Framework

A reference model for delivering analytics and insights with an LLM as the delivery mechanism: on-demand answers, on-demand artifacts, and reusable artifact templates, connected to disparate systems — a warehouse such as Snowflake, operational systems, and the raw files that live outside the schema.

Built to demonstrate a pattern any organization can adopt, large or small.

## Read it online

The whole thing is published as a static site from `docs/` — two runnable demos plus the three written documents, readable in any browser with nothing to install:

**https://nativeeridian.github.io/claude-experiments/**

> **One-time setup:** GitHub Pages has to be switched on for this repo before that link resolves.
> Go to **Settings → Pages**, set **Source: Deploy from a branch**, choose the branch and the **`/docs`** folder, and save. The first build takes a minute or two.

## Contents

| | What it is | Who it's for |
|---|---|---|
| [`demo/question-to-artifact.html`](demo/question-to-artifact.html) | **Executive demo** — the short version. One idea (Snowflake owns the number, the model owns the story), three worked requests with the Snowflake SQL and MCP calls behind each, and the six components you actually build. | Senior leadership |
| [`demo/insight-stack-demo.html`](demo/insight-stack-demo.html) | Full demo — five worked examples including a refusal, with tool traces and provenance blocks on every artifact. | Practitioners |
| [`docs/02-executive-summary.md`](docs/02-executive-summary.md) | **The Five-Layer Insight Stack** in plain terms, with the actual technology named, honest cost, a 90-day path, and how you'd know it's working. | Senior leadership |
| [`docs/01-research-landscape.md`](docs/01-research-landscape.md) | How organizations are doing this today — four architectural patterns, measured accuracy results, what MCP is and isn't, standards, documented security failures, evaluation practice. Sourced throughout. | Architects |
| [`docs/03-reference-architecture.md`](docs/03-reference-architecture.md) | The build specification: semantic contract fields, MCP server inventory, artifact template schema, eval harness, security controls, and adoption paths by org size. | Implementation team |

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

## Building the site

The files in `demo/` are authored as Claude Artifact fragments — no `<!doctype>`, `<html>` or `<body>`, because claude.ai supplies that wrapper when the artifact is published. The build step adds an equivalent wrapper plus link-preview metadata so the same pages stand alone on any static host:

```bash
node tools/build-site.js     # demo/*.html  ->  docs/exec-demo.html, docs/full-demo.html
```

Re-run it after editing anything in `demo/`, and commit the regenerated files in `docs/`. No dependencies, no build tooling.

Both demos include a live lane that asks Claude a question of your own. That only works on the claude.ai-hosted copies; on the static site it switches itself off and says so, and the worked examples run normally either way.

## Provenance of the figures

Meridian Industrial Supply is fictional and every number in the demos is synthetic, shaped to be realistic for a mid-market industrial distributor. The architecture, the products named and the research findings are real, and the research document cites its sources.
