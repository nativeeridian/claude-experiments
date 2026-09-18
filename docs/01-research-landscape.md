# How organizations are actually delivering LLM-powered analytics

**Landscape research — September 2026**
Scope: what is in production today, what the measured results are, which architectures have converged, and where the remaining gaps sit.

---

## 1. What changed in the last eighteen months

Three things moved at once, and together they made this problem tractable in a way it wasn't in 2024:

1. **Frontier model SQL competence crossed a usable threshold.** On a repeatable insurance-analytics benchmark, raw text-to-SQL accuracy went from 32.7% (GPT-4, 2023) to 64.5% (Claude Sonnet 4.6 and GPT-5.3 Codex, 2026) against the *same* normalized schema — and to 84–90% once three straightforward join models were added on top of that schema.
2. **A wire protocol won.** MCP (Model Context Protocol) became the default way an agent discovers and calls data tools. Snowflake, Databricks, dbt Labs, Cube, AtScale, Metabase, Power BI and dozens of others now ship or host MCP servers. The November 2025 spec revision formalized OAuth 2.1 for remote servers, which is what made enterprise security teams willing to sign off.
3. **A semantic standard landed.** The Open Semantic Interchange specification hit v1.0 on 27 January 2026 under an Apache-2 licensed repo, backed by 33+ organizations including Snowflake, Databricks, dbt Labs, Qlik, AtScale, Salesforce, Alation and Atlan. It was donated to the Apache Software Foundation and entered the incubator as **Apache Ossie (incubating)** on 10 July 2026 — the acronym collided with the Open Source Initiative; the spec itself is unchanged.

The net effect: the hard part is no longer "can the model write SQL." It is "does the model know what your business means by *revenue*, and can you prove what it did."

---

## 2. The central finding: the bottleneck is semantics, not the model

This is the single most important result in the literature, and it is now well-measured rather than asserted.

### 2.1 Where text-to-SQL actually breaks

- **Roughly 81% of text-to-SQL errors are schema- or semantic-level**, not syntax. The model guesses what a column or a join means. Syntax errors — the failure mode people expect — are the minority.
- **Unaided, on real enterprise schemas, reported production accuracy runs 10–31%.** Not because the SQL is malformed, but because production warehouses are full of ambiguous table structures, undocumented relationships, and encoded status values that appear nowhere in training data.
- **Schema churn degrades it further.** When tables are added, split, or merged, execution accuracy has been measured dropping by up to 24 points.
- **Terms are genuinely contested inside the company.** "Revenue," "active customer," and "margin" mean different things to finance, sales and ops. The warehouse does not record which one the asker meant, so the model picks one.

### 2.2 The measured lift from a semantic layer

dbt Labs' 2026 benchmark (11 questions × 20 repetitions, ACME Insurance dataset, four configurations):

| Configuration | Claude Sonnet 4.6 | GPT-5.3 Codex |
|---|---|---|
| 2023 baseline (GPT-4), text-to-SQL | 32.7% | — |
| 2023 baseline (GPT-4), semantic layer | 60.5% | — |
| Normalized schema, text-to-SQL | 64.5% | 64.5% |
| Normalized schema, semantic layer | 72.7% | 72.7% |
| **+3 join models, text-to-SQL** | **90.0%** | **84.1%** |
| **+3 join models, semantic layer** | **98.2%** | **100.0%** |
| Questions *within* semantic layer scope | **100.0%** | **100.0%** |

A separate paired benchmark across three frontier models found that adding even a small semantic context document lifted query accuracy by **17–23 percentage points**.

Two conclusions the data supports:

- **Modeling helps both approaches.** Three added join models moved text-to-SQL by 25 points. Data modeling is not made obsolete by AI; it is the highest-leverage AI investment available.
- **Within a modeled scope, the answer is deterministic.** dbt's MetricFlow compiles the query itself. The model's only job is picking the right metric and dimensions; it cannot produce a bad join or a wrong aggregation. As the benchmark puts it: *"if it picks the right metric and dimensions, the query is guaranteed to be correct."*

### 2.3 The asymmetry that actually matters to an executive

The accuracy numbers are less important than *how each approach fails*.

