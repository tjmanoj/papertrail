# finding-writer

A CoCo skill that assembles a formal regulatory finding from provenance bundles
(from `risk-scanner`) and clause citations (from `regulation-linker`). Every
figure in the output is a footnote resolving to its evidence chain.

## Why

The gap between "we have the data" and "we have a defensible finding" is
formatting and traceability. This skill bridges that gap with a structural
guarantee: **no figure can appear in the finding text unless it was provided
in a provenance bundle**.

## How the no-ungrounded-figure guarantee works

Two structural layers enforce this — it is not a best-effort instruction to
the LLM:

### Layer 1 — Input containment

The AI_COMPLETE prompt is constructed from ONLY:
- Numbered facts extracted from provenance bundles
- Clause citations from the regulatory corpus
- The analyst's original question

The model has no database access, no SQL execution, no raw data. Numbers
can only enter through the bundles.

### Layer 2 — Output validation

After AI_COMPLETE returns, three validation checks run:

| Check | What it verifies | Failure action |
|---|---|---|
| A: Footnote coverage | Every `[N]` maps to a provided fact | Reject finding |
| B: Number grounding | Every number in the text appears in a bundle | Reject finding |
| C: Clause references | At least one clause is cited | Reject finding |

If any check fails, the skill returns an error — never the invalid finding.
Together, these layers make it structurally impossible for an ungrounded number
to survive into the output.

## Interface

### Input

| Parameter | Required | Description |
|---|---|---|
| `question` | yes | The analyst's original question |
| `provenance_bundles` | yes | Array from `risk-scanner` |
| `regulatory_clauses` | yes | Array from `regulation-linker` |
| `model` | no | Default `snowflake-llama-agentic-large` |

### Output

```json
{
  "finding_text": "Formal prose with [1], [2] footnote markers ...",
  "footnotes": [
    {
      "footnote_number": 1,
      "metric_name": "structuring_indicator_score",
      "metric_definition": "...",
      "generated_sql": "SELECT ...",
      "result_value": "33.33",
      "source_row_ids": ["TXN-001", ...],
      "source_table": "PAPERTRAIL.GOLD.FACT_TRANSACTION",
      "clause_id": "CL-...",
      "clause_number": "§4.2",
      "clause_text_excerpt": "The institution must ..."
    }
  ],
  "model_used": "snowflake-llama-agentic-large",
  "generated_at": "2026-10-01T16:00:00Z"
}
```

## Preconditions

- At least one provenance bundle must be provided
- At least one regulatory clause must be provided
- The Snowflake account must support AI_COMPLETE with the requested model

## Composability

This skill is **step 2** in the PaperTrail provenance chain:

```
risk-scanner ──┐
               ├──→ finding-writer ──→ provenance-logger
regulation-linker ┘
```

It consumes the output of both `risk-scanner` and `regulation-linker`.
Its output feeds directly into `provenance-logger`.

## Adapting to your project

1. Adjust the AI_COMPLETE system prompt for your regulatory domain
2. The validation logic, footnote schema, and bundle format are generic
