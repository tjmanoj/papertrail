# risk-scanner

A CoCo skill that queries governed metrics through a Cortex Analyst semantic
view and returns a structured **provenance bundle**: the metric value, its
business definition, the exact SQL that produced it, and the primary keys of
every source row.

## Why

Querying a metric is easy. *Defending* the number — proving what SQL produced
it, which rows fed it, and what it means — is the hard part. This skill
captures all four in one atomic operation so downstream consumers (humans,
auditors, or the `finding-writer` skill) can cite the figure with full
traceability.

## Interface

### Input

| Parameter | Required | Default | Description |
|---|---|---|---|
| `question` | yes* | — | Natural-language metric question |
| `metric` | yes* | — | Explicit metric name (alternative to `question`) |
| `semantic_view` | no | `PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC` | Semantic view FQN |
| `warehouse` | no | `PAPERTRAIL_WH` | Warehouse name |
| `filters` | no | — | Jurisdiction, date range, counterparty ID |

\* Provide `question` or `metric`; at least one is required.

### Output — Provenance Bundle

```json
{
  "metric": "structuring_indicator_score",
  "metric_definition": "Percentage of settled, non-reversal cash deposits ...",
  "generated_sql": "SELECT ... FROM PAPERTRAIL.GOLD.FACT_TRANSACTION ...",
  "result_value": "33.33",
  "result_rows": [{"counterparty_id": "CP-abc", "structuring_indicator_score": 33.33}],
  "source_row_ids": ["TXN-001", "TXN-002"],
  "source_row_count": 6,
  "source_table": "PAPERTRAIL.GOLD.FACT_TRANSACTION",
  "semantic_view": "PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC",
  "queried_at": "2026-10-01T15:30:00Z"
}
```

### Error output

```json
{"error": "NO_MATCHING_METRIC", "available_metrics": ["...", "..."]}
```

## Preconditions

- The semantic view must exist and be queryable
- The warehouse must exist (the skill will resume it if suspended)
- The caller must have SELECT on the GOLD schema tables

## Composability

This skill is **step 1** in the PaperTrail provenance chain:

```
risk-scanner ──┐
               ├──→ finding-writer ──→ provenance-logger
regulation-linker ┘
```

But it is also independently useful: invoke it any time you need a governed
metric with full audit metadata, even without generating a finding.

## Adapting to your project

1. Point `semantic_view` to your own semantic view FQN
2. Update the governed metric list in SKILL.md
3. The bundle schema, procedure, and error handling are project-independent
