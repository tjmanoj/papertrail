# PaperTrail Skills

Four CoCo CLI skills that compose into an audit-ready provenance chain. Each is
independently useful; together they turn a compliance question into a persisted
regulatory finding where every figure resolves to governed SQL and source rows.

## The chain

```
                    Analyst question
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
         risk-scanner       regulation-linker
         (governed SQL)     (Cortex Search)
                │                   │
                └─────────┬─────────┘
                          ▼
                   finding-writer
                   (AI_COMPLETE + validation)
                          │
                          ▼
                  provenance-logger
                  (GOVERNANCE tables)
```

`risk-scanner` and `regulation-linker` are independent and can run in parallel.
`finding-writer` requires both outputs. `provenance-logger` runs last.

## What each skill does

| Skill | Responsibility | Reads | Writes |
|---|---|---|---|
| [`risk-scanner`](risk-scanner/) | Query a governed metric, return a provenance bundle with SQL + source row IDs | Semantic view, GOLD tables | Nothing |
| [`regulation-linker`](regulation-linker/) | Retrieve regulatory clauses from Cortex Search | Cortex Search service | Nothing |
| [`finding-writer`](finding-writer/) | Assemble a formal finding from bundles + clauses via AI_COMPLETE | Nothing (formats input only) | Nothing |
| [`provenance-logger`](provenance-logger/) | Persist finding + footnotes to GOVERNANCE tables | Nothing | GOVERNANCE.FINDINGS, GOVERNANCE.FINDING_FOOTNOTES |

## The provenance chain for a single figure

A number in a finding resolves through:

```
"33.33% of cash deposits fall within the structuring band" [1]
  └── Footnote [1]
        ├── Metric: structuring_indicator_score
        ├── Definition: "Percentage of settled, non-reversal cash deposits
        │   with amounts in the $8,000-$9,999 band"
        ├── SQL: SELECT ... FROM PAPERTRAIL.GOLD.FACT_TRANSACTION ...
        ├── Source rows: [TXN-abc, TXN-def, ...]
        └── Clause: §4.2 "Structuring Detection Thresholds"
            - Transaction Monitoring Rules (BOTH jurisdictions)
```

## How to use

### Full chain (CoCo session)

```
$risk-scanner    → returns provenance bundle(s)
$regulation-linker → returns clause citations
$finding-writer  → assembles finding from both outputs
$provenance-logger → persists to GOVERNANCE tables
```

### Individual use

Each skill stands alone:
- Use `$risk-scanner` any time you need a metric with full audit metadata
- Use `$regulation-linker` to find which clauses govern a given topic
- Use `$finding-writer` if you already have bundles and clauses from elsewhere
- Use `$provenance-logger` to persist any finding that follows the schema

## Adapting to your project

All four skills are parameterised. No hardcoded counterparty IDs, dates, or
PaperTrail-specific values appear in the skill logic. To reuse:

1. **risk-scanner** - point `semantic_view` to your own semantic view, update
   the governed metric list
2. **regulation-linker** - point `search_service` to your Cortex Search FQN,
   update the metric-to-query mapping
3. **finding-writer** - adjust the AI_COMPLETE system prompt for your domain;
   the validation logic is domain-independent
4. **provenance-logger** - point to your governance tables; the append-only
   pattern and content-hash mechanism are generic

## Prerequisites

- A Cortex Analyst semantic view with governed metrics
- A Cortex Search service over a regulatory or policy corpus
- Governance tables matching the schema in `sql/08-governance.sql`
- A Snowflake warehouse (XS is sufficient)
