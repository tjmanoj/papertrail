-- 05-quality.sql — Data Metric Functions for PaperTrail
-- Idempotent: safe to re-run. Uses ADD ... IF NOT EXISTS pattern where
-- supported; otherwise wraps in exception-safe blocks.
-- Prerequisite: 04-gold.sql (GOLD dynamic tables exist and refreshed).
--
-- Attaches Snowflake built-in system DMFs to important columns in GOLD.
-- Schedule: TRIGGER_ON_CHANGES — DMFs evaluate after each DT refresh.

USE DATABASE PAPERTRAIL;
USE WAREHOUSE PAPERTRAIL_WH;

-- ============================================================
-- 1. Set DMF schedule on GOLD tables
-- ============================================================

ALTER DYNAMIC TABLE GOLD.DIM_COUNTERPARTY
  SET DATA_METRIC_SCHEDULE = 'TRIGGER_ON_CHANGES';

ALTER DYNAMIC TABLE GOLD.DIM_ACCOUNT
  SET DATA_METRIC_SCHEDULE = 'TRIGGER_ON_CHANGES';

ALTER DYNAMIC TABLE GOLD.FACT_TRANSACTION
  SET DATA_METRIC_SCHEDULE = 'TRIGGER_ON_CHANGES';

ALTER DYNAMIC TABLE GOLD.FACT_ALERT
  SET DATA_METRIC_SCHEDULE = 'TRIGGER_ON_CHANGES';

ALTER DYNAMIC TABLE GOLD.FACT_CASE
  SET DATA_METRIC_SCHEDULE = 'TRIGGER_ON_CHANGES';


-- ============================================================
-- 2. DIM_COUNTERPARTY — null counts and duplicate key check
-- ============================================================

ALTER DYNAMIC TABLE GOLD.DIM_COUNTERPARTY
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (counterparty_id);

ALTER DYNAMIC TABLE GOLD.DIM_COUNTERPARTY
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (risk_rating);

ALTER DYNAMIC TABLE GOLD.DIM_COUNTERPARTY
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (jurisdiction);

ALTER DYNAMIC TABLE GOLD.DIM_COUNTERPARTY
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.DUPLICATE_COUNT
  ON (counterparty_id);


-- ============================================================
-- 3. DIM_ACCOUNT — null counts and duplicate key check
-- ============================================================

ALTER DYNAMIC TABLE GOLD.DIM_ACCOUNT
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (account_id);

ALTER DYNAMIC TABLE GOLD.DIM_ACCOUNT
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (counterparty_id);

ALTER DYNAMIC TABLE GOLD.DIM_ACCOUNT
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.DUPLICATE_COUNT
  ON (account_id);


-- ============================================================
-- 4. FACT_TRANSACTION — null counts, duplicate key, freshness
-- ============================================================

ALTER DYNAMIC TABLE GOLD.FACT_TRANSACTION
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (transaction_id);

ALTER DYNAMIC TABLE GOLD.FACT_TRANSACTION
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (counterparty_id);

ALTER DYNAMIC TABLE GOLD.FACT_TRANSACTION
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (amount_usd);

ALTER DYNAMIC TABLE GOLD.FACT_TRANSACTION
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.DUPLICATE_COUNT
  ON (transaction_id);


-- ============================================================
-- 5. FACT_ALERT — null counts, duplicate key
-- ============================================================

ALTER DYNAMIC TABLE GOLD.FACT_ALERT
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (alert_id);

ALTER DYNAMIC TABLE GOLD.FACT_ALERT
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (counterparty_id);

ALTER DYNAMIC TABLE GOLD.FACT_ALERT
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.DUPLICATE_COUNT
  ON (alert_id);


-- ============================================================
-- 6. FACT_CASE — null counts, duplicate key
-- ============================================================

ALTER DYNAMIC TABLE GOLD.FACT_CASE
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (case_id);

ALTER DYNAMIC TABLE GOLD.FACT_CASE
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
  ON (counterparty_id);

ALTER DYNAMIC TABLE GOLD.FACT_CASE
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.DUPLICATE_COUNT
  ON (case_id);
