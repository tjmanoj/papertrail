Set up the PaperTrail project foundation. Do exactly these steps, then report results concisely.

1. Report the current account, region, active role, and any existing warehouses.

2. Create an XS warehouse named PAPERTRAIL_WH with AUTO_SUSPEND = 60,
   AUTO_RESUME = TRUE, INITIALLY_SUSPENDED = TRUE. Idempotent DDL.

3. Create database PAPERTRAIL with schemas RAW, CURATED, GOLD, GOVERNANCE.

4. IMPORTANT DIAGNOSTIC — determine whether Cortex AI inference works in this
   region. Try, in order, and report exactly which succeed and which fail with
   what error:
     SELECT AI_COMPLETE('claude-sonnet-5', 'Reply with the single word OK');
     SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b', 'Reply with OK');
   Then query SHOW PARAMETERS LIKE 'CORTEX_ENABLED_CROSS_REGION' IN ACCOUNT.
   Tell me which model names are actually usable in this region, and whether
   cross-region inference needs enabling.

5. Write every DDL statement you ran into sql/00-foundation.sql, idempotent,
   with brief comments.

Do not create any other objects. Do not generate data yet.
