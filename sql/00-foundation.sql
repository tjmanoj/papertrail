-- 00-foundation.sql — PaperTrail project foundation
-- Idempotent: safe to re-run in any account.

-- Warehouse: XS, 60 s auto-suspend, starts suspended
CREATE WAREHOUSE IF NOT EXISTS PAPERTRAIL_WH
  WITH WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME  = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'PaperTrail project — XS warehouse with 60s auto-suspend';

-- Database
CREATE DATABASE IF NOT EXISTS PAPERTRAIL
  COMMENT = 'Risk and regulatory intelligence copilot — Provenance team';

-- Schemas
CREATE SCHEMA IF NOT EXISTS PAPERTRAIL.RAW;
CREATE SCHEMA IF NOT EXISTS PAPERTRAIL.CURATED;
CREATE SCHEMA IF NOT EXISTS PAPERTRAIL.GOLD;
CREATE SCHEMA IF NOT EXISTS PAPERTRAIL.GOVERNANCE;