- **Text-to-SQL fails silently.** It "will cheerfully give you a wrong number." A plausible, well-formatted, confidently-narrated wrong number, in a board deck.
- **A semantic layer fails loudly.** It never returns invalid data; when the question is outside its modeled scope it returns an error instead of a guess.

The benchmark shows this cleanly: on questions requiring more entity hops than the model covered, text-to-SQL scored 70–100% and the semantic layer scored **0%** — because it refused. That 0% is the desirable behavior. An analytics system that says "I can't answer that, here's why" is trustworthy; one that is right 90% of the time and gives no signal about which 10% is not usable for decisions that matter.

**Design implication:** the framework must route finance-grade questions through governed definitions and let exploratory questions run free — with the output visibly labeled as to which path it took.

---

## 3. The four architectural patterns in the market

Everything shipping today is a variation on one of four patterns.

### Pattern A — Warehouse-native agents
*Snowflake Cortex Analyst / Cortex Agents; Databricks AI/BI Genie and Genie One*

Semantics, retrieval, execution and governance all live inside the data platform. Snowflake's Cortex Analyst reads a **semantic model file** (capped at 1 MB) that carries business process definitions, metric logic and synonyms — explicitly because a bare schema lacks that knowledge. Cortex Agents orchestrate across Cortex Analyst (structured, text-to-SQL) and Cortex Search (unstructured, semantic search), and can combine both in one answer. Databricks Genie generates SQL against Unity Catalog governed tables with an inspectable-SQL trust step; the 2026 Genie One release added routing across governed analytical assets and connected knowledge.

- **Strengths:** governance is inherited from the platform, not reimplemented. Lowest integration burden if you are already all-in.
- **Watch-out:** the Snowflake-**managed** MCP server supports semantic **views**, not semantic **models** — an easy and expensive assumption to get wrong when planning. The open-source `Snowflake-Labs/mcp` server covers the wider surface.
- **Lock-in:** high. Semantics are expressed in platform-specific artifacts.

### Pattern B — BI-suite copilots
*Power BI Copilot (Microsoft Fabric), Tableau Next / Tableau Agent (Agentforce), Looker + Gemini, Tableau Pulse, ThoughtSpot*

AI bolted onto an incumbent BI suite, reusing the existing semantic model (DAX, LookML, Tableau data sources). Power BI Copilot translates natural language to DAX and narrates report pages; multi-turn conversation went GA in April 2026. Tableau Next launched March 2026 as an agentic platform inside Salesforce's Agentforce ecosystem.

- **Strengths:** zero new governance surface; reuses a decade of modeling; users are already there.
- **Watch-out:** answers are trapped inside the BI tool. Weak at anything off-model, and weak at the hybrid structured + unstructured question.
- **Lock-in:** high, but you already paid it.

### Pattern C — Semantic-layer-first, agent-agnostic
*dbt MCP server, Cube, AtScale, Kyvos, Omni, Lightdash*

A vendor-neutral semantic layer is the contract; any agent consumes it over MCP. The dbt MCP server exposes `list_metrics`, `get_dimensions`, `query_metrics`, plus lineage and metadata tools (`get_all_models`, `get_model_details`, `get_model_parents`, `get_mart_models`). Cube's architecture is the clearest published reference: **semantic model layer** (metrics, dimensions, joins, access policies, owned by the data team) → **query compilation layer** (governance applied at compile time) → **agent interface layer** (MCP, SQL, REST, GraphQL).

The critical governance property in this pattern: **row-level and role-based rules are compiled into the generated SQL**, so the agent structurally cannot query data the user isn't entitled to see. This is materially stronger than filtering results after the fact.

- **Strengths:** portable across warehouses and agents; strongest governance story; Apache Ossie makes the definitions themselves portable.
- **Watch-out:** you must actually do the modeling. There is no shortcut.
- **Lock-in:** lowest.

### Pattern D — AI-native agent host
*Claude with MCP connectors + Agent Skills; custom agents on the Claude Agent SDK or equivalents*

The agent is the product surface; data platforms are connected as tools. The published pattern is three layers: **Skills** (reusable domain expertise — how to build a DCF, how to trace a GL break, how to write the QBR), **connectors** (governed, real-time MCP access to systems), and **subagents** (delegated specialist work). Skills matter here because they are where *analytical method* lives — as distinct from *data semantics*, which live in the semantic layer.

