# The Five-Layer Insight Stack

**An executive summary: how to let anyone in the organization ask a real business question and get back a trustworthy, finished piece of work.**

Audience: senior leadership. No prior technical background assumed — but the actual technology is named, because you will be asked what it costs and what it depends on.

---

## The problem, stated honestly

Your organization already has the data. What it does not have is **throughput**.

A question like *"why did margin drop in the Southeast last quarter?"* requires someone to know which table holds the answer, which definition of margin finance actually uses, that the freight rebate accrual lives in a spreadsheet on SharePoint and not in the warehouse at all, and how to write it all up for an executive. That person exists. There are four of them, they are booked six weeks out, and they spend most of their time rebuilding the same analysis with different dates on it.

Two previous attempts to fix this did not work:

- **Self-service BI** gave everyone a dashboard tool. Adoption stalled below 20%, and Gartner has long put BI project failure at 70–80%. The tool was never the constraint — knowing what to ask and what the numbers meant was.
- **Generic AI chatbots over the database** produce plausible, confident, wrong numbers. On real enterprise schemas, unaided natural-language-to-SQL has been measured at **10–31% accuracy**, and roughly **81% of its errors** come from misunderstanding what a column or a join *means* — not from broken syntax. A wrong number that looks right is worse than no number.

The lesson from both: **the bottleneck was never the interface, and it is not the AI model either. It is that the organization has never written down what its own numbers mean in a form a machine can use.**

---

## What we are proposing

A five-layer model that turns questions into finished work — an answer, a chart, a memo, a board-ready brief — while keeping every number traceable to a definition someone owns.

The load-bearing idea is one sentence: **the AI never decides what a metric means; it only decides which agreed metric answers your question, and then writes up the result.**

That single constraint is what separates this from a chatbot, and it is measurable. In a 2026 benchmark, the same frontier models scored **84–90%** writing SQL freely against a schema, and **98–100%** when routed through agreed definitions — with a property that matters more than the accuracy: when the question fell outside what had been defined, the free-SQL approach still answered (sometimes wrongly, always confidently), and the governed approach **refused and said so**. For anything going in front of a board, an auditor, or a regulator, a system that knows what it doesn't know is the only acceptable kind.

---

## The model

Five layers, plus two things that run through all of them. Any organization can adopt this — the layers stay the same whether you run Snowflake and a data team of thirty, or a shared drive and a controller who is good at Excel. Only the products change.

### Layer 1 — Sources: where the truth actually lives

Everything that holds a fact worth asking about. Deliberately including the messy half:

- The **warehouse or database** — Snowflake, Databricks, BigQuery, Postgres, or a folder of Parquet files.
- The **operational systems** — ERP, CRM, support desk, billing, HRIS.
- **The files** — the rebate spreadsheet, the signed contracts, the vendor price list, the quarterly carrier notice PDF. This is where half of every interesting answer lives, and it is the half every BI tool ignores.

*Technology:* your existing systems. Loose files are made queryable in place with **DuckDB** (spreadsheets, CSVs, Parquet), and documents are made searchable with a **vector index** — Snowflake Cortex Search, Databricks Vector Search, or an open-source index for smaller estates.

**Nothing here needs to move.** This is not a data migration.

### Layer 2 — Access: one governed door per system

Every source gets a single, well-described, authenticated entrance that AI tools can use — instead of credentials scattered across scripts and notebooks.

*Technology:* **MCP (Model Context Protocol)** — the standard that settled this in 2025–26. Snowflake, Databricks, dbt, Salesforce, Microsoft and most major vendors now ship MCP servers, so most of this layer is configuration rather than construction. Remote servers authenticate with **OAuth 2.1**.

*The rule that matters:* the door opens **as the person asking**, never as an administrator. If someone cannot see EMEA salaries in the source system, the AI cannot see them either — enforced by the system, not by instructions to the model. The most-cited public failure in this category happened exactly this way: an AI agent connected with an admin-level role that bypassed row-level security, and a malicious instruction hidden in a support ticket caused it to leak data. The agent worked as designed. The *permission* was the defect.

