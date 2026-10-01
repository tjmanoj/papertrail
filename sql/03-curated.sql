-- 03-curated.sql - CURATED-layer dynamic tables for PaperTrail
-- Idempotent: CREATE OR REPLACE throughout.
-- Prerequisite: 01-raw.sql (RAW tables loaded via 02-load.sql).
--
-- CURATED resolves messiness in RAW and makes governance choices EXPLICIT
-- as columns, without filtering anything out. The semantic view (via GOLD)
-- decides which filters to apply - CURATED only exposes the levers.

USE DATABASE PAPERTRAIL;
USE SCHEMA CURATED;
USE WAREHOUSE PAPERTRAIL_WH;

-- ============================================================
-- 1. ENTITY_LINK - beneficial ownership: individual → corporate
-- ============================================================
-- Grain: one row per (individual, corporate) beneficial-ownership link.
-- Heuristic: an individual whose surname appears in a corporate's legal
-- name within the same jurisdiction. In production this comes from a
-- KYC/UBO data feed; here we use name matching as a proxy.
-- The data generator planted one known pair:
--   CP-DUAL-IND "Marcus Wellington" ↔ CP-DUAL-CORP "Wellington Capital Pty Ltd"

CREATE OR REPLACE DYNAMIC TABLE ENTITY_LINK
  TARGET_LAG = '1 hour'
  WAREHOUSE = PAPERTRAIL_WH
AS
SELECT
    ind.counterparty_id        AS individual_counterparty_id,
    corp.counterparty_id       AS corporate_counterparty_id,
    ind.full_legal_name        AS individual_name,
    corp.full_legal_name       AS corporate_name,
    ind.jurisdiction           AS jurisdiction,
    SPLIT_PART(TRIM(ind.full_legal_name), ' ', -1) AS matched_surname
FROM PAPERTRAIL.RAW.COUNTERPARTY ind
JOIN PAPERTRAIL.RAW.COUNTERPARTY corp
  ON corp.counterparty_type = 'CORPORATE'
  AND ind.jurisdiction = corp.jurisdiction
  AND CONTAINS(
        UPPER(corp.full_legal_name),
        UPPER(SPLIT_PART(TRIM(ind.full_legal_name), ' ', -1))
      )
WHERE ind.counterparty_type = 'INDIVIDUAL'
  AND LENGTH(SPLIT_PART(TRIM(ind.full_legal_name), ' ', -1)) >= 5;


-- ============================================================
-- 2. TRANSACTION_CLASSIFIED - governance-explicit transaction view
-- ============================================================
-- Grain: one row per transaction (same as RAW.TRANSACTION).
-- Adds explicit boolean columns for every governance choice the data
-- model identified as a divergence source: settled vs pending, reversal
-- vs not, booking date vs value date, direction, cash flag, structuring
-- band, cross-border. Nothing is filtered - the semantic layer decides.

CREATE OR REPLACE DYNAMIC TABLE TRANSACTION_CLASSIFIED
  TARGET_LAG = '1 hour'
  WAREHOUSE = PAPERTRAIL_WH
AS
SELECT
    t.transaction_id,
    t.account_id,
    a.counterparty_id,
    t.transaction_date                       AS value_date,
    t.transaction_timestamp::DATE            AS booking_date,
    t.transaction_timestamp,
    t.transaction_type,
    t.amount_usd,
    t.originator_name,
    t.originator_country,
    t.beneficiary_name,
    t.beneficiary_country,
    t.transfer_reference,
    t.channel,
    t.status,
    t.is_reversal,
    t.reversed_transaction_id,
    t.reporting_entity_jurisdiction,

    -- Governance-explicit status flags
    (t.status = 'SETTLED')                   AS is_settled,
    (t.status = 'PENDING')                   AS is_pending,
    (t.status = 'FAILED')                    AS is_failed,
    (t.status = 'REVERSED')                  AS is_reversed_status,
    (rev.reversed_txn_id IS NOT NULL)        AS has_been_reversed,

    -- Direction classification
    CASE
        WHEN t.transaction_type IN ('WIRE_IN', 'CASH_DEPOSIT')     THEN 'INFLOW'
        WHEN t.transaction_type IN ('WIRE_OUT', 'CASH_WITHDRAWAL') THEN 'OUTFLOW'
        WHEN t.transaction_type = 'INTERNAL_TRANSFER'              THEN 'INTERNAL'
        WHEN t.transaction_type IN ('POS', 'ATM')                  THEN 'OUTFLOW'
        WHEN t.transaction_type = 'FEE'                            THEN 'FEE'
    END                                      AS net_direction,

    -- Cash flag for structuring detection
    (t.transaction_type IN ('CASH_DEPOSIT', 'CASH_WITHDRAWAL')) AS is_cash,

    -- Structuring band: cash deposits in $8,000-$9,999 (just below $10K threshold)
    (t.transaction_type = 'CASH_DEPOSIT'
     AND t.amount_usd BETWEEN 8000 AND 9999) AS is_structuring_band,

    -- Cross-border flag
    CASE
        WHEN t.transaction_type = 'WIRE_IN'  AND t.originator_country IS NOT NULL
             AND t.originator_country != a.jurisdiction            THEN TRUE
        WHEN t.transaction_type = 'WIRE_OUT' AND t.beneficiary_country IS NOT NULL
             AND t.beneficiary_country != a.jurisdiction           THEN TRUE
        ELSE FALSE
    END                                      AS is_cross_border,

    -- Account context
    a.account_type,
    a.jurisdiction                           AS account_jurisdiction,
    a.status                                 AS account_status,

    -- Counterparty context
    cp.counterparty_type,
    cp.risk_rating                           AS counterparty_risk_rating,
    cp.full_legal_name                       AS counterparty_name,
    cp.jurisdiction                          AS counterparty_jurisdiction

