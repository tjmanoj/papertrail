PHASE 2 (DEVELOPMENT) — build the CURATED and GOLD layers. Read CORTEX.md,
docs/data-model.md and docs/architecture.md first. Implement what they specify.

RAW is loaded and verified (11 tables, 240,798 transactions). Build the
transformation layer that the semantic view will sit on.

1. sql/03-curated.sql — CURATED layer as DYNAMIC TABLES (TARGET_LAG = '1 hour',
   WAREHOUSE = PAPERTRAIL_WH), idempotent. These should resolve the messiness
   the data model deliberately introduced:
   - Entity resolution: one logical counterparty view that links an individual
     to corporates where they are a beneficial owner, so exposure can be
     computed consistently.
   - A transaction view that makes the governance choices EXPLICIT as columns
     rather than leaving them implicit: settled vs pending, reversal vs not,
     booking date vs value date. Do not filter them out - the whole point is
     that the semantic layer decides, and the columns must exist to be decided on.
   - Account and alert enrichment as the data model describes.

2. sql/04-gold.sql — GOLD layer as DYNAMIC TABLES: the analysis-ready facts and
   dimensions the seven governed metrics need. One row grain per table, clearly
   documented in comments.

3. Attach DATA METRIC FUNCTIONS for data quality on the important columns -
   null counts, duplicate keys, and freshness. Put them in sql/05-quality.sql.
   Use Snowflake's built-in system DMFs where they fit.

4. Wait for the dynamic tables to refresh, then verify:
   - Every dynamic table has refreshed successfully (check
     INFORMATION_SCHEMA / DYNAMIC_TABLE_REFRESH_HISTORY).
   - Row counts at each layer are sane and explainable.
   - The six planted typologies from data/out/ground_truth.csv are still
     traceable through to GOLD. Report found/total per typology.
   - DMF results: report any violations.

5. Suspend PAPERTRAIL_WH when done.

Report: the layer diagram (table -> table), row counts per table, refresh
status, typology traceability, and DMF findings. Flag anything that surprised you.