- **Strengths:** the only pattern that natively spans structured warehouse data, loose files, documents, tickets and SaaS systems in a single answer. Also the only one whose output is not constrained to a chart in a BI canvas — it can produce a memo, a model, a deck, a working document.
- **Watch-out:** you own the orchestration, the evals and the audit trail. Nothing is inherited.
- **Lock-in:** low on data, moderate on agent tooling.

### Which to pick

Most serious 2026 deployments are **C + D**: a governed semantic layer as the source of numeric truth, an agent host as the experience and artifact layer, MCP as the seam. A or B are the right answer when the organization is genuinely single-platform and the questions stay inside that platform. The demo framework in this repo is deliberately C + D, because that is the pattern that generalizes to "any organization, big or small."

---

## 4. MCP is the connective tissue — and here is what it is not

MCP standardizes *how* context is exchanged. It does not standardize *what the context means*. An MCP server that exposes raw table schemas is raw text-to-SQL with extra steps, and it will inherit all of §2's failure modes.

The practical distinction:

| | Schema-exposing MCP server | Semantics-exposing MCP server |
|---|---|---|
| What the agent sees | tables, columns, types | named metrics, dimensions, valid grains, descriptions |
| What the agent emits | SQL it composed | a structured request naming governed objects |
| Who writes the SQL | the model | a deterministic compiler (MetricFlow, Cube, Cortex) |
| Failure mode | silently wrong | explicit refusal |
| Access control | whatever the connection's role allows | compiled into the query |

This table is the single most useful artifact to put in front of a data platform team, because "we already have an MCP server" is currently the most common false-positive signal of readiness.

---

## 5. The standard: Apache Ossie (formerly OSI)

- **v1.0 released 27 January 2026**, Apache-2 licensed, on GitHub.
- Defines a **vendor-neutral, extensible model for semantic constructs**: data sets, metrics, dimensions, relationships and contexts.
- **33+ member organizations**: Snowflake, Databricks, dbt Labs, Qlik, AtScale, Salesforce, Alation, Atlan, Coalesce, Collate, JetBrains, Lightdash, Credible and others.
- Donated to the Apache Software Foundation; entered the incubator as **Apache Ossie (incubating) on 10 July 2026**.
- The problem it names is exactly the one above: *a lack of shared meaning*, with business logic trapped in proprietary systems and rebuilt repeatedly.

**Why a leader should care:** this is the difference between defining "net revenue" once and defining it in Power BI, in Looker, in the warehouse, in the finance model, and again for every AI tool. Ossie alignment is the hedge that stops the semantic layer from becoming the next thing you are locked into.

---

## 6. The data that is not in the warehouse

Every organization has consequential data outside the schema: the freight rebate spreadsheet on SharePoint, the signed contract PDFs, the support ticket backlog, the vendor price list emailed every quarter. This is usually where the *interesting* half of an answer lives, and it is what most BI copilots simply cannot reach.

Approaches in production:

- **Platform-native hybrid retrieval.** Snowflake Cortex Search (unstructured semantic search) alongside Cortex Analyst (structured), orchestrated by a Cortex Agent that selects the source per question and merges results when a question spans both.
- **Unstructured ETL into the lakehouse.** Unstructured.io-style pipelines (high-fidelity PDF/HTML extraction, OCR, table preservation, smart chunking, 30+ connectors) landing into a vector index the agent can query. Databricks publishes a full reference pipeline for this.
- **File-level SQL.** DuckDB / MotherDuck for querying spreadsheets, CSVs and Parquet in place, with the vector store alongside for semantic retrieval — the agent gets both `SQL execution` and `similarity search` as tools. Research work (NeuSym-RAG, and deep LM integration into DuckDB) points the same direction: hybrid neural-symbolic retrieval beats either alone on document QA.

**The governance rule that matters more than the tooling choice:** an ungoverned file must never silently override a governed metric. In practice that means three states for any input, carried through to the rendered output:

1. **Governed** — defined in the semantic layer, certified, auditable.
2. **Referenced** — a file or document read at answer time, cited by name, version and timestamp, visibly labeled as un-certified.
3. **Quarantined** — reachable but not usable for a stated decision class (e.g. anything going to the board).

And a standing promotion path: any *referenced* source that shows up in three consequential answers is a backlog item to model properly. That single rule is what stops the spreadsheet layer from quietly becoming the system of record.

---

## 7. Security and governance: what has actually gone wrong

MCP's risk surface is real and documented, and a framework that ignores it will not pass review.

- **Indirect prompt injection is the dominant threat.** Malicious instructions hidden in retrieved content — a support ticket, a PDF, a web page, a document — manipulate agent behavior. The attacker never touches the prompt; they influence what the agent *reads*.
- **The canonical incident:** the Supabase MCP case, where the server ran with a `service_role` that bypassed row-level security, and an injection planted in a support ticket caused the agent to run SQL and leak tokens. The agent behaved as designed; the *privilege* was the defect.
- **Token passthrough is an anti-pattern.** Forwarding a raw user access token to a downstream API means the downstream service cannot distinguish the server from the user, logs attribute actions to the wrong principal, and a stolen token gains extra reach.
- **OAuth 2.1 is the standard** for remote MCP servers as of the November 2025 spec.
- **Full-chain delegation is the model to reason in:** who the user is, which client is acting, which server is called, what token is used, what resource is touched, and whether that tool action is authorized *in that context*.

The five controls that follow from this, in priority order:

1. **Never run the data connection as a superuser.** The agent connects as the asking human, or as a narrowly-scoped service principal with RLS enforced. Compile-time access control (Pattern C) is the strongest available form.
2. **Treat all retrieved content as untrusted input**, never as instructions. Documents, tickets and files are data.
3. **No token passthrough.** Token exchange at every hop, with the audience bound to the destination.
4. **Log the whole trace** — question, tools called, arguments, definitions resolved, rows returned, artifact produced. This is the audit trail *and* the eval corpus.
5. **Human approval gates on write actions.** Reads can be autonomous; anything that changes a system is confirmed.

---

## 8. Trust engineering: how teams evaluate these systems

The teams succeeding at this treat the analytics agent as a tested software system, not a demo.

- **A golden question set is the foundation.** Twenty real questions pulled from production or pilot traffic, each with the correct answer written by a human who understands the workflow. Coverage guideline in use: **~60% happy path, ~30% edge cases, ~10% adversarial** (including questions that *should* be refused).
- **Three layers of testing**, because no single check catches how agents fail:
  1. **Unit tests** on the deterministic parts — tools, parsers, retrieval.
  2. **Eval suites** over representative tasks with pass/fail criteria — golden-set regressions for known failures.
  3. **LLM-as-judge** for open-ended quality a fixed answer can't capture (is the narrative actually responsive, are the caveats right).
- **Diagnose by reading traces.** Roughly **80% of failures cluster into three to five buckets.** Categorize every failure; fix the bucket, not the instance.
- **A published reference implementation exists:** `datacult/dbt-agent-trust` — a working data agent on the dbt semantic layer with a layered evaluation framework, and an honest treatment of the interpretation problems automated evaluation cannot solve.

**The organizational point:** the golden set is the contract between the data team and the business. It is how "do you trust it?" becomes a number that moves.

---

## 9. The underserved layer: artifacts, not answers

Nearly every product in §3 stops at *chat plus a chart*. Natural language querying, auto-generated insights, anomaly detection and forecasting are now described as "standard expectations rather than differentiators."

What is *not* solved, and where the opportunity sits:

- **The unit of business value is a document, not a row.** A margin bridge with three recommendations, a QBR pack, a variance memo with the exceptions already investigated, a board appendix. People don't want to query; they want the thing they were going to build from the query.
- **Templates make generated output governable.** A free-form generated report is unreviewable. A *template* — fixed sections, fixed metric definitions, required provenance block, required caveats section — is reviewable once and then reusable forever. This is the mechanism that makes generative output safe for recurring executive consumption.
- **The realistic operating model is mixed, and the market has already converged on it:** most teams in 2026 run a question-and-answer or auto-generate tool for everyday questions, and keep a small set of governed dashboards for finance-grade reporting. Design for both from day one; do not pitch replacing the dashboards.