### Layer 3 — Meaning: the semantic contract

**This is the layer that decides whether the whole thing works.** It is a written, version-controlled definition of your business vocabulary: what "net revenue" is, what counts as an "active customer," which grains are valid, who owns each definition, and who is allowed to see what.

*Technology:* **dbt Semantic Layer**, **Cube**, **AtScale**, **Snowflake semantic views**, or **Databricks Unity Catalog metrics**. Write the definitions to the **Apache Ossie** standard (formerly Open Semantic Interchange — v1.0 in January 2026, 33+ backers including Snowflake, Databricks, dbt Labs, Qlik and Salesforce) so they stay portable if you change tools.

Two properties make this layer worth the effort:

- **The query is generated deterministically, not by the AI.** The model picks the metric; a compiler writes the SQL. It structurally cannot invent a wrong join or a wrong aggregation.
- **Permissions are compiled into the query**, not filtered out afterwards.

*Honest cost:* this is where the real work is. You do not need to model everything — you need to model the **twenty questions your leadership actually asks**, which is typically 15–30 metrics and takes a small team **six to ten weeks**. Everything else can wait.

### Layer 4 — Reasoning: the analyst

The AI agent that plans the work: understands the question, picks the right metrics, notices it needs the freight spreadsheet as well as the warehouse, pulls both, does the decomposition, and knows when to stop and say *"I can't answer that."*

*Technology:* **Claude** (or a comparable frontier model) as the agent host, with two distinct things attached:

- **Connectors** — the MCP doors from Layer 2.
- **Skills** — reusable, written-down *analytical method*. How your company does a margin bridge. What belongs in a QBR. How to investigate a variance. This is where your best analysts' judgment gets encoded once and reused by everyone — and it is separate from Layer 3, which holds what the numbers mean rather than how to reason about them.

*The rule that matters:* answers run in one of **two clearly-labeled lanes**. The **governed lane** uses only defined metrics and is valid for decisions of record. The **exploratory lane** can range wider and is labeled as un-certified. Every output shows which lane it came from. This mirrors what the market has already settled on — governed reporting for finance-grade numbers, generative answers for everyday questions — and the mistake is pretending you only need one.

### Layer 5 — Delivery: artifacts, not answers

The part most tools skip. **The unit of business value is a document, not a row.** Nobody wants a query result; they want the margin bridge with three recommendations, the QBR pack, the variance memo with the exceptions already investigated.

So output is generated from **templates** — fixed sections, fixed metric definitions, a required provenance block, a required caveats section. A free-form AI report is unreviewable. A template is reviewed **once** by finance or risk, and then every report built from it is trustworthy by construction.

*Technology:* interactive HTML artifacts, documents, decks and spreadsheets generated on demand; scheduled runs for recurring briefs; a small set of governed dashboards kept for the finance-grade numbers.

Three delivery modes cover nearly everything:

| Mode | What it is | Example |
|---|---|---|
| **Answer** | A question, answered now, with chart and provenance | *"Fill rate by DC this month?"* |
| **Artifact** | A full document from a template | *"Build the Monday exec brief."* |
| **Watch** | Standing monitors that produce an artifact only when something breaks a threshold | *"Tell me when any region's margin moves more than 100bps."* |

### Running through all five: Trust and Control

- **Trust** — a **golden question set**: twenty real questions with human-verified correct answers (~60% routine, ~30% edge cases, ~10% questions that *should be refused*). It runs like a test suite on every change. This turns "do you trust it?" from an argument into a number that moves, and it is the single best-evidenced practice in the field.
- **Control** — least-privilege identity, no credential passthrough, everything the agent read and did is logged, all retrieved content treated as untrusted data rather than instructions, and human approval on anything that writes back to a system.

---

## Why this works where self-service BI did not

