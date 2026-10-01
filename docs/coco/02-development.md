# Phase 2 - Development (RAW layer)

**Surface:** CoCo CLI, headless via `cortex exec` · **Connection:** AT72852
**Date:** 2026-10-01

## Sessions

| # | Purpose | Prompt | Transcript |
|---|---|---|---|
| 1 | RAW DDL + generator authored | [`prompts/02-data.md`](prompts/02-data.md) | `transcripts/02-data-*` |
| 2 | Stage, PUT, COPY INTO | [`prompts/02c-load.md`](prompts/02c-load.md) | `transcripts/02-load-*` |
| 3 | Determinism defect fix | [`prompts/03-determinism.md`](prompts/03-determinism.md) | `transcripts/03-determinism-*` |
| 4 | Full reload + verification | [`prompts/04-reload.md`](prompts/04-reload.md) | `transcripts/04-reload-*` |

## What was built

- `sql/01-raw.sql` - 11 RAW tables with column comments, idempotent.
- `sql/02-load.sql` - stage, file format, TRUNCATE + COPY INTO, idempotent.
- `data/generate.py` - deterministic generator: 809 counterparties, 1,497
  accounts, 240,798 transactions over 18 months, plus alerts, cases, watchlist
  and screening results.
- `data/out/ground_truth.csv` - held-out answer key for the six planted
  typologies. **Never loaded into Snowflake**; absence from the stage is
  asserted during every reload.

## A defect worth recording

The generator declared itself deterministic and set both `random.seed()` and
`np.random.seed()`, but minted entity IDs with `uuid.uuid4().hex[:12]`. `uuid4`
draws from `os.urandom` and is not governed by `random.seed()`, so **every run
produced different account, alert and case IDs.**

Consequence: regenerating the data silently invalidated `ground_truth.csv`,
because the key referenced IDs that no longer existed. This was caught by
comparing local CSV record counts against Snowflake rather than trusting the
agent's own summary - which had attributed the row-count drift to "a slightly
newer data generation run."

Fixed by replacing the ID helper with a counter hashed against a fixed salt and
the seed. A self-test now guards it:

```
python3 data/generate.py --verify-determinism
```

It generates twice into separate temp directories and compares SHA-256 of every
output file. 12/12 PASS. Because of this, the whole dataset is reproducible
byte-for-byte, which is what makes a clean-room rebuild in a second Snowflake
account meaningful rather than approximate.

## Verified state

- 11/11 tables: Snowflake row count == logical CSV record count.
- 11/11 foreign keys: zero orphans.
- 6/6 planted typologies: 100% of referenced IDs present in Snowflake.
- `ground_truth.csv` confirmed absent from the stage.
- `PAPERTRAIL_WH` suspended.

Note: logical CSV records are counted with Python's `csv` module, not `wc -l`  -
`regulatory_document.csv` holds 6 records across 48 physical lines because clause
text contains embedded newlines.