---

## 10. The market reality check

Worth stating plainly, because it sets the bar for what "success" has to mean:

- ~9 in 10 organizations use AI in at least one function; **only ~6% capture significant enterprise value**, and an estimated **80–95% of AI projects fail to deliver promised return**.
- **79% of organizations report challenges adopting AI** — a double-digit increase year over year; 59% invest $1M+/year, **29% see significant returns**.
- Self-service BI, the direct predecessor of this idea, has an **adoption rate below 20%**, and Gartner has long put BI project failure at **70–80%**. A **45% failure rate** is associated specifically with rolling out self-service *before* governance basics (metric definitions, RBAC) exist.
- **60% of leaders report a data literacy skills gap**, while 88% call basic data literacy essential. Organizations that pair AI investment with structured upskilling are **twice as likely to report significant positive ROI (42% vs 21%)**.

Read together, these say something specific: *the failure mode of this project category is not technical.* It is shipping a capable system into an organization that has no agreed definitions, no governance, and no training — which is precisely the history of self-service BI repeating. The framework must therefore treat the semantic contract and the golden question set as first-class deliverables, not as documentation.

---

## 11. What this implies for the framework

Ten design commitments, each traceable to a finding above:

1. **Semantics are the product.** Model the metrics before connecting the model. (§2)
2. **Two lanes, visibly labeled.** Governed lane for decisions of record; exploratory lane for everything else. Never let the user confuse them. (§2.3, §9)
3. **Refusal is a feature.** "I can't answer that, and here's what it would take" ships in v1. (§2.3)
4. **MCP is the seam, not the solution.** Expose semantics over MCP, never raw schemas. (§4)
5. **Write definitions to a portable standard.** Apache Ossie alignment. (§5)
6. **Off-schema data is in scope from day one**, with governed / referenced / quarantined labeling and a promotion path. (§6)
7. **Least privilege, no passthrough, all content untrusted, everything logged.** (§7)
8. **A golden question set is a deliverable**, and the eval score is the adoption metric. (§8)
9. **The output is an artifact from a template**, not a chat reply. (§9)
10. **Ship with enablement**, or accept the 20% adoption ceiling. (§10)

---

## Sources