FROM PAPERTRAIL.RAW.TRANSACTION t
JOIN PAPERTRAIL.RAW.ACCOUNT a
  ON t.account_id = a.account_id
JOIN PAPERTRAIL.RAW.COUNTERPARTY cp
  ON a.counterparty_id = cp.counterparty_id
LEFT JOIN (
    SELECT DISTINCT reversed_transaction_id AS reversed_txn_id
    FROM PAPERTRAIL.RAW.TRANSACTION
    WHERE is_reversal = TRUE
      AND reversed_transaction_id IS NOT NULL
) rev
  ON t.transaction_id = rev.reversed_txn_id;


-- ============================================================
-- 3. ALERT_ENRICHED - alert view with transaction and case context
-- ============================================================
-- Grain: one row per alert (same as RAW.ALERT).
-- Enriched with linked-transaction stats, counterparty context,
-- and case linkage. Status flags make disposition explicit.

CREATE OR REPLACE DYNAMIC TABLE ALERT_ENRICHED
  TARGET_LAG = '1 hour'
  WAREHOUSE = PAPERTRAIL_WH
AS
SELECT
    al.alert_id,
    al.counterparty_id,
    al.rule_id,
    al.rule_name,
    al.alert_date,
    al.alert_timestamp,
    al.typology,
    al.severity,
    al.status,
    al.assigned_analyst_id,
    al.jurisdiction,
    al.narrative,

    -- Status flags
    (al.status = 'OPEN')                    AS is_open,
    (al.status = 'ESCALATED')               AS is_escalated,
    (al.status LIKE 'CLOSED%')              AS is_closed,
    (al.status = 'CLOSED_SAR_FILED')        AS is_sar_filed,
    (al.status IN ('OPEN', 'ESCALATED'))    AS is_active,

    -- Linked transaction stats
    COALESCE(atx.linked_transaction_count, 0)       AS linked_transaction_count,
    COALESCE(atx.linked_transaction_amount_usd, 0)  AS linked_transaction_amount_usd,

    -- Counterparty context
    cp.counterparty_type,
    cp.full_legal_name                       AS counterparty_name,
    cp.risk_rating                           AS counterparty_risk_rating,

    -- Case linkage (picks the latest case if multiple)
    ca_ranked.case_id                        AS linked_case_id,
    ci.status                                AS linked_case_status,
    ci.priority                              AS linked_case_priority

FROM PAPERTRAIL.RAW.ALERT al
JOIN PAPERTRAIL.RAW.COUNTERPARTY cp
  ON al.counterparty_id = cp.counterparty_id
LEFT JOIN (
    SELECT
        atb.alert_id,
        COUNT(*)            AS linked_transaction_count,
        SUM(t.amount_usd)  AS linked_transaction_amount_usd
    FROM PAPERTRAIL.RAW.ALERT_TRANSACTION atb
    JOIN PAPERTRAIL.RAW.TRANSACTION t
      ON atb.transaction_id = t.transaction_id
    GROUP BY atb.alert_id
) atx
  ON al.alert_id = atx.alert_id
LEFT JOIN (
    SELECT alert_id, case_id,
           ROW_NUMBER() OVER (PARTITION BY alert_id ORDER BY case_id DESC) AS rn
    FROM PAPERTRAIL.RAW.CASE_ALERT
) ca_ranked
  ON al.alert_id = ca_ranked.alert_id AND ca_ranked.rn = 1
LEFT JOIN PAPERTRAIL.RAW.CASE_INVESTIGATION ci
  ON ca_ranked.case_id = ci.case_id;


-- ============================================================
-- 4. ACCOUNT_ENRICHED - account view with counterparty context
-- ============================================================
-- Grain: one row per account (same as RAW.ACCOUNT).
-- Enriched with counterparty attributes and explicit status flags.

CREATE OR REPLACE DYNAMIC TABLE ACCOUNT_ENRICHED
  TARGET_LAG = '1 hour'
  WAREHOUSE = PAPERTRAIL_WH
AS
SELECT
    a.account_id,
    a.counterparty_id,
    a.account_type,
    a.currency_code,
    a.opened_date,
    a.closed_date,
    a.status,
    a.branch_code,
    a.jurisdiction,
    a.average_monthly_balance_usd,

    -- Status flags
    (a.status = 'ACTIVE')                    AS is_active,
    (a.status = 'DORMANT')                   AS is_dormant,
    (a.status = 'CLOSED')                    AS is_closed_acct,
    (a.status = 'FROZEN')                    AS is_frozen,

    -- Age
    DATEDIFF('day', a.opened_date, CURRENT_DATE()) AS account_age_days,

    -- Counterparty context
    cp.counterparty_type,
    cp.full_legal_name                       AS counterparty_name,
    cp.risk_rating                           AS counterparty_risk_rating,
    cp.pep_flag                              AS counterparty_pep_flag,
    cp.jurisdiction                          AS counterparty_jurisdiction

FROM PAPERTRAIL.RAW.ACCOUNT a
JOIN PAPERTRAIL.RAW.COUNTERPARTY cp
  ON a.counterparty_id = cp.counterparty_id;
