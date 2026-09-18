# Reference Architecture — build specification

Companion to `02-executive-summary.md`. This is the implementable version of the Five-Layer Insight Stack: component specs, contracts, tool surfaces, and the paths for three organization sizes.

---

## 0. Architecture at a glance

```
                 ┌──────────────────────────────────────────────────────┐
   TRUST         │  Golden question set · eval harness · trace log       │
   (spine)       │  provenance rendering · refusal policy                │
                 └──────────────────────────────────────────────────────┘
                 ┌──────────────────────────────────────────────────────┐
   CONTROL       │  Identity · least privilege · token exchange          │
   (spine)       │  untrusted-content handling · write approval gates    │
                 └──────────────────────────────────────────────────────┘

   L5  DELIVERY    Artifact templates → answer card · brief · report · watch
                          ▲
   L4  REASONING   Agent host + Skills (method) + orchestration + lane router
                          ▲
   L3  MEANING     Semantic contract: metrics · dimensions · grains · policies
                          ▲                        (Apache Ossie-aligned)
   L2  ACCESS      MCP servers — one governed door per source, OAuth 2.1
                          ▲
   L1  SOURCES     Warehouse · operational systems · files · documents
```

Data flows up. Authority flows down: L3 constrains what L4 may claim, L2 constrains what L4 may see, and the Control spine constrains both.

---

## 1. Layer 1 — Sources

Three classes, each with a different readiness path.

| Class | Examples | Made agent-ready by | Governance state |
|---|---|---|---|
| **Modeled** | warehouse marts, curated tables | semantic layer (L3) | Governed |
| **Operational** | CRM, ERP, ticketing, billing | vendor MCP server or REST wrapper | Referenced (read-only) |
| **Off-schema** | spreadsheets, PDFs, price lists, contracts | DuckDB for tabular; vector index + extraction for documents | Referenced or Quarantined |

### 1.1 Off-schema handling (the part most architectures omit)

**Tabular files.** Register a file-level query surface with **DuckDB** (or MotherDuck for a hosted shared catalog). DuckDB reads `.xlsx`, `.csv` and `.parquet` in place from object storage or a mounted share — no ingestion project. Expose it as a read-only MCP tool with an allowlisted path prefix.