**Semantic layers and accuracy**
- [Semantic Layer vs. Text-to-SQL: 2026 Benchmark Update — dbt Developer Blog](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)
- [Semantic Layers for Reliable LLM-Powered Data Analytics: A Paired Benchmark — arXiv](https://arxiv.org/pdf/2604.25149)
- [Semantic Layer for AI Agents (2026) — Cube](https://cube.dev/articles/semantic-layer-for-ai-agents-2026)
- [Why text-to-SQL fails — Omni Analytics](https://omni.co/blog/why-text-to-sql-fails)
- [Text-to-SQL for Enterprise: Metric Drift and Context Layer — Atlan](https://atlan.com/know/ai-agent/data-for-ai/text-to-sql-for-enterprise/)
- [Semantic Layer for AI: Why LLM Analytics Fail Without One — Knowi](https://www.knowi.com/blog/semantic-layer-for-ai/)

**MCP and platform implementations**
- [Semantic Layer + MCP: The Architecture Behind Trustworthy AI Analytics — Polar](https://www.polaranalytics.com/post/mcp-semantic-layer-ai-analytics)
- [Introducing the dbt MCP Server — dbt Developer Blog](https://docs.getdbt.com/blog/introducing-dbt-mcp-server)
- [dbt-labs/dbt-mcp — GitHub](https://github.com/dbt-labs/dbt-mcp)
- [Cortex Analyst — Snowflake Documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst)
- [Snowflake-managed MCP server — Snowflake Documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-mcp)
- [Snowflake-Labs/mcp — GitHub](https://github.com/Snowflake-Labs/mcp)
- [MCP Servers on Snowflake Unify and Extend Data Agents — Snowflake](https://www.snowflake.com/en/blog/mcp-servers-unify-extend-data-agents/)
- [AI/BI and Genie release notes 2026 — Microsoft Learn](https://learn.microsoft.com/en-us/azure/databricks/ai-bi/release-notes/2026)
- [Future-Proofing Enterprise AI: AtScale's MCP Integration](https://www.atscale.com/blog/enterprise-ai-mcp-semantic-layer/)
- [MCP Servers and the Semantic Layer Gap — TimeXtender](https://www.timextender.com/blog/product-technology/mcp-servers-and-the-semantic-layer-gap-what-data-teams-need-to-know)

**Standards**
- [Open Semantic Interchange Specification Finalized — Snowflake](https://www.snowflake.com/en/blog/open-semantic-interchanges-specs-finalized/)
- [Open Semantic Interchange — project home](https://open-semantic-interchange.org/)
- [Qlik Joins Snowflake-Led Open Semantic Interchange](https://www.qlik.com/blog/qlik-joins-snowflake-led-open-semantic-interchange-to-bring-consistent)

**Off-schema and unstructured data**
- [Build an unstructured data pipeline for RAG — Databricks](https://docs.databricks.com/aws/en/agents/tutorials/ai-cookbook/quality-data-pipeline-rag)
- [Effortless ETL for Unstructured Data with Unstructured.io & MotherDuck](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/)
- [Multi Source RAG: Enterprise Pipeline for All Filetypes — Unstructured](https://unstructured.io/blog/everything-from-everywhere-all-at-once-enterprise-rag-with-multiple-sources-and-filetypes)
- [NeuSym-RAG: Hybrid Neural Symbolic Retrieval — arXiv](https://arxiv.org/pdf/2505.19754)
- [Beyond Quacking: Deep Integration of Language Models and RAG into DuckDB — arXiv](https://arxiv.org/pdf/2504.01157)

**Security and governance**
- [MCP Security: Risks, Real Incidents & Controls (2026) — Checkmarx](https://checkmarx.com/learn/mcp-security-risks-real-world-incidents-and-security-controls/)
- [MCP Prompt Injection: Why Your AI Agents Can't Defend Against It Alone — Obot](https://obot.ai/blog/mcp-prompt-injection-ai-agent-security/)
- [Agentic MCP Security Best Practices — Cloud Security Alliance](https://labs.cloudsecurityalliance.org/agentic/agentic-mcp-security-best-practices-v1/)
- [MCP Security Risks 2026: Tool Poisoning and Data Leakage — Colrows](https://colrows.com/blogs/mcp-security-risks-tool-poisoning-data-leakage/)

**Evaluation and trust**
- [datacult/dbt-agent-trust — GitHub](https://github.com/datacult/dbt-agent-trust)
- [Golden Datasets for AI Evals: Design, Coverage, and Trade-offs](https://aisystemswithharsh.substack.com/p/golden-datasets-for-ai-evals-design)
- [What is AI Agent Evaluation? — Databricks](https://www.databricks.com/blog/what-is-agent-evaluation)

**Agent architecture**
- [MCP connector — Claude Platform Docs](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector)
- [Agents for financial services — Anthropic](https://www.anthropic.com/news/finance-agents)
- [Structuring Agents, Skills, and MCPs: Best Practices from Anthropic](https://medium.com/intuitionmachine/structuring-agents-skills-and-mcps-best-practices-from-anthropic-9312849ccea6)

**Market and adoption**
- [Enterprise AI adoption in 2026 — WRITER](https://writer.com/blog/enterprise-ai-adoption-2026/)
- [The State of AI in the Enterprise 2026 — Deloitte](https://www.deloitte.com/us/en/what-we-do/capabilities/applied-artificial-intelligence/content/state-of-ai-in-the-enterprise.html)
- [Why Self-Service BI Fails in Large Enterprises — Perceptive Analytics](https://www.perceptive-analytics.com/why-self-service-bi-fails-in-large-enterprises/)
- [The State of Data & AI Literacy in 2026 — DataCamp](https://www.datacamp.com/blog/the-state-of-data-and-ai-literacy-in-2026-definitions-statistics-and-the-ai-skills-gap)
- [Conversational BI Tools 2026: Scored and Compared — Colrows](https://colrows.com/blogs/conversational-bi-tools/)
- [What is Generative Business Intelligence? — SG Analytics](https://www.sganalytics.com/blog/generative-business-intelligence/)
