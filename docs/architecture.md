# PaperTrail - Architecture Design

> Design-only document. No objects created. Written before any DDL beyond
> foundation schemas so a judge can see the thinking that preceded the build.

---

## 5. The Path: Signal → Evidence → Documented Finding

The system converts a raw risk signal in transaction data into an audit-ready
regulatory finding. Every step uses a native Snowflake feature - no external
orchestration, no third-party LLM APIs.

### Step-by-step flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         ANALYST QUESTION                        │
│  "Show me counterparties with structuring indicators above 70   │
│   in the last quarter and cite the relevant AML policy clause"  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
               ┌───────────────────────┐
               │  CORTEX ANALYST       │
               │  Semantic View query  │
               │  (governed SQL only)  │
               └───────────┬───────────┘
                           │  Returns: structured result set
                           │  + the exact SQL that produced it
                           │  + metric definitions from semantic view
                           ▼
               ┌───────────────────────┐
               │  CORTEX SEARCH        │
               │  Regulatory documents │
               │  (unstructured)       │
               └───────────┬───────────┘
                           │  Returns: matching clauses with
                           │  document_id, clause_number, clause_text
                           ▼
               ┌───────────────────────┐
               │  AI_COMPLETE          │
               │  Finding assembly     │
               │  (structured prompt)  │
               └───────────┬───────────┘
                           │  Returns: prose finding where every
                           │  figure is a footnote
                           ▼
               ┌───────────────────────┐
               │  PROVENANCE TABLE     │
               │  GOVERNANCE.FINDINGS  │
               │  (persisted record)   │
               └───────────────────────┘
