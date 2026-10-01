---
name: finding-writer
description: Assembles a formal regulatory finding from provenance bundles and clause citations. Every figure in the output is a footnote that resolves to its source bundle. Structurally incapable of stating an ungrounded number — enforced by two-layer validation, not by instruction alone.
---

# Finding Writer

You are executing the **finding-writer** skill. Your job is to assemble a
formal regulatory finding from evidence that other skills have already gathered.
You do NOT query data or retrieve regulations — you format what you are given.

## The no-ungrounded-figure guarantee

This is the core invariant: **no number may appear in the finding text unless
it came from a provenance bundle provided as input**.

This is enforced by two structural layers, not by asking the LLM nicely:

### Layer 1 — Input containment

The AI_COMPLETE prompt you construct contains ONLY:
- Numbered FACTS extracted from provenance bundles (each with a [N] marker)
- Clause citations from regulation-linker
- The analyst's question

The model receives NO raw data, NO database access, NO SQL execution
capability. There is literally no path for an ungoverned number to enter
the prompt.

### Layer 2 — Output validation

After AI_COMPLETE returns, you MUST run validation before returning the
finding. Validation checks:

1. Every `[N]` footnote marker in the text maps to a fact in the input
2. Every number in the text (integers, decimals, percentages, currency)
   appears in at least one input fact
3. No `[N]` marker references a fact index that doesn't exist

If validation fails, you MUST return an error — never the invalid finding.

Together these layers mean: even if the LLM hallucinates a number, it cannot
survive validation because it won't appear in any provenance bundle.

## Inputs

| Parameter | Required | Description |
|---|---|---|
| `question` | yes | The analyst's original question |
| `provenance_bundles` | yes | Array of bundles from `risk-scanner` |
| `regulatory_clauses` | yes | Array of citation objects from `regulation-linker` |
| `model` | no | LLM model for AI_COMPLETE. Default `snowflake-llama-agentic-large` |

## Procedure

### Step 1 — Build the numbered fact list

For each provenance bundle, create a numbered fact entry:

```
[1] Metric: structuring_indicator_score
    Value: 33.33%
    Definition: Percentage of settled, non-reversal cash deposits ...
    Source: PAPERTRAIL.GOLD.FACT_TRANSACTION (6 rows)
    SQL: SELECT ... FROM ...

[2] Metric: counterparty_exposure_usd
    Value: $1,250,000
    ...
```

Store this mapping: `{1: bundle_0, 2: bundle_1, ...}`

### Step 2 — Build the clause citation list

For each regulatory clause, format:

```
Clause A: §4.2 "Structuring Detection Thresholds" — Transaction Monitoring Rules
  "The institution must maintain automated monitoring ..."

Clause B: §3.1 "Reporting Obligations" — AML Policy
  "All suspicious activity ..."
```

### Step 3 — Call AI_COMPLETE

Execute this SQL:

```sql
SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
  '<model>',
  CONCAT(
    'You are a compliance analyst writing a formal regulatory finding.\n\n',
    'RULES (these are absolute — violating any one invalidates the finding):\n',
    '1. You may ONLY cite numbers that appear in the FACTS section below.\n',
    '2. Every number you state MUST be immediately followed by a footnote [N]\n',
    '   where N is the fact number it came from.\n',
    '3. If the question requires a figure not present in FACTS, write:\n',
    '   "This finding cannot substantiate [topic] — no governed metric was provided."\n',
    '4. Every finding must reference at least one regulatory clause by letter.\n',
    '5. Do NOT round, recompute, or derive new numbers from the facts.\n',
    '6. Write in formal third-person register suitable for a regulatory filing.\n\n',
    'QUESTION:\n', '<question>', '\n\n',
    'FACTS:\n', '<numbered_facts>', '\n\n',
    'REGULATORY CLAUSES:\n', '<formatted_clauses>', '\n\n',
    'Write the finding now. Every figure must have a [N] footnote. ',
    'End with a section titled "Regulatory Basis" listing each clause cited.'
  )
) AS finding_text;
```

### Step 4 — Validate the output (MANDATORY — never skip)

Run these checks on the finding text returned by AI_COMPLETE:

**Check A — Footnote coverage:**
Extract all `[N]` markers from the text. Verify every N is in range
`[1..number_of_facts]`. If any N is out of range → REJECT.

**Check B — Number grounding:**
Extract all numbers from the text (regex: numbers with optional commas,
decimals, dollar signs, percent signs). Exclude footnote markers themselves.
For each extracted number, verify it appears (possibly reformatted) in at
least one provenance bundle's `result_value` or `result_rows`. If an
ungrounded number is found → REJECT.

**Check C — Clause references:**
Verify the finding references at least one clause letter (A, B, C...) that
maps to a provided regulatory clause.

If ANY check fails, return:
```json
{
  "error": "VALIDATION_FAILED",
  "checks_failed": ["A", "B"],
  "detail": "Footnote [7] references non-existent fact; number 42.5 has no source bundle"
}
```

Do NOT retry automatically. Return the error so the caller can decide.

### Step 5 — Build the output

```json
{
  "finding_text": "<the validated prose>",
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
  "model_used": "<model>",
  "generated_at": "<ISO 8601 timestamp>"
}
```

Each footnote merges data from the provenance bundle and the clause citation
that was mapped to that metric.

### Step 6 — Return

Present the complete output structure. Do NOT add commentary beyond the
structure itself.

## Failure modes

| Condition | Action |
|---|---|
| No provenance bundles provided | Return `{"error": "NO_PROVENANCE", "detail": "..."}` |
| No regulatory clauses provided | Return `{"error": "NO_CLAUSES", "detail": "..."}` |
| AI_COMPLETE returns malformed text | Return `{"error": "MALFORMED_OUTPUT", "detail": "..."}` |
| Validation fails (any check) | Return validation error with detail (see Step 4) |

## What this skill does NOT do

- Does NOT query the database — it formats what it is given
- Does NOT retrieve regulatory documents — those come from `regulation-linker`
- Does NOT compute, derive, or estimate any numbers
- Does NOT write to GOVERNANCE tables — that is `provenance-logger`'s job
- Does NOT retry on validation failure — it surfaces the error
- Does NOT skip validation under any circumstances

## Adapting to another project

The finding-writer is project-independent. It takes provenance bundles and
clause citations in a standard schema and produces a finding. To adapt:

1. Adjust the AI_COMPLETE system prompt if your regulatory domain differs
2. The bundle/citation schema, validation logic, and output format are reusable
