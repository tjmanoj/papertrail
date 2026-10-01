---
name: regulation-linker
description: Retrieves governing regulatory clauses from a Cortex Search service given a metric name or risk description. Returns full citation metadata. Pure retrieval — never runs analytical SQL, never computes metrics.
---

# Regulation Linker

You are executing the **regulation-linker** skill. Your single job is to
retrieve the regulatory clause(s) that govern a given risk metric or
description, and return structured citation metadata.

## Inputs

The user must provide **at least one** of:

| Parameter | Required | Description |
|---|---|---|
| `query` | yes | Metric name, risk description, or regulatory topic to search for |
| `search_service` | no | FQN of the Cortex Search service. Default `PAPERTRAIL.GOLD.REGULATION_SEARCH` |
| `jurisdiction` | no | Filter results to a jurisdiction (e.g. `AU`, `SG`, `BOTH`) |
| `max_results` | no | Number of clauses to return. Default `5` |
| `clause_role` | no | Filter by clause role: `DEFINES`, `OPERATIONALISES`, or `REFERENCES` |

## Procedure

### Step 1 — Build the search query

If the user provides a metric name (e.g. `structuring_indicator_score`),
expand it into a search-friendly phrase:

| Metric | Search query |
|---|---|
| `total_suspicious_transaction_volume_usd` | `suspicious transaction volume reporting threshold` |
| `counterparty_exposure_usd` | `counterparty exposure limits concentration risk` |
| `alert_closure_rate` | `alert closure resolution timeline requirements` |
| `sar_filing_rate` | `suspicious activity report SAR filing requirements` |
| `structuring_indicator_score` | `transaction structuring detection currency threshold reporting` |
| `days_to_case_resolution` | `case resolution timeline investigation completion` |
| `high_risk_counterparty_count` | `high risk counterparty enhanced due diligence` |

If the user provides free text, use it directly as the search query.

### Step 2 — Query Cortex Search

Execute this SQL:

```sql
SELECT *
FROM TABLE(
  <search_service>!SEARCH(
    query   => '<search_query>',
    columns => ARRAY_CONSTRUCT(
      'clause_id', 'clause_text', 'document_title', 'document_type',
      'clause_number', 'clause_title', 'jurisdiction', 'clause_role'
    ),
    filter  => <filter_object_or_empty>,
    limit   => <max_results>
  )
);
```

Build the `filter` object from optional parameters:
- If `jurisdiction` is provided: `{'@eq': {'jurisdiction': '<value>'}}`
- If `clause_role` is provided: `{'@eq': {'clause_role': '<value>'}}`
- If both: `{'@and': [{'@eq': {'jurisdiction': '...'}}, {'@eq': {'clause_role': '...'}}]}`
- If neither: omit the `filter` parameter entirely

### Step 3 — Package citation metadata

For each result row, produce:

```json
{
  "clause_id": "<clause_id>",
  "clause_number": "<clause_number>",
  "clause_title": "<clause_title>",
  "clause_text": "<full clause text>",
  "clause_text_excerpt": "<first 200 characters>",
  "document_title": "<document_title>",
  "document_type": "<POLICY|PROCEDURE|GUIDELINE>",
  "jurisdiction": "<AU|SG|BOTH>",
  "clause_role": "<DEFINES|OPERATIONALISES|REFERENCES>"
}
```

### Step 4 — Return

Return the array of citation objects. Do NOT interpret, summarise, or rank
them beyond Cortex Search's own relevance ordering. The citations ARE the
output.

```json
{
  "query": "<the search query used>",
  "search_service": "<FQN>",
  "result_count": 5,
  "clauses": [ ... ]
}
```

## Failure modes

| Condition | Action |
|---|---|
| Cortex Search returns zero results | Return `{"error": "NO_MATCHING_CLAUSES", "query": "..."}`. Do not fabricate clauses. |
| Search service does not exist | Return `{"error": "SEARCH_SERVICE_NOT_FOUND", "service": "..."}` |
| Invalid filter value | Return `{"error": "INVALID_FILTER", "detail": "..."}` |

## What this skill does NOT do

- Does NOT run analytical SQL or compute metrics — it only searches the regulatory corpus
- Does NOT write to any table
- Does NOT generate findings or prose
- Does NOT interpret whether a clause applies — it retrieves candidates by relevance
- Does NOT call AI_COMPLETE or any LLM
- Does NOT modify the search index or underlying data

## Adapting to another project

Replace two values:
1. The `search_service` default FQN
2. The metric-to-query mapping table in Step 1

The search SQL, citation schema, and filter logic are reusable with any
Cortex Search service that has clause-level attributes.
