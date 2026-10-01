---
name: provenance-logger
description: Persists a completed regulatory finding and its footnotes to the GOVERNANCE schema tables. Append-only — never updates or deletes. Returns the finding_id and content hash for tamper evidence.
---

# Provenance Logger

You are executing the **provenance-logger** skill. Your single job is to
persist a completed finding and its provenance chain to the GOVERNANCE schema
for permanent audit record.

## Inputs

| Parameter | Required | Description |
|---|---|---|
| `finding` | yes | The complete output of `finding-writer` |
| `question` | yes | The analyst's original question |
| `analyst_role` | no | Defaults to `CURRENT_ROLE()` |
| `analyst_jurisdiction` | no | Jurisdiction scope (`AU`, `SG`, `GLOBAL`) |
| `supersedes_finding_id` | no | If this finding replaces a prior one |
| `database` | no | Default `PAPERTRAIL` |
| `schema` | no | Default `GOVERNANCE` |

## Procedure

### Step 1 — Generate identifiers

Generate a UUID for the finding:

```sql
SELECT UUID_STRING() AS finding_id;
```

Generate one UUID per footnote.

### Step 2 — Compute the content hash

```sql
SELECT SHA2('{finding_text}') AS content_hash;
```

This is tamper evidence: any modification to the finding text changes the hash.

### Step 3 — INSERT the finding

```sql
INSERT INTO <database>.<schema>.FINDINGS (
    finding_id, question_text, finding_text, content_hash,
    analyst_role, analyst_jurisdiction, model_used,
    supersedes_finding_id
) VALUES (
    '<finding_id>',
    '<question>',
    '<finding_text>',
    '<content_hash>',
    '<analyst_role or CURRENT_ROLE()>',
    '<analyst_jurisdiction>',
    '<model_used>',
    <supersedes_finding_id or NULL>
);
```

### Step 4 — INSERT the footnotes

For each footnote in the finding:

```sql
INSERT INTO <database>.<schema>.FINDING_FOOTNOTES (
    footnote_id, finding_id, footnote_number,
    metric_name, metric_definition, generated_sql,
    result_value, source_row_ids, source_table,
    clause_id, clause_number, clause_text_excerpt
) VALUES (
    '<footnote_uuid>',
    '<finding_id>',
    <footnote_number>,
    '<metric_name>',
    '<metric_definition>',
    '<generated_sql>',
    '<result_value>',
    PARSE_JSON('<source_row_ids_array>'),
    '<source_table>',
    '<clause_id>',
    '<clause_number>',
    '<clause_text_excerpt>'
);
```

### Step 5 — Verify persistence

Run a confirmation query:

```sql
SELECT
    f.finding_id,
    f.content_hash,
    f.created_at,
    COUNT(fn.footnote_id) AS footnote_count
FROM <database>.<schema>.FINDINGS f
LEFT JOIN <database>.<schema>.FINDING_FOOTNOTES fn
  ON f.finding_id = fn.finding_id
WHERE f.finding_id = '<finding_id>'
GROUP BY f.finding_id, f.content_hash, f.created_at;
```

### Step 6 — Return

```json
{
  "finding_id": "<uuid>",
  "content_hash": "<sha256>",
  "footnote_count": 2,
  "persisted_at": "<timestamp from DB>",
  "database": "PAPERTRAIL",
  "schema": "GOVERNANCE"
}
```

## Failure modes

| Condition | Action |
|---|---|
| Missing `finding_text` | Return `{"error": "NO_FINDING_TEXT"}` — nothing to persist |
| Missing footnotes array | Return `{"error": "NO_FOOTNOTES"}` — a finding without provenance is not loggable |
| INSERT fails (constraint violation) | Return the SQL error. Do NOT retry with a different ID without understanding why. |
| Verification query returns 0 rows | Return `{"error": "PERSISTENCE_FAILED"}` — the INSERT did not commit |

## What this skill does NOT do

- Does NOT run analytical queries or compute metrics
- Does NOT call AI_COMPLETE or any LLM
- Does NOT retrieve regulatory documents
- Does NOT update or delete existing findings — append-only
- Does NOT validate the finding content — that is `finding-writer`'s responsibility
- Does NOT generate or modify finding text

## Append-only policy

This skill enforces append-only semantics:
- It executes INSERT statements only — never UPDATE or DELETE
- If a finding must be corrected, a new finding is created with
  `supersedes_finding_id` pointing to the prior one
- Both findings persist permanently; the latest is authoritative

## Adapting to another project

Replace three values:
1. The `database` and `schema` defaults
2. The table names (`FINDINGS`, `FINDING_FOOTNOTES`) if yours differ
3. The column list if your schema has additional fields

The append-only pattern, verification step, and content-hash mechanism are
project-independent.