**Documents.** Extraction → chunking → embedding → index. Use **Unstructured.io** or the platform equivalent (Databricks' published RAG pipeline, Snowflake Cortex Search) for high-fidelity PDF/HTML extraction with table preservation and OCR. Preserve `source_uri`, `page`, `version` and `last_modified` on every chunk — these become the provenance fields in L5.

### 1.2 The three-state labeling rule

Every fact that reaches an artifact carries exactly one state, and the state is rendered in the output:

- **Governed** — resolved through the semantic contract. Valid for decisions of record.
- **Referenced** — read at answer time from an operational system or a file. Cited with name, version and timestamp. Visibly un-certified.
- **Quarantined** — reachable but barred from a stated decision class (board, regulatory, external).

**Promotion trigger:** any *Referenced* source appearing in three consequential answers becomes a modeling backlog item. Without this rule, the spreadsheet layer silently becomes the system of record.

---

## 2. Layer 2 — Access

### 2.1 Server inventory (typical first domain)

| Server | Source | Mode | Auth | Notes |
|---|---|---|---|---|
| `warehouse-semantic` | dbt / Cube / Cortex | read | OAuth 2.1, user identity | **Primary.** Exposes metrics, not tables. |
| `warehouse-sql` | warehouse | read | OAuth 2.1, user identity | Exploratory lane only. Off by default for pilot users. |
| `crm` | Salesforce / HubSpot | read | OAuth 2.1 | Vendor server where available. |
| `tickets` | Zendesk / ServiceNow | read | OAuth 2.1 | High injection risk — see §7.3. |
| `files` | DuckDB over object store | read | service principal, path-allowlisted | Tabular off-schema. |
| `docs` | vector index | read | service principal, ACL-filtered | Document retrieval. |

### 2.2 Non-negotiables

- **No superuser connections.** The connection carries the asking user's identity, or a service principal scoped narrowly enough that its full reach is acceptable if compromised.
- **No token passthrough.** Exchange tokens at each hop with the audience bound to the destination. A raw user token forwarded downstream makes the log attribute actions to the wrong principal and gives a stolen token extra reach.
- **Every tool is read-only by default.** Write tools are separately declared and gated (§7.4).
- **Schema-exposing servers are not semantics-exposing servers.** An MCP server over raw tables is text-to-SQL with extra steps and inherits every failure mode in `01-research-landscape.md` §2.

---

## 3. Layer 3 — The semantic contract

### 3.1 Required fields per metric

Model to the **Apache Ossie** spec (v1.0, Jan 2026) so definitions stay portable. Whatever tool holds them, each metric carries:

| Field | Why it exists |
|---|---|
| `name` | Stable machine identifier, e.g. `gross_margin_pct` |
| `label`, `synonyms` | What people actually call it — drives correct resolution from natural language |
| `definition` | One sentence a business user would accept |
| `expression` | The computation, in the semantic layer's own syntax |
| `grain` | Valid time and entity grains; anything else is refused |
| `dimensions` | Legal slicing keys, with their own definitions |
| `owner` | A named person. Definitions need an editor, not a committee. |
| `certified` | Boolean. Uncertified metrics render with a visible badge. |
| `access_policy` | Row-level and role-level rules, compiled into the query |
| `caveats` | Known gotchas surfaced in every artifact that uses it |
| `version`, `effective_from` | Restatement history — why last quarter's number changed |

### 3.2 Scope discipline

Model the **20 questions leadership actually asks** — typically 15–30 metrics. Not the warehouse. A full-warehouse modeling program takes two years and gets cancelled at month nine.

### 3.3 The refusal contract

The semantic layer must be able to answer "no." Three refusal classes, each with distinct output copy:

| Class | Trigger | What the user is told |
|---|---|---|
| **Out of scope** | metric or dimension not modeled | what is missing, and what modeling it would take |
| **Out of grain** | requested grain not valid for the metric | which grains are available |
| **Out of grant** | user not entitled to the data | that the data exists and who to ask |

A refusal is a successful outcome and is logged as one. Systems that cannot refuse cannot be trusted with decisions of record.

---

## 4. Layer 4 — Reasoning

### 4.1 The lane router

The first decision on every question:

```
question
  ├─ resolves fully to certified metrics?      → GOVERNED lane
  ├─ resolves partially, rest is Referenced?   → GOVERNED + REFERENCED (mixed, labeled)
  ├─ needs un-modeled data, user is entitled?  → EXPLORATORY lane (labeled un-certified)
  └─ out of grant or out of scope entirely?    → REFUSE (§3.3)
```

The lane is rendered on the artifact. Users must never have to guess which one they got.

### 4.2 Skills: method, not meaning

Skills hold **how your organization does analysis**; the semantic contract holds **what the numbers mean**. Keeping them separate is what lets either change without breaking the other.

Starter set for a commercial-margin domain:

| Skill | Encodes |
|---|---|
| `margin-bridge` | How to decompose a margin change: price, mix, cost, freight, rebate timing. The order of operations, and the bps convention. |
| `variance-investigation` | Threshold for "material," which dimensions to drill first, when to stop |
| `account-risk-review` | Which signals combine into a risk view, and their weights |
| `exec-brief` | What belongs in the Monday brief, and what never does |
| `provenance-block` | How every artifact cites sources, definitions, lane and caveats |

### 4.3 Orchestration pattern

1. **Resolve** — ask the semantic MCP server what metrics and dimensions exist (`list_metrics`, `get_dimensions`). Never assume.
2. **Plan** — map the question to metrics, grains and filters; identify off-schema needs; pick the lane.
3. **Execute** — `query_metrics` for governed numbers; file and document tools for referenced material. Run independent calls in parallel.
4. **Reconcile** — where a referenced source disagrees with a governed metric, the governed number wins and the discrepancy is reported, never silently reconciled.
5. **Compose** — fill an L5 template. Never free-form.
6. **Log** — full trace to the Trust spine.

---

## 5. Layer 5 — Delivery

### 5.1 Template specification

A template is a reviewed contract, approved once by finance or risk and reusable thereafter. Minimum fields:

```yaml
template: margin_variance_review
version: 3
owner: fp&a
sections:
  - headline           # required, one sentence, must name magnitude and direction
  - decomposition      # required, chart + table, bps convention
  - drivers            # required, ranked, each traced to a source
  - recommendations    # required, max 3, each with owner and horizon
  - provenance         # required, non-removable
  - caveats            # required, non-removable, from metric.caveats + lane
metrics_allowed:       # the agent may not substitute others
  - gross_margin_pct
  - net_revenue
  - freight_cost_per_order
lane: governed         # this template refuses to render in exploratory lane
refusal_copy: standard
```

Two fields carry most of the safety: `metrics_allowed` (the agent cannot quietly swap a definition) and the non-removable `provenance` and `caveats` sections.

### 5.2 Delivery modes

| Mode | Trigger | Output | Latency target |
|---|---|---|---|
| **Answer** | ad-hoc question | answer card: headline, chart, table, provenance | < 30s |
| **Artifact** | template invoked | full document — HTML, doc, deck or spreadsheet | < 5 min |
| **Watch** | threshold breach on a schedule | artifact produced *only* on breach | on event |

**Watch** is the mode with the best return and the least attention paid to it: it inverts the model from "people remember to ask" to "the system speaks when something is wrong."

### 5.3 The provenance block

Non-removable, on every artifact:

- Lane (Governed / Mixed / Exploratory)
- Each metric used, with its definition, version and owner
- Each referenced source, with URI, version and last-modified timestamp
- Anything the system refused to include, and why
- Run timestamp and trace ID

---

## 6. The Trust spine

### 6.1 Golden question set

- **20 questions** for a first domain, drawn from real traffic, each with a human-written correct answer.
- Composition: **~60% happy path, ~30% edge cases, ~10% adversarial** — including questions that must be refused and at least one indirect-injection probe.
- Versioned in git beside the semantic contract. A metric change that breaks a golden answer is a failing build.

### 6.2 Three evaluation layers

| Layer | Method | Catches |
|---|---|---|
| **Unit** | ordinary tests on tools, parsers, retrieval | broken plumbing |
| **Eval suite** | golden-set regression, pass/fail per question | wrong metric, wrong grain, missed refusal |
| **LLM-as-judge** | rubric scoring of narrative quality | unresponsive or mis-caveated prose |

Diagnose by reading the trace on every failure and bucketing the failure mode: roughly **80% of failures cluster into three to five buckets**. Fix the bucket.

A published reference implementation worth reading before building your own: [`datacult/dbt-agent-trust`](https://github.com/datacult/dbt-agent-trust).

### 6.3 The score that matters

| Metric | Gate |
|---|---|
| In-scope accuracy | 100% — anything less means the contract is under-specified |
| Correct refusal rate | 100% |
| Provenance completeness | 100% |
| Narrative quality (judge) | ≥ 4/5 median |

In-scope accuracy below 100% is a modeling defect, not a model defect. This is the go/no-go gate for pilot expansion — not the demo.

---

## 7. The Control spine

### 7.1 Identity and privilege
The agent acts as the asking user wherever the source supports it. Where it cannot, the service principal's full reach must be acceptable *assuming compromise*. Prefer **compile-time access control** — access rules compiled into the generated query — over post-hoc result filtering.

### 7.2 Token handling
OAuth 2.1 for remote MCP servers. Token exchange at each hop, audience bound to destination. Never forward a raw user token downstream.

### 7.3 Untrusted content
All retrieved content — tickets, documents, file contents, web pages, field values — is **data, never instructions**. Tickets and shared documents are the highest-risk surface because anyone can write to them. Wrap retrieved content in explicit delimiters, strip or neutralize instruction-shaped text in the highest-risk sources, and keep an injection probe in the golden set.

### 7.4 Write actions
Reads are autonomous. Anything that changes a system — updating a CRM field, filing a ticket, posting a message — is a distinct tool, separately declared, and human-approved at invocation.

### 7.5 Audit
Every run logs: question, user, lane, tools called with arguments, definitions resolved, row counts, artifact produced, refusals, and trace ID. This is simultaneously the audit record, the eval corpus and the debugging surface. Build it first; retrofitting it is painful.

---

## 8. Three adoption paths

Same five layers. Different products.

### 8.1 Enterprise (Snowflake or Databricks estate)

| Layer | Choice |
|---|---|
| Sources | Warehouse + Cortex Search / Vector Search for documents |
| Access | Snowflake-managed MCP server or `Snowflake-Labs/mcp`; Databricks MCP |
| Meaning | Snowflake semantic views / Unity Catalog metrics, **or** dbt Semantic Layer for portability |
| Reasoning | Claude with MCP connectors + Skills; or Cortex Agents for the in-platform subset |
| Delivery | Generated artifacts + a retained governed dashboard set |

*Gotcha:* the Snowflake-**managed** MCP server supports semantic **views**, not semantic **models**. Confirm which surface you are building against before committing — this is the most common and most expensive planning error in this pattern.

### 8.2 Mid-market (a warehouse and a small data team)

| Layer | Choice |
|---|---|
| Sources | BigQuery / Postgres / Redshift + object storage for files |
| Access | dbt MCP server (`list_metrics`, `get_dimensions`, `query_metrics`, plus lineage tools) + DuckDB file server |
| Meaning | **dbt Semantic Layer** — MetricFlow compiles the query deterministically |
| Reasoning | Claude with connectors + Skills |
| Delivery | Interactive HTML artifacts + scheduled briefs |

This is the reference path. It has the best published evidence behind it and the lowest lock-in.

### 8.3 Small organization (no warehouse)

| Layer | Choice |
|---|---|
| Sources | Operational SaaS exports + spreadsheets in a shared drive |
| Access | DuckDB over the drive; vendor MCP servers for SaaS |
| Meaning | **A YAML metrics file in git.** 10–20 metrics, same required fields as §3.1, with a small resolver. |
| Reasoning | Claude with connectors + Skills |
| Delivery | Generated artifacts, no dashboard layer at all |

The semantic contract does **not** require a semantic layer product. It requires written, owned, versioned definitions. A 200-line YAML file in git delivers most of the benefit for an organization of thirty people, and it upgrades cleanly into dbt or Cube later because the required fields are the same.

---

## 9. Build order

Deliberately not the order the diagram suggests. Audit first, because retrofitting it is painful; delivery before breadth, because an artifact is what earns the next round of funding.

1. **Trace logging** (§7.5) — before anything else.
2. **Golden question set** (§6.1) — this is also the scope document.
3. **Semantic contract** for those questions only (§3).
4. **Semantic MCP server** + identity (§2).
5. **One artifact template**, end to end (§5.1).
6. **Eval harness** on the golden set (§6.2).
7. **Off-schema sources** — files and documents (§1.1).
8. **Skills** encoding method (§4.2).
9. **Two more templates**, then Watch mode (§5.2).
10. **Pilot with enablement** — training is a line item, not an afterthought.

Steps 1–6 are the minimum honest system. Everything after is expansion.
