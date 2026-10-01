---
name: risk-scanner
description: Runs a governed metric query through a Cortex Analyst semantic view and returns a structured provenance bundle — the metric value, its definition, the exact SQL, and the source row identifiers. Read-only. Never writes data, never generates prose.
---

# Risk Scanner

You are executing the **risk-scanner** skill. Your single job is to query a
governed metric and return a structured **provenance bundle** that a downstream
skill or human auditor can verify independently.

## Inputs

The user must provide **at least one** of:

| Parameter | Required | Description |
|---|---|---|
| `question` | yes (or `metric`) | Natural-language question implying a metric |
| `metric` | yes (or `question`) | Explicit governed metric name |
| `semantic_view` | no | FQN of the semantic view. Default `PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC` |
| `warehouse` | no | Warehouse. Default `PAPERTRAIL_WH` |
| `filters` | no | Jurisdiction, date range, counterparty ID, or other WHERE-clause constraints |

## Governed metrics

The semantic view defines exactly seven governed metrics. This skill only
operates on these — if a question falls outside them, return an error.

1. `total_suspicious_transaction_volume_usd` — SUM of settled, non-reversal, alert-linked amounts
2. `counterparty_exposure_usd` — entity-resolved exposure (direct + beneficial ownership)
3. `alert_closure_rate` — percentage of alerts with CLOSED status
4. `sar_filing_rate` — percentage of cases with SAR_FILED status
5. `structuring_indicator_score` — percentage of cash deposits in the $8K–$9,999 band
6. `days_to_case_resolution` — calendar days from case open to close
7. `high_risk_counterparty_count` — COUNT DISTINCT where risk_rating IN (HIGH, VERY_HIGH)

## Procedure

### Step 1 — Query via Cortex Analyst

```
cortex analyst query "<question>" --view=<semantic_view>
```

Extract from the response:
- The **SQL** Cortex Analyst generated
- The **result rows**
- Which governed **metric** the SQL computes (match against the seven above)

If Cortex Analyst is unavailable or returns an error, fall back to Step 1b.

### Step 1b — Fallback: run a Verified Query Representation

Identify the relevant VQR from the semantic view YAML's `verified_queries:`
section. Apply the user's filters to the VQR SQL. Execute it directly:

```sql
USE WAREHOUSE PAPERTRAIL_WH;
<VQR SQL with filters applied>
```

Use the VQR SQL as the `generated_sql` in the output bundle.

### Step 2 — Look up the metric definition

Read the metric's `description:` field from the semantic view YAML (under
`measures:` for the relevant table). This is the business-language definition
that goes into the provenance bundle.

### Step 3 — Capture source row identifiers

Run a follow-up query to get the **primary keys** of rows that contributed to
the aggregation. Use the same FROM/WHERE clause from Step 1, but SELECT the
PK column instead of the aggregate:

- Transaction metrics → `transaction_id` from `FACT_TRANSACTION`
- Counterparty metrics → `counterparty_id` from `DIM_COUNTERPARTY`
- Alert metrics → `alert_id` from `FACT_ALERT`
- Case metrics → `case_id` from `FACT_CASE`

Limit to 1000 row IDs. If more exist, note the total count.

### Step 4 — Package the provenance bundle

Return **exactly** this JSON structure:

```json
{
  "metric": "<metric_name>",
  "metric_definition": "<business definition from semantic view>",
  "generated_sql": "<exact SQL from Step 1 or 1b>",
  "result_value": "<the computed figure as a string>",
  "result_rows": [{"col": "val", ...}],
  "source_row_ids": ["<pk1>", "<pk2>"],
  "source_row_count": 42,
  "source_table": "<FQN of source table>",
  "semantic_view": "<FQN used>",
  "queried_at": "<ISO 8601 timestamp>"
}
```

### Step 5 — Return

Present the JSON bundle to the user. Do NOT summarise, interpret, or add prose.
The bundle IS the output.

## Failure modes

| Condition | Action |
|---|---|
| Cortex Analyst cannot answer | Return `{"error": "ANALYST_CANNOT_ANSWER", "detail": "..."}` |
| Question maps to no governed metric | Return `{"error": "NO_MATCHING_METRIC", "available_metrics": [...]}` |
| Query returns zero rows | Return a valid bundle with `result_value: "0"` and empty `source_row_ids`. Zero is a valid finding. |
| Warehouse suspended | Resume it (`ALTER WAREHOUSE <wh> RESUME`), run the query, note this in output |

## What this skill does NOT do

- Does NOT generate prose, summaries, findings, or interpretations
- Does NOT write to any table — it is strictly read-only
- Does NOT query regulatory documents or Cortex Search
- Does NOT run ad-hoc SQL — every query goes through the semantic view or its VQRs
- Does NOT call AI_COMPLETE or any LLM for text generation
- Does NOT chain to other skills — it returns its bundle and stops

## Adapting to another project

Replace three values:
1. The `semantic_view` default FQN
2. The `warehouse` default name
3. The governed metric list (read them from your own semantic view YAML)

Everything else — the procedure, bundle schema, and failure handling — is
project-independent.
