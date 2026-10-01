Reload Snowflake with the date-shifted data, then re-validate. Read CORTEX.md.

data/out/ was regenerated with the window shifted to 2025-04-01..2026-09-30.
Snowflake currently holds the OLD data and all entity IDs have changed, so a
full replace is required. sql/02-load.sql already exists and is correct.

CSV dir (note the space in the path, quote it):
/Users/manoj/Documents/Tj/h2skill/snowflake coco/papertrail/data/out/

1. Re-PUT all 11 CSVs with OVERWRITE=TRUE. EXCLUDE ground_truth.csv.
2. Run the TRUNCATE + COPY INTO statements from sql/02-load.sql.
3. Force a refresh of all 9 dynamic tables (4 CURATED, 5 GOLD) so they pick up
   the new data, and confirm each last-refresh state is SUCCEEDED.
4. Verify: row counts per RAW table against logical CSV record counts (use
   Python's csv module, not wc -l), and zero TRUE orphan foreign keys - a NULL
   FK is not an orphan, only a non-null value with no parent counts.
5. Confirm the date shift landed: min/max transaction date in
   GOLD.FACT_TRANSACTION, and the count of transactions in Q3 2026
   (expect roughly 90,000, definitely not 71).
6. RE-RUN the Cortex Analyst validation against PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC
   for these, reporting question / generated SQL / answer / PASS or FAIL on
   governed semantics:
     a) What was our total suspicious transaction volume last quarter?
     b) Which counterparties have the highest exposure?
     c) What is our alert closure rate this year?
     d) How many high risk counterparties do we have in Singapore?
     e) What share of cases resulted in a SAR filing?
   Question (a) previously returned $546.93 against sparse data - it must now
   return a substantial figure. Be honest about any that fail.
7. Suspend PAPERTRAIL_WH.

Report: load table, integrity, date-range confirmation, and the validation table.
