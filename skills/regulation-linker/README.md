# regulation-linker

A CoCo skill that retrieves regulatory clauses from a Cortex Search service
given a metric name or risk description. Returns structured citation metadata
for use in regulatory findings.

## Why

A compliance finding that cites "the AML policy" is not auditable. An examiner
needs the specific clause — §3.1 of the Transaction Monitoring Rules — and
enough text to verify the citation without opening the source document. This
skill bridges the gap between a risk metric and the regulation that makes it
matter.

## Interface

### Input

| Parameter | Required | Default | Description |
|---|---|---|---|
| `query` | yes | — | Metric name, risk context, or regulatory topic |
| `search_service` | no | `PAPERTRAIL.GOLD.REGULATION_SEARCH` | Cortex Search FQN |
| `jurisdiction` | no | — | Filter: `AU`, `SG`, or `BOTH` |
| `max_results` | no | `5` | Clauses to return |
| `clause_role` | no | — | Filter: `DEFINES`, `OPERATIONALISES`, `REFERENCES` |

### Output — Citation array

```json
{
  "query": "transaction structuring detection ...",
  "search_service": "PAPERTRAIL.GOLD.REGULATION_SEARCH",
  "result_count": 3,
  "clauses": [
    {
      "clause_id": "CL-...",
      "clause_number": "§4.2",
      "clause_title": "Structuring Detection Thresholds",
      "clause_text": "The institution must maintain automated ...",
      "clause_text_excerpt": "The institution must maintain autom...",
      "document_title": "Transaction Monitoring Rules",
      "document_type": "PROCEDURE",
      "jurisdiction": "BOTH",
      "clause_role": "DEFINES"
    }
  ]
}
```

## Preconditions

- The Cortex Search service must exist and be active
- The warehouse must be available for search execution
- The caller needs USAGE on the search service

## Composability

This skill is **step 1b** in the PaperTrail provenance chain, running in
parallel with `risk-scanner`:

```
risk-scanner ──┐
               ├──→ finding-writer ──→ provenance-logger
regulation-linker ┘
```

Also independently useful: invoke it any time you need to find the regulatory
basis for a compliance question.

## Adapting to your project

1. Point `search_service` to your Cortex Search service FQN
2. Update the metric-to-query mapping table in SKILL.md Step 1
3. Adjust attribute names if your search schema differs
