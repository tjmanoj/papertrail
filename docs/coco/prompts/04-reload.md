Reload PAPERTRAIL.RAW from the regenerated CSVs. Read CORTEX.md first.

Context: data/generate.py was fixed for determinism, so data/out/ has been
regenerated and all entity IDs changed. The data currently in Snowflake is
STALE and must be fully replaced. sql/02-load.sql already exists and is correct.

Repo root contains a space in its path - quote paths in PUT commands.
Absolute CSV dir: /Users/manoj/Documents/Tj/h2skill/snowflake coco/papertrail/data/out/

Steps:
1. Re-PUT all 11 CSVs to @PAPERTRAIL.RAW.PAPERTRAIL_LOAD/<tablename>/ with
   OVERWRITE=TRUE AUTO_COMPRESS=TRUE. EXCLUDE ground_truth.csv - it is the
   held-out answer key and must never enter Snowflake.
2. Run the TRUNCATE + COPY INTO statements from sql/02-load.sql.
3. Confirm ground_truth.csv is absent from the stage - LIST the stage and check.
4. Verify and report ONE table with: table, rows in Snowflake, rows in the
   local CSV (count logical CSV records with Python's csv module, NOT wc -l,
   because regulatory_document.csv has embedded newlines in quoted fields),
   and match Y/N. All 11 must match.
5. Referential integrity in Snowflake: report orphan counts for every foreign
   key in docs/data-model.md. All must be zero.
6. Confirm the planted typologies survived the round trip. Read
   data/out/ground_truth.csv locally, then for each of the 6 typologies check
   that its referenced transaction_ids / account_ids / alert_ids all exist in
   Snowflake. Report found/total per typology - all must be 100%.
7. Suspend PAPERTRAIL_WH.

Report the three tables and nothing else unless something failed.