| Self-service BI asked users to… | This model asks the organization to… |
|---|---|
| Learn a query tool | Ask in their own words |
| Know which table to use | Write down what the metrics mean, once |
| Build the chart themselves | Receive a finished document |
| Trust the output on faith | See the sources and definitions behind every number |
| Notice when they got it wrong | Be told when the question can't be answered |

The burden moves off the business user and onto a **one-time, reusable, auditable definition effort** — which is work the finance and data teams have wanted to do for years and have never been able to justify. This is the justification.

---

## What it costs and how long it takes

A realistic 90-day path for a first business domain. This is deliberately narrow: pick **one** domain (commercial margin, supply chain, or revenue retention) and one executive sponsor who actually wants the output.

| Phase | Weeks | What happens | Who |
|---|---|---|---|
| **1. Agree the questions** | 1–2 | Collect the 20 questions leadership actually asks. Write the correct answers by hand. This is the golden set *and* the scope. | Business + data lead |
| **2. Define the meaning** | 3–8 | Model 15–30 metrics in the semantic layer. Identify which answers need off-schema files. | Data team (2–3 people) |
| **3. Open the doors** | 5–8 | Stand up MCP access to warehouse, one operational system, and the file store. Identity and least-privilege review. | Data + security |
| **4. Teach the method** | 7–10 | Write 3–5 Skills encoding how your analysts actually do this work. Build 3 artifact templates. | Best analyst + data team |
| **5. Prove it** | 9–11 | Run the golden set. Fix the failures. Target: 100% on in-scope questions, correct refusal on out-of-scope. | Data team |
| **6. Land it** | 11–13 | 20–30 pilot users, with training. Measure. | Sponsor |

**Typical first-domain investment:** 2–3 data people part-time for a quarter, one analyst, plus platform and model costs that are small relative to the labor. **The expensive input is definitional agreement, not compute.**

---

## The risk you should actually worry about

Not that the technology fails. That the organization does what it did last time.

The numbers are unambiguous: ~9 in 10 organizations now use AI somewhere, **~6% capture significant enterprise value**, and an estimated **80–95% of AI projects fail to deliver their promised return**. Rolling out self-service *before* governance basics existed carries a measured **45% failure rate**. Meanwhile **60% of leaders report a data literacy gap** — and organizations that pair AI investment with structured training are **twice as likely to report positive ROI (42% vs 21%)**.

Three specific ways this fails, and the counter to each:

1. **Skipping Layer 3 because the demo works without it.** It always demos well and degrades silently in production. *Counter:* the golden set score is the go/no-go gate, not the demo.
2. **Shipping without training.** *Counter:* budget enablement as a line item from the start.
3. **Boiling the ocean.** Modeling the whole warehouse takes two years and gets cancelled at month nine. *Counter:* twenty questions, one domain, ninety days.

---

## How you will know it is working

| Measure | Target by end of first domain |
|---|---|
| Golden set accuracy, in-scope questions | 100% |
| Correct refusal rate, out-of-scope questions | 100% |
| Median time from question to finished artifact | Under 10 minutes (from 3–10 days) |
| Share of recurring reports produced from templates | 50%+ |
| Weekly active askers in the pilot group | 60%+ of the group |
| Analyst hours returned from routine reporting | Tracked and reported monthly |

The last one is the business case. Everything above it is how you make the last one believable.

---

## What to decide now

1. **Pick the domain and the sponsor.** One domain, one executive who wants the output.
2. **Commission the twenty questions.** This costs two weeks and de-risks everything after it.
3. **Name the owner of the semantic contract.** A person, not a committee. Metric definitions need an editor.
4. **Approve the two-lane principle.** Governed answers for decisions of record, exploratory answers labeled as such — agreed before anyone builds, not after the first disputed number.

---

*Companion documents: `01-research-landscape.md` (the evidence base, with sources) and `03-reference-architecture.md` (the build specification). The interactive demo in `demo/` shows all five layers operating on a worked example.*
