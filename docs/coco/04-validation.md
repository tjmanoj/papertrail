# Phase 4 — Testing & validation (ongoing)

Validation is continuous here rather than a final step, because three sessions
reported success while leaving the database in a different state than claimed.

## Standing rule

**No claim about Snowflake is accepted from a transcript.** Every assertion in
this repo about what exists is confirmed by querying the account.

## Audit of phases 0–3

Session `06-audit` ran a full audit before Phase 4 began. Eight sections, every
row marked PASS or FAIL.

| Section | Result |
|---|---|
| A · Warehouse config (XSMALL / 60s / suspended) | PASS |
| B · Schemas (RAW, CURATED, GOLD, GOVERNANCE) | PASS |
| C · RAW row counts, 11 tables | PASS |
| D · 9 dynamic tables, refresh state | PASS |
| E · Referential integrity | PASS *(after correction)* |
| F · Data metric functions | PASS *(after correction)* |
| G · Typology traceability to GOLD, 6 typologies | PASS |
| H · Answer-key isolation | PASS |

### The audit's own two false failures

The first pass reported E and F as failures. Both were defects in the audit, not
in the data — a useful reminder that a check is only as good as its query.

**F — data metric functions.** The audit queried for DMFs *defined in*
`PAPERTRAIL` and found zero. But the attached metrics are system-defined
(`SNOWFLAKE.CORE.NULL_COUNT`, `SNOWFLAKE.CORE.DUPLICATE_COUNT`), so that query
could never see them. The correct query is:

```sql
SELECT * FROM TABLE(INFORMATION_SCHEMA.DATA_METRIC_FUNCTION_REFERENCES(
  REF_ENTITY_NAME => 'PAPERTRAIL.GOLD.FACT_TRANSACTION',
  REF_ENTITY_DOMAIN => 'TABLE'));
```

Result: **17 attachments across all 5 GOLD tables, all `STARTED`.**

**E — referential integrity.** The audit flagged 1,141 orphans on
`WATCHLIST_SCREENING_RESULT → WATCHLIST_ENTRY`. It had counted NULL foreign keys
as orphans. An orphan is a *non-null* key with no parent. Split properly:

| Measure | Rows |
|---|---|
| Total | 1,143 |
| NULL `watchlist_entry_id` | 1,141 |
| **True orphans** | **0** |

NULL is semantically correct: those rows are `NO_MATCH` screenings with low match
scores, so there is no watchlist entry to point at. Only the two sanctions-scenario
rows carry a non-null key, and both resolve.

## Still outstanding

- DMFs are attached and `STARTED` but have not yet produced rows in
  `SNOWFLAKE.LOCAL.DATA_QUALITY_MONITORING_RESULTS`. That is *no results yet*,
  not *zero violations* — to be re-checked before submission.
- The scored evaluation against `ground_truth.csv` runs once the agent exists.
