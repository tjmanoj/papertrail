-- 04-gold.sql - GOLD-layer dynamic tables for PaperTrail
-- Idempotent: CREATE OR REPLACE throughout.
-- Prerequisite: 03-curated.sql (CURATED dynamic tables).
--
-- GOLD provides analysis-ready facts and dimensions for the seven
-- governed metrics the semantic view will expose. Each table has a
-- single, documented grain and is queryable without further joins
-- for the metric(s) it serves.

USE DATABASE PAPERTRAIL;
USE SCHEMA GOLD;
USE WAREHOUSE PAPERTRAIL_WH;

-- ============================================================
-- 1. DIM_COUNTERPARTY - counterparty dimension
-- ============================================================
-- Grain: one row per counterparty.
-- Serves: counterparty_exposure_usd, high_risk_counterparty_count.
-- Includes direct exposure (own active accounts), entity-resolved
-- exposure (adds accounts of corporates beneficially owned), and
-- alert/case summary stats.

CREATE OR REPLACE DYNAMIC TABLE DIM_COUNTERPARTY
  TARGET_LAG = '1 hour'
  WAREHOUSE = PAPERTRAIL_WH
AS
SELECT
    cp.counterparty_id,
    cp.counterparty_type,
    cp.full_legal_name,
    cp.country_of_incorporation,
    cp.country_of_residence,
    cp.date_of_birth,
    cp.industry_code,
    cp.risk_rating,
    cp.risk_rating_date,
    cp.kyc_refresh_due_date,
    cp.onboarding_date,
    cp.pep_flag,
    cp.source_of_wealth,
    cp.relationship_manager_id,
    cp.jurisdiction,

    -- Risk flags
    (cp.risk_rating IN ('HIGH', 'VERY_HIGH'))          AS is_high_risk,
    (cp.kyc_refresh_due_date < CURRENT_DATE())         AS is_kyc_overdue,
    DATEDIFF('day', cp.risk_rating_date,
             CURRENT_TIMESTAMP())                      AS days_since_risk_assessment,

    -- Account stats (direct ownership only)
    COALESCE(accts.active_account_count, 0)            AS active_account_count,
    COALESCE(accts.total_account_count, 0)             AS total_account_count,
    COALESCE(accts.direct_exposure_usd, 0)             AS direct_exposure_usd,

    -- Entity-resolved exposure: direct + beneficial ownership of corporates
    COALESCE(accts.direct_exposure_usd, 0)
      + COALESCE(bo.beneficial_exposure_usd, 0)        AS resolved_exposure_usd,

    -- Alert summary
    COALESCE(alrt.total_alerts, 0)                     AS total_alerts,
    COALESCE(alrt.open_alerts, 0)                      AS open_alerts,
    COALESCE(alrt.escalated_alerts, 0)                 AS escalated_alerts,
    (COALESCE(alrt.open_alerts, 0)
     + COALESCE(alrt.escalated_alerts, 0) > 0)        AS has_active_alert,

    -- Case summary
    COALESCE(cs.total_cases, 0)                        AS total_cases,
    COALESCE(cs.open_cases, 0)                         AS open_cases,
    (COALESCE(cs.open_cases, 0) > 0)                   AS has_open_case

FROM PAPERTRAIL.RAW.COUNTERPARTY cp

LEFT JOIN (
    SELECT
        counterparty_id,
        COUNT(*)                                                         AS total_account_count,
        COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END)                   AS active_account_count,
        SUM(CASE WHEN status = 'ACTIVE'
                 THEN COALESCE(average_monthly_balance_usd, 0) ELSE 0 END) AS direct_exposure_usd
    FROM PAPERTRAIL.RAW.ACCOUNT
    GROUP BY counterparty_id
) accts
  ON cp.counterparty_id = accts.counterparty_id

LEFT JOIN (
    SELECT
        el.individual_counterparty_id AS counterparty_id,
        SUM(CASE WHEN a.status = 'ACTIVE'
                 THEN COALESCE(a.average_monthly_balance_usd, 0) ELSE 0 END) AS beneficial_exposure_usd
    FROM PAPERTRAIL.CURATED.ENTITY_LINK el
    JOIN PAPERTRAIL.RAW.ACCOUNT a
      ON a.counterparty_id = el.corporate_counterparty_id
    GROUP BY el.individual_counterparty_id
) bo
  ON cp.counterparty_id = bo.counterparty_id