```

### Handoffs between steps

| From | To | What passes | Format |
|---|---|---|---|
| Analyst question | Cortex Analyst | Natural language question | Text |
| Cortex Analyst | Finding assembly | Result rows, SQL text, metric definitions | Structured JSON: `{metric_name, sql, rows, definition}` |
| Cortex Search | Finding assembly | Relevant regulatory clauses | Structured JSON: `{clause_id, clause_number, clause_text, document_title}` |
| Finding assembly (AI_COMPLETE) | GOVERNANCE.FINDINGS | Prose finding with footnotes | Text (finding) + JSON (provenance chain) |

### What each Snowflake feature does

| Feature | Role in PaperTrail |
|---|---|
| **Semantic View** | Single governed definition of every metric. Cortex Analyst can only generate SQL through the semantic view, so there is no path to ungoverned computation. The semantic view YAML includes verified queries (VQRs) that encode the "blessed" way to compute each metric. |
| **Cortex Analyst** | Translates natural language to SQL via the semantic view. Returns the SQL it generated - this SQL becomes the provenance evidence for every figure. |
| **Cortex Search** | Indexes regulatory documents (REGULATORY_DOCUMENT_CLAUSE table). When a finding references a metric, the system retrieves the relevant regulatory clause that justifies why that metric matters. |
| **AI_COMPLETE** | Assembles the final finding. Input is structured (metric results + clause citations). Output is prose with footnotes. The LLM does not compute any numbers - it formats them. Numbers come only from governed SQL. |
| **Row Access Policy** | Controls which rows each analyst persona can see based on jurisdiction. An AU analyst and an SG analyst asking the same question get different result sets - correctly and traceably. |

---

## 6. Skill Decomposition

Four CoCo CLI skills. Each has a single responsibility, clear inputs/outputs,
and an explicit boundary.

### Skill 1: `risk-scanner`

**Responsibility:** Run governed metric queries and return structured results
with full provenance metadata.

**What it does:**
- Accepts a metric name (or natural language question that implies a metric).
- Routes through Cortex Analyst against the semantic view.
- Captures the generated SQL, the result set, and the metric definition from
  the semantic view YAML.
- Returns a structured provenance bundle: `{metric, sql, rows, definition}`.

**Inputs:** A natural language question or explicit metric name + parameters
(date range, jurisdiction, counterparty filter).

**Outputs:** JSON provenance bundle. Every number in the output can be traced
to specific rows and the governed SQL that produced them.

**Boundary:** This skill never generates prose, never touches regulatory
documents, never writes to the findings table. It only queries and packages
evidence.

---

### Skill 2: `regulation-linker`

**Responsibility:** Given a metric or risk context, retrieve the specific
regulatory clause(s) that apply.

**What it does:**
- Accepts a metric name or a short description of the risk finding.
- Queries Cortex Search over the REGULATORY_DOCUMENT_CLAUSE table.
- Returns the top matching clauses with full citation metadata.

**Inputs:** Metric name or contextual description of the regulatory question.

**Outputs:** Array of `{clause_id, clause_number, clause_text, document_title,
document_type, jurisdiction}`.

**Boundary:** This skill never runs analytical SQL, never computes metrics,
never generates findings. It is a pure retrieval interface over the regulatory
corpus.

---

### Skill 3: `finding-writer`

**Responsibility:** Assemble a formal regulatory finding from evidence bundles
and regulatory citations.

**What it does:**
- Accepts one or more provenance bundles from `risk-scanner` and clause
  citations from `regulation-linker`.
- Calls AI_COMPLETE with a structured prompt that requires every figure to be
  a footnote referencing its provenance bundle.
- The prompt is rigid: the model may not state any number that is not in the
  input bundles. If the question requires a metric not in the input, the
  skill returns a "cannot substantiate" response rather than hallucinating.
- Outputs formatted finding text with numbered footnotes.

**Inputs:** `{provenance_bundles: [...], regulatory_clauses: [...], question: "..."}`

**Outputs:** `{finding_text: "...", footnotes: [{id, metric, sql, source_rows,
clause_citation}], generated_at: timestamp}`

**Boundary:** This skill never runs SQL against the database. It never
retrieves regulatory documents. It only formats what it is given. The
"no figure without provenance" constraint is enforced here - structurally,
by only providing governed numbers as input.

---

### Skill 4: `provenance-logger`

**Responsibility:** Persist a completed finding and its full provenance chain
to the GOVERNANCE schema for audit trail.

**What it does:**
- Accepts the output of `finding-writer`.
- Writes to `GOVERNANCE.FINDINGS` (the finding text, timestamp, analyst
  identity, question asked).
- Writes to `GOVERNANCE.FINDING_FOOTNOTES` (one row per footnote: the metric
  name, the SQL, the source row identifiers, the clause citation).
- Returns the `finding_id` for reference.

**Inputs:** The complete output of `finding-writer` plus session context
(analyst role, jurisdiction).

**Outputs:** `{finding_id, persisted_at, footnote_count}`

**Boundary:** This skill only writes to GOVERNANCE schema. It never runs
analytical queries, never calls LLMs, never retrieves documents.

---

### How the skills chain

```
                    Analyst question
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
         risk-scanner       regulation-linker
                │                   │
                └─────────┬─────────┘
                          ▼
                   finding-writer
                          │
                          ▼
                  provenance-logger
```

`risk-scanner` and `regulation-linker` run in parallel (they are independent).
`finding-writer` requires both outputs. `provenance-logger` runs last.

A CoCo session orchestrates this as a sequential tool chain. No external
orchestrator is needed - the skills are invoked in conversation order.

---

## 7. Row-Level Governance

### Personas

| Persona | Role | Jurisdiction | What they see |
|---|---|---|---|
| `AU_COMPLIANCE_ANALYST` | Compliance analyst | AU | All counterparties, accounts, transactions, alerts, and cases where `jurisdiction = 'AU'`. |
| `SG_COMPLIANCE_ANALYST` | Compliance analyst | SG | All counterparties, accounts, transactions, alerts, and cases where `jurisdiction = 'SG'`. |

### Regulatory justification

Under AUSTRAC (Australia) and MAS (Singapore) regulations, AML compliance
functions are structured by jurisdiction. An Australian compliance officer has
no authority to investigate a Singapore-booked client, and vice versa. Sharing
counterparty data across jurisdictions requires an explicit cross-border
information sharing agreement.

More concretely:
- AUSTRAC AML/CTF Rules Part 8.1 require that access to customer information
  be limited to staff with a legitimate compliance need.
- MAS Notice 626 §13 requires that Singapore-booked customer data be accessible
  only to Singapore-based compliance staff unless a formal data-sharing
  arrangement is documented.

This means the same query - "show me high-risk counterparties" - legitimately
returns different rows for different analysts, and both answers are correct for
their jurisdiction.

### Where Row Access Policies apply

| Table | Policy column | Logic |
|---|---|---|
| `COUNTERPARTY` | `jurisdiction` | `CURRENT_ROLE()` determines visible jurisdictions |
| `ACCOUNT` | `jurisdiction` | Same |
| `TRANSACTION` | `reporting_entity_jurisdiction` | Same |
| `ALERT` | `jurisdiction` | Same |
| `CASE` | `jurisdiction` | Same |
| `WATCHLIST_SCREENING_RESULT` | joins to COUNTERPARTY.jurisdiction | Inherited from counterparty's jurisdiction |

### Cross-border transactions

A transaction where `originator_country = 'AU'` and `beneficiary_country = 'SG'`
is booked by the initiating branch (`reporting_entity_jurisdiction = 'AU'`).
The SG analyst sees the receiving leg on the SG account but not the sending
alert on the AU side. This is the correct regulatory behaviour - the SG analyst
works the SG side independently.

**Assumption:** A `GLOBAL_MLRO` role exists that sees all jurisdictions for
escalated cases. This role is not used in the demo but the row access policy
should accommodate it with a simple role check.

---

## 8. Provenance Mechanism

### The chain

A single figure in a finished finding resolves through four links:

```
Figure in finding text
  └── Footnote [1]
        ├── Metric definition (from semantic view YAML)
        ├── Exact SQL (captured from Cortex Analyst response)
        ├── Source rows (transaction_ids / counterparty_ids that produced the number)
        └── Regulatory clause (clause_id, clause_number, document_title)
