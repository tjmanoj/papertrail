Execute the existing load. Do not rewrite sql/02-load.sql unless it is wrong.

Working dir is the repo root. CSVs are in ./data/out/ (absolute path prefix:
/Users/manoj/Documents/Tj/h2skill/snowflake coco/papertrail/data/out/).
Note the path contains a space - quote it properly in PUT commands.

Steps:
1. Run the stage and file-format DDL from sql/02-load.sql.
2. PUT each CSV into @PAPERTRAIL.RAW.PAPERTRAIL_LOAD/<tablename>/ with
   AUTO_COMPRESS=TRUE OVERWRITE=TRUE. One PUT per table directory, matching the
   COPY INTO paths already in the file. EXCLUDE ground_truth.csv entirely.
3. Run the TRUNCATE + COPY INTO statements.
4. Report a table: table, rows loaded, expected rows from the CSV, match Y/N.
   Expected: counterparty 809, account 1497, transaction 240769,
   alert 219, alert_transaction 3082, case_investigation 93, case_alert 97,
   watchlist_entry 82, watchlist_screening_result 1150,
   regulatory_document 48, regulatory_document_clause 18.
5. Suspend PAPERTRAIL_WH.

Be efficient - batch the PUTs. Report only the results table plus any errors.
