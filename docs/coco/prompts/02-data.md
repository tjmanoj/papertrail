PHASE 2 (DEVELOPMENT) — synthetic data generation. Read CORTEX.md,
docs/data-model.md and docs/architecture.md first. Implement the spec they
define; do not redesign it.

Build the RAW layer and its generator.

1. Write sql/01-raw.sql — idempotent DDL for every RAW entity in the data model,
   with column comments. Load nothing yet.

2. Write data/generate.py — a deterministic generator (fixed seed, stdlib +
   pandas/numpy only) producing referentially consistent CSVs into data/out/.
   Requirements:
   - Foreign keys must resolve. Dates must order sensibly (no settlement before
     booking, no transaction before account opening).
   - Volumes: roughly 800 counterparties, 1,600 accounts, 250,000 transactions
     over 18 months, plus alerts, cases, watchlist, screening results.
   - Plant ALL SIX typologies from data-model.md section 4 exactly as specified
     at row level, each affecting a known, recorded set of entity IDs.
   - Write data/out/ground_truth.csv listing every planted instance: typology,
     the entity IDs involved, the window, and the expected detection. This file
     is the held-out answer key for evaluation - it must NEVER be loaded into
     Snowflake.
   - Deliberately include the conditions that make metrics diverge: reversals,
     PENDING transactions, transactions whose booking and value dates straddle
     a month boundary, one counterparty who is both an individual accountholder
     and a beneficial owner of a corporate.
   - Print a summary table of row counts and planted signal when run.

3. Run the generator. Verify referential integrity with explicit checks (orphan
   FK counts must be zero) and report the results.

4. Load the CSVs into PAPERTRAIL.RAW. Use a stage plus COPY INTO. Put the
   loading SQL in sql/02-load.sql, idempotent.

5. Verify the load: row counts per table against the CSVs, and confirm the
   planted typologies are actually present in Snowflake with a few spot-check
   queries. Report a table of results.

Remember to suspend PAPERTRAIL_WH when finished. Report concisely at the end:
what exists, row counts, integrity check results, and anything that deviated
from the spec.
