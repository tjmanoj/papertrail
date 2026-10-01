# provenance-logger

A CoCo skill that persists a completed regulatory finding and its full
provenance chain to Snowflake GOVERNANCE tables. Append-only by design —
never updates, never deletes.

## Why

A finding that exists only in a chat session is not auditable. This skill
writes the finding, its footnotes, and a SHA-256 content hash to permanent
tables so the provenance chain survives the session and can be independently
verified.

## Interface

### Input

| Parameter | Required | Default | Description |
|---|---|---|---|
| `finding` | yes | — | Complete output of `finding-writer` |
| `question` | yes | — | The analyst's original question |
| `analyst_role` | no | `CURRENT_ROLE()` | Role at generation time |
| `analyst_jurisdiction` | no | — | `AU`, `SG`, or `GLOBAL` |
| `supersedes_finding_id` | no | `NULL` | Prior finding this replaces |
| `database` | no | `PAPERTRAIL` | Target database |
| `schema` | no | `GOVERNANCE` | Target schema |

### Output

```json
{
  "finding_id": "a1b2c3d4-...",
  "content_hash": "e3b0c442...",
  "footnote_count": 2,
  "persisted_at": "2026-10-01T16:15:00Z",
  "database": "PAPERTRAIL",
  "schema": "GOVERNANCE"
}
```

## Preconditions

- `GOVERNANCE.FINDINGS` and `GOVERNANCE.FINDING_FOOTNOTES` tables must exist
- The caller must have INSERT privilege on both tables
- The `finding` input must contain `finding_text` and `footnotes` array

## Composability

This skill is the **final step** in the PaperTrail provenance chain:

```
risk-scanner ──┐
               ├──→ finding-writer ──→ provenance-logger
regulation-linker ┘
```

Also independently useful: any finding (from any source) can be logged as long
as it conforms to the input schema.

## Adapting to your project

1. Point `database` and `schema` to your governance tables
2. Adjust table/column names if your schema differs
3. The append-only pattern and content-hash mechanism are generic