LEFT JOIN (
    SELECT
        counterparty_id,
        COUNT(*)                                              AS total_alerts,
        COUNT(CASE WHEN status = 'OPEN' THEN 1 END)          AS open_alerts,
        COUNT(CASE WHEN status = 'ESCALATED' THEN 1 END)     AS escalated_alerts
    FROM PAPERTRAIL.RAW.ALERT
    GROUP BY counterparty_id
) alrt
  ON cp.counterparty_id = alrt.counterparty_id

LEFT JOIN (
    SELECT
        counterparty_id,
        COUNT(*)                                                            AS total_cases,
        COUNT(CASE WHEN status IN ('OPEN', 'UNDER_REVIEW') THEN 1 END)     AS open_cases
    FROM PAPERTRAIL.RAW.CASE_INVESTIGATION
    GROUP BY counterparty_id
) cs
  ON cp.counterparty_id = cs.counterparty_id;


-- ============================================================
-- 2. DIM_ACCOUNT - account dimension
-- ============================================================
-- Grain: one row per account.
-- Serves: counterparty_exposure_usd drill-through.

CREATE OR REPLACE DYNAMIC TABLE DIM_ACCOUNT
  TARGET_LAG = '1 hour'
  WAREHOUSE = PAPERTRAIL_WH
AS
SELECT
    ae.account_id,
    ae.counterparty_id,
    ae.account_type,
    ae.currency_code,
    ae.opened_date,
    ae.closed_date,
    ae.status,
    ae.branch_code,
    ae.jurisdiction,
    ae.average_monthly_balance_usd,
    ae.is_active,
    ae.is_dormant,
    ae.account_age_days,
    ae.counterparty_type,
    ae.counterparty_name,
    ae.counterparty_risk_rating,
    ae.counterparty_pep_flag
FROM PAPERTRAIL.CURATED.ACCOUNT_ENRICHED ae;


-- ============================================================
-- 3. FACT_TRANSACTION - transaction fact
-- ============================================================
-- Grain: one row per transaction.
-- Serves: total_suspicious_transaction_volume_usd,
--         structuring_indicator_score.
-- Includes all governance-explicit flags from CURATED plus alert
-- linkage (whether this transaction is evidentially linked to an
-- active alert). A single transaction can link to multiple alerts;
-- flags reflect the aggregate across all linked alerts.

CREATE OR REPLACE DYNAMIC TABLE FACT_TRANSACTION
  TARGET_LAG = '1 hour'
  WAREHOUSE = PAPERTRAIL_WH
AS
SELECT
    tc.transaction_id,
    tc.account_id,
    tc.counterparty_id,
    tc.value_date,
    tc.booking_date,
    tc.transaction_timestamp,
    tc.transaction_type,
    tc.amount_usd,
    tc.originator_name,
    tc.originator_country,
    tc.beneficiary_name,
    tc.beneficiary_country,
    tc.transfer_reference,
    tc.channel,
    tc.status,
    tc.is_reversal,
    tc.reversed_transaction_id,
    tc.reporting_entity_jurisdiction,

    -- Governance flags (passthrough from CURATED)
    tc.is_settled,
    tc.is_pending,
    tc.is_failed,
    tc.is_reversed_status,
    tc.has_been_reversed,
    tc.net_direction,
    tc.is_cash,
    tc.is_structuring_band,
    tc.is_cross_border,

    -- Context (passthrough from CURATED)
    tc.account_type,
    tc.account_jurisdiction,
    tc.account_status,
    tc.counterparty_type,
    tc.counterparty_risk_rating,
    tc.counterparty_name,
    tc.counterparty_jurisdiction,

    -- Alert linkage (aggregated across all alerts this transaction links to)
    COALESCE(alx.is_alert_linked, FALSE)           AS is_alert_linked,
    COALESCE(alx.is_alert_linked_active, FALSE)    AS is_alert_linked_active,
    COALESCE(alx.linked_alert_count, 0)            AS linked_alert_count,
    alx.linked_alert_max_severity