```

### What must be persisted

Two tables in `GOVERNANCE` schema:

#### `GOVERNANCE.FINDINGS`

| Column | Type | Description |
|---|---|---|
| `finding_id` | VARCHAR PK | UUID |
| `question_text` | VARCHAR | The analyst's original question |
| `finding_text` | VARCHAR | The assembled prose finding |
| `analyst_role` | VARCHAR | `CURRENT_ROLE()` at time of generation |
| `analyst_jurisdiction` | VARCHAR | Derived from role |
| `generated_at` | TIMESTAMP_NTZ | |
| `model_used` | VARCHAR | Which LLM assembled the finding |

#### `GOVERNANCE.FINDING_FOOTNOTES`

| Column | Type | Description |
|---|---|---|
| `footnote_id` | VARCHAR PK | UUID |
| `finding_id` | VARCHAR FK | |
| `footnote_number` | INTEGER | Position in the finding text |
| `metric_name` | VARCHAR | e.g. `total_suspicious_transaction_volume_usd` |
| `metric_definition` | VARCHAR | Business definition from semantic view |
| `generated_sql` | VARCHAR | The exact SQL Cortex Analyst produced |
| `result_value` | VARCHAR | The number as it appears in the finding |
| `source_row_ids` | ARRAY | Array of primary keys from source tables |
| `source_table` | VARCHAR | Which table the rows came from |
| `clause_id` | VARCHAR FK | References REGULATORY_DOCUMENT_CLAUSE |
| `clause_number` | VARCHAR | e.g. `§3.1` for display |
| `clause_text_excerpt` | VARCHAR | First 200 chars of the clause |

### Why this works

- **Reproducibility:** Given `generated_sql`, any auditor can re-run the query
  and verify the number. If the underlying data has changed (new transactions
  posted), the timestamp on the finding establishes the point-in-time context.
- **Traceability:** `source_row_ids` means an auditor can drill to the exact
  rows - not "these are the kinds of transactions" but "these specific
  transaction_ids."
- **Regulatory justification:** `clause_id` resolves to the specific paragraph
  of policy that says this metric matters. An examiner doesn't have to take
  the analyst's word for why the number was computed.
- **Tamper evidence:** Findings are INSERT-only. No UPDATE or DELETE on
  `GOVERNANCE.FINDINGS`. A finding is a permanent record. If a finding is
  superseded, a new finding is created with a reference to the prior one.

### What we explicitly do NOT persist

- The full result set of every query. Only the aggregated value and the PKs of
  contributing rows. Re-running the SQL reproduces the full detail.
- The raw LLM prompt/response. We persist the structured input (bundles +
  clauses) and the structured output (finding + footnotes). The intermediate
  prompt engineering is not part of the audit trail.

---

## 9. Risks and Open Questions

### Will be hard

| Risk | Why | Mitigation |
|---|---|---|
| **Cortex Analyst SQL fidelity** | Cortex Analyst may generate SQL that doesn't exactly match the semantic view's intended semantics - e.g., it might apply filters in the wrong order or miss the reversal exclusion. Verified queries help but may not cover every question shape. | Write verified queries (VQRs) for the 7 governed metrics. Evaluation suite tests that the Analyst produces correct SQL for at least 20 natural-language variations. If the Analyst deviates, the VQR should redirect it. |
| **Provenance capture from Analyst** | Cortex Analyst returns SQL, but capturing it programmatically (not just displaying it) for storage in the provenance table requires parsing the Analyst response. If the Analyst response format changes or the SQL is embedded in markdown, extraction may break. | Build a rigid extraction function that expects SQL in a code block. Test it against 20+ Analyst responses in the eval suite. Fall back to "unable to extract provenance" rather than guessing. |
| **Cortex Search relevance for clause retrieval** | Regulatory documents are dense and use overlapping terminology. A query about "structuring" might retrieve clauses about "account structure" instead of "transaction structuring." | Use clause-level chunking (not full documents) to keep chunks focused. Include the clause title and section number in the indexed text to give the search model more context. Test retrieval precision in evals. |
| **Synthetic data believability** | Generating 50K transactions that look like a real bank's activity while also embedding detectable signal is non-trivial. Random data won't have realistic daily/weekly patterns, amount distributions, or counterparty behaviour. | Use a Python generation script with explicit distributions: log-normal for amounts, weekday-weighted for dates, Poisson for transaction counts. Embed typologies as explicit code paths, not random perturbations. |
| **Row access policy + Cortex Analyst interaction** | Row access policies filter at query time. If the semantic view is queried by an AU analyst, the results are correct for AU. But the Cortex Analyst doesn't know it's being filtered - it might say "total across all counterparties" when it means "total across AU counterparties." | The semantic view should include `jurisdiction` as a required filter dimension. The Analyst prompt (system instruction in the semantic view YAML) should state that results are jurisdiction-scoped. |

### Might not work in three days

| Concern | Impact if it fails | Fallback |
|---|---|---|
| **End-to-end skill chaining** | If CoCo skill chaining is unreliable or slow, the demo becomes "run each skill manually" rather than a fluid analyst experience. | Pre-record a demo video of the full chain working. Have a backup where the presenter manually triggers each skill in sequence, which still shows the architecture even if automation is incomplete. |
| **Cortex Analyst VQR coverage** | If Analyst ignores VQRs for novel question phrasings, some answers may use ungoverned SQL. | Limit the demo to the 7 governed metrics with known-good VQRs. Don't ad-lib questions during the live demo. |
| **Cortex Search on small corpus** | With only 6 regulatory documents (~30 clauses), Cortex Search may not have enough signal to rank well. | If retrieval is poor, fall back to a simpler keyword-based lookup table mapping metric names to clause IDs. Less impressive but still demonstrates the provenance concept. |
| **Finding quality** | AI_COMPLETE may produce awkward prose or fail to properly format footnotes in the required structure. | Use a rigid structured output prompt with few-shot examples. Validate output format programmatically; retry once if malformed; display raw JSON provenance if prose generation fails. |

### Open questions

1. **Should the semantic view cover both RAW and CURATED, or only GOLD?**
   The semantic view should sit on GOLD-layer views that join and clean the
   data. The semantic view should never reach into RAW directly. Decision:
   semantic view → GOLD views → CURATED tables → RAW tables.

2. **How many verified queries?** At minimum one per governed metric (7).
   Ideally 2-3 per metric covering different filter combinations. Budget 15-20
   VQRs total. More is better for Analyst accuracy but each takes time to write
   and test.

3. **Should findings be immutable or versionable?** Design says INSERT-only.
   But what if an analyst generates a finding, spots an error, and wants to
   regenerate? Proposed: new finding with a `supersedes_finding_id` column.
   Both findings persist; the latest is authoritative.

4. **Demo persona management.** Do we create actual Snowflake roles
   (`AU_COMPLIANCE_ANALYST`, `SG_COMPLIANCE_ANALYST`) or simulate jurisdiction
   filtering with a session variable? Real roles are more impressive for the
   demo but take time to set up. Decision deferred to implementation session.