FROM PAPERTRAIL.CURATED.TRANSACTION_CLASSIFIED tc
LEFT JOIN (
    SELECT
        atb.transaction_id,
        TRUE                                         AS is_alert_linked,
        MAX(IFF(al.status IN ('OPEN', 'ESCALATED'), 1, 0)) > 0  AS is_alert_linked_active,
        COUNT(DISTINCT atb.alert_id)                  AS linked_alert_count,
        CASE MAX(CASE al.severity
                     WHEN 'CRITICAL' THEN 4 WHEN 'HIGH' THEN 3
                     WHEN 'MEDIUM'   THEN 2 WHEN 'LOW'  THEN 1 END)
             WHEN 4 THEN 'CRITICAL' WHEN 3 THEN 'HIGH'
             WHEN 2 THEN 'MEDIUM'   WHEN 1 THEN 'LOW'
        END                                           AS linked_alert_max_severity
    FROM PAPERTRAIL.RAW.ALERT_TRANSACTION atb
    JOIN PAPERTRAIL.RAW.ALERT al
      ON atb.alert_id = al.alert_id
    GROUP BY atb.transaction_id
) alx
  ON tc.transaction_id = alx.transaction_id;


-- ============================================================
-- 4. FACT_ALERT - alert fact
-- ============================================================
-- Grain: one row per alert.
-- Serves: alert_closure_rate (cohort-based).
-- Includes transaction stats, case linkage, and counterparty context
-- from CURATED, plus a cohort_month for time-series aggregation.

CREATE OR REPLACE DYNAMIC TABLE FACT_ALERT
  TARGET_LAG = '1 hour'
  WAREHOUSE = PAPERTRAIL_WH
AS
SELECT
    ae.alert_id,
    ae.counterparty_id,
    ae.rule_id,
    ae.rule_name,
    ae.alert_date,
    ae.alert_timestamp,
    ae.typology,
    ae.severity,
    ae.status,
    ae.assigned_analyst_id,
    ae.jurisdiction,
    ae.narrative,
    ae.is_open,
    ae.is_escalated,
    ae.is_closed,
    ae.is_sar_filed,
    ae.is_active,
    ae.linked_transaction_count,
    ae.linked_transaction_amount_usd,
    ae.counterparty_type,
    ae.counterparty_name,
    ae.counterparty_risk_rating,
    ae.linked_case_id,
    ae.linked_case_status,
    ae.linked_case_priority,

    DATE_TRUNC('MONTH', ae.alert_date)     AS cohort_month

FROM PAPERTRAIL.CURATED.ALERT_ENRICHED ae;


-- ============================================================
-- 5. FACT_CASE - case / investigation fact
-- ============================================================
-- Grain: one row per case.
-- Serves: sar_filing_rate, days_to_case_resolution.
-- Terminal flags distinguish final dispositions from in-progress.
-- days_to_resolution is NULL for cases still open.

CREATE OR REPLACE DYNAMIC TABLE FACT_CASE
  TARGET_LAG = '1 hour'
  WAREHOUSE = PAPERTRAIL_WH
AS
SELECT
    ci.case_id,
    ci.counterparty_id,
    ci.opened_date,
    ci.closed_date,
    ci.status,
    ci.priority,
    ci.assigned_analyst_id,
    ci.jurisdiction,
    ci.resolution_narrative,

    -- Terminal / filing flags
    (ci.status IN ('SAR_FILED', 'CLOSED_NO_ACTION'))   AS is_terminal,
    (ci.status = 'SAR_FILED')                          AS is_sar_filed,
    (ci.status = 'CLOSED_NO_ACTION')                   AS is_closed_no_action,
    (ci.status IN ('OPEN', 'UNDER_REVIEW'))            AS is_open,
    (ci.status = 'ESCALATED_TO_MLRO')                  AS is_escalated,

    -- Resolution timing (calendar days; NULL if not terminal)
    CASE WHEN ci.closed_date IS NOT NULL
         THEN DATEDIFF('day', ci.opened_date, ci.closed_date)
    END                                                AS days_to_resolution,

    -- Cohort
    DATE_TRUNC('MONTH', ci.opened_date)                AS cohort_month,

    -- Alert count
    COALESCE(ca.linked_alert_count, 0)                 AS linked_alert_count,

    -- Counterparty context
    cp.counterparty_type,
    cp.full_legal_name                                 AS counterparty_name,
    cp.risk_rating                                     AS counterparty_risk_rating,
    cp.jurisdiction                                    AS counterparty_jurisdiction

FROM PAPERTRAIL.RAW.CASE_INVESTIGATION ci
JOIN PAPERTRAIL.RAW.COUNTERPARTY cp
  ON ci.counterparty_id = cp.counterparty_id
LEFT JOIN (
    SELECT case_id, COUNT(*) AS linked_alert_count
    FROM PAPERTRAIL.RAW.CASE_ALERT
    GROUP BY case_id
) ca
  ON ci.case_id = ca.case_id;
