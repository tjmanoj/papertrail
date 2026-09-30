-- 01-raw.sql — RAW-layer DDL for PaperTrail
-- Idempotent: safe to re-run. All CREATE OR REPLACE.
-- Prerequisite: 00-foundation.sql (creates database, schemas, warehouse).

USE DATABASE PAPERTRAIL;
USE SCHEMA RAW;
USE WAREHOUSE PAPERTRAIL_WH;

-- ============================================================
-- 1. COUNTERPARTY
-- ============================================================
CREATE OR REPLACE TABLE COUNTERPARTY (
    counterparty_id             VARCHAR     NOT NULL  COMMENT 'Stable internal identifier',
    counterparty_type           VARCHAR     NOT NULL  COMMENT 'INDIVIDUAL | CORPORATE | CORRESPONDENT_BANK',
    full_legal_name             VARCHAR     NOT NULL  COMMENT 'Name as on legal documents',
    country_of_incorporation    VARCHAR(2)            COMMENT 'ISO 3166-1 alpha-2; corporates/banks',
    country_of_residence        VARCHAR(2)            COMMENT 'ISO 3166-1 alpha-2; individuals',
    date_of_birth               DATE                  COMMENT 'Individuals only; NULL for corporates',
    industry_code               VARCHAR               COMMENT 'ANZSIC division code',
    risk_rating                 VARCHAR     NOT NULL  COMMENT 'LOW | MEDIUM | HIGH | VERY_HIGH',
    risk_rating_date            TIMESTAMP_NTZ         COMMENT 'When risk was last assessed',
    kyc_refresh_due_date        DATE                  COMMENT 'Next mandatory KYC review date',
    onboarding_date             DATE        NOT NULL  COMMENT 'Relationship start date',
    pep_flag                    BOOLEAN     NOT NULL  COMMENT 'Politically Exposed Person flag',
    source_of_wealth            VARCHAR               COMMENT 'Declared source of wealth',
    relationship_manager_id     VARCHAR               COMMENT 'FK to staff (not modelled in RAW)',
    jurisdiction                VARCHAR(2)  NOT NULL  COMMENT 'Booking jurisdiction: AU or SG',

    CONSTRAINT pk_counterparty PRIMARY KEY (counterparty_id)
)
COMMENT = 'Any legal person or entity the bank has a relationship with';

-- ============================================================
-- 2. ACCOUNT
-- ============================================================
CREATE OR REPLACE TABLE ACCOUNT (
    account_id                  VARCHAR     NOT NULL  COMMENT 'Account identifier',
    counterparty_id             VARCHAR     NOT NULL  COMMENT 'FK → COUNTERPARTY',
    account_type                VARCHAR     NOT NULL  COMMENT 'SAVINGS | CURRENT | TERM_DEPOSIT | LOAN | NOSTRO | VOSTRO',
    currency_code               VARCHAR(3)  NOT NULL  COMMENT 'ISO 4217 currency code',
    opened_date                 DATE        NOT NULL  COMMENT 'Account opening date',
    closed_date                 DATE                  COMMENT 'NULL if still open',
    status                      VARCHAR     NOT NULL  COMMENT 'ACTIVE | DORMANT | CLOSED | FROZEN',
    branch_code                 VARCHAR               COMMENT 'Branch identifier',
    jurisdiction                VARCHAR(2)  NOT NULL  COMMENT 'AU or SG',
    average_monthly_balance_usd NUMBER(18,2)          COMMENT 'Rolling 3-month average balance in USD',

    CONSTRAINT pk_account PRIMARY KEY (account_id)
)
COMMENT = 'Product-holding unit: savings, current, loan, nostro/vostro';

-- ============================================================
-- 3. TRANSACTION
-- ============================================================
CREATE OR REPLACE TABLE TRANSACTION (
    transaction_id                  VARCHAR       NOT NULL  COMMENT 'Transaction identifier',
    account_id                      VARCHAR       NOT NULL  COMMENT 'FK → ACCOUNT',
    transaction_date                DATE          NOT NULL  COMMENT 'Value / settlement date',
    transaction_timestamp           TIMESTAMP_NTZ NOT NULL  COMMENT 'Exact booking time',
    transaction_type                VARCHAR       NOT NULL  COMMENT 'WIRE_IN | WIRE_OUT | CASH_DEPOSIT | CASH_WITHDRAWAL | INTERNAL_TRANSFER | POS | ATM | FEE',
    amount_usd                      NUMBER(18,2)  NOT NULL  COMMENT 'Always positive; direction inferred from type',
    originator_name                 VARCHAR                 COMMENT 'Sender name (wire-ins)',
    originator_country              VARCHAR(2)              COMMENT 'Sender country ISO alpha-2',
    beneficiary_name                VARCHAR                 COMMENT 'Receiver name (wire-outs)',
    beneficiary_country             VARCHAR(2)              COMMENT 'Receiver country ISO alpha-2',
    transfer_reference              VARCHAR                 COMMENT 'Links debit/credit legs of a transfer',
    channel                         VARCHAR       NOT NULL  COMMENT 'BRANCH | ONLINE | MOBILE | SWIFT',
    is_reversal                     BOOLEAN       NOT NULL  COMMENT 'TRUE if this reverses a prior txn',
    reversed_transaction_id         VARCHAR                 COMMENT 'FK → TRANSACTION being reversed',
    status                          VARCHAR       NOT NULL  COMMENT 'SETTLED | PENDING | REVERSED | FAILED',
    reporting_entity_jurisdiction   VARCHAR(2)    NOT NULL  COMMENT 'Jurisdiction of the booking branch',

    CONSTRAINT pk_transaction PRIMARY KEY (transaction_id)
)
COMMENT = 'Single monetary movement on an account';

-- ============================================================
-- 4. ALERT
-- ============================================================
CREATE OR REPLACE TABLE ALERT (
    alert_id              VARCHAR       NOT NULL  COMMENT 'Alert identifier',
    counterparty_id       VARCHAR       NOT NULL  COMMENT 'FK → COUNTERPARTY (primary subject)',
    rule_id               VARCHAR       NOT NULL  COMMENT 'Detection rule that fired',
    rule_name             VARCHAR       NOT NULL  COMMENT 'Human-readable rule name',
    alert_date            DATE          NOT NULL  COMMENT 'Date the rule fired',
    alert_timestamp       TIMESTAMP_NTZ NOT NULL  COMMENT 'Exact timestamp of alert generation',
    typology              VARCHAR       NOT NULL  COMMENT 'STRUCTURING | RAPID_MOVEMENT | DORMANT_REACTIVATION | SANCTIONS_NEAR_MATCH | VELOCITY_SPIKE | ROUND_TRIPPING',
    severity              VARCHAR       NOT NULL  COMMENT 'LOW | MEDIUM | HIGH | CRITICAL',
    status                VARCHAR       NOT NULL  COMMENT 'OPEN | ESCALATED | CLOSED_NO_ACTION | CLOSED_SAR_FILED',
    assigned_analyst_id   VARCHAR                 COMMENT 'Analyst assigned to the alert',
    jurisdiction          VARCHAR(2)    NOT NULL  COMMENT 'AU or SG',
    narrative             VARCHAR                 COMMENT 'Auto-generated description of the alert',

    CONSTRAINT pk_alert PRIMARY KEY (alert_id)
)
COMMENT = 'Automated detection signal from a monitoring rule';

-- ============================================================
-- 5. ALERT_TRANSACTION (bridge)
-- ============================================================
CREATE OR REPLACE TABLE ALERT_TRANSACTION (
    alert_id        VARCHAR NOT NULL  COMMENT 'FK → ALERT',
    transaction_id  VARCHAR NOT NULL  COMMENT 'FK → TRANSACTION',

    CONSTRAINT pk_alert_transaction PRIMARY KEY (alert_id, transaction_id)
)
COMMENT = 'Bridge: which transactions triggered or are linked to an alert';

-- ============================================================
-- 6. CASE
-- ============================================================
CREATE OR REPLACE TABLE CASE_INVESTIGATION (
    case_id                 VARCHAR     NOT NULL  COMMENT 'Case identifier',
    counterparty_id         VARCHAR     NOT NULL  COMMENT 'FK → COUNTERPARTY',
    opened_date             DATE        NOT NULL  COMMENT 'Investigation opened date',
    closed_date             DATE                  COMMENT 'NULL if open',
    status                  VARCHAR     NOT NULL  COMMENT 'OPEN | UNDER_REVIEW | ESCALATED_TO_MLRO | SAR_FILED | CLOSED_NO_ACTION',
    priority                VARCHAR     NOT NULL  COMMENT 'ROUTINE | URGENT | CRITICAL',
    assigned_analyst_id     VARCHAR               COMMENT 'Assigned compliance analyst',
    jurisdiction            VARCHAR(2)  NOT NULL  COMMENT 'AU or SG',
    resolution_narrative    VARCHAR               COMMENT 'Free-text outcome description',

    CONSTRAINT pk_case PRIMARY KEY (case_id)
)
COMMENT = 'Investigation case grouping one or more alerts for a counterparty. Named CASE_INVESTIGATION to avoid CASE keyword conflict.';

-- ============================================================
-- 7. CASE_ALERT (bridge)
-- ============================================================
CREATE OR REPLACE TABLE CASE_ALERT (
    case_id   VARCHAR NOT NULL  COMMENT 'FK → CASE_INVESTIGATION',
    alert_id  VARCHAR NOT NULL  COMMENT 'FK → ALERT',

    CONSTRAINT pk_case_alert PRIMARY KEY (case_id, alert_id)
)
COMMENT = 'Bridge: which alerts are grouped into a case';

-- ============================================================
-- 8. WATCHLIST_ENTRY
-- ============================================================
CREATE OR REPLACE TABLE WATCHLIST_ENTRY (
    watchlist_entry_id        VARCHAR     NOT NULL  COMMENT 'Watchlist entry identifier',
    list_source               VARCHAR     NOT NULL  COMMENT 'OFAC_SDN | UN_SANCTIONS | EU_SANCTIONS | AUSTRAC_PRESCRIBED | PEP_LIST',
    listed_name               VARCHAR     NOT NULL  COMMENT 'Name as listed on the watchlist',
    listed_name_normalised    VARCHAR     NOT NULL  COMMENT 'Uppercased, diacritics stripped',
    country                   VARCHAR(2)            COMMENT 'ISO alpha-2 country',
    listed_date               DATE        NOT NULL  COMMENT 'Date added to the list',
    delisted_date             DATE                  COMMENT 'NULL if still active',
    entity_type               VARCHAR     NOT NULL  COMMENT 'INDIVIDUAL | ENTITY | VESSEL | AIRCRAFT',
    identifying_information   VARCHAR               COMMENT 'DOB, passport number, etc.',

    CONSTRAINT pk_watchlist_entry PRIMARY KEY (watchlist_entry_id)
)
COMMENT = 'Sanctions/PEP/adverse-media record from an external watchlist provider';

-- ============================================================
-- 9. WATCHLIST_SCREENING_RESULT
-- ============================================================
CREATE OR REPLACE TABLE WATCHLIST_SCREENING_RESULT (
    screening_id          VARCHAR       NOT NULL  COMMENT 'Screening result identifier',
    counterparty_id       VARCHAR       NOT NULL  COMMENT 'FK → COUNTERPARTY',
    watchlist_entry_id    VARCHAR                 COMMENT 'FK → WATCHLIST_ENTRY; NULL if no match',
    screening_date        TIMESTAMP_NTZ NOT NULL  COMMENT 'When screening was performed',
    match_score           NUMBER(5,2)   NOT NULL  COMMENT '0–100 fuzzy similarity score',
    match_status          VARCHAR       NOT NULL  COMMENT 'CONFIRMED_MATCH | FALSE_POSITIVE | PENDING_REVIEW | NO_MATCH',
    reviewed_by           VARCHAR                 COMMENT 'Analyst who adjudicated',

    CONSTRAINT pk_watchlist_screening PRIMARY KEY (screening_id)
)
COMMENT = 'Output of matching a counterparty against watchlists';

-- ============================================================
-- 10. REGULATORY_DOCUMENT
-- ============================================================
CREATE OR REPLACE TABLE REGULATORY_DOCUMENT (
    document_id           VARCHAR     NOT NULL  COMMENT 'Document identifier',
    document_type         VARCHAR     NOT NULL  COMMENT 'AML_POLICY | SANCTIONS_PROCEDURE | STR_GUIDANCE | KYC_POLICY | LIQUIDITY_GUIDANCE | RISK_APPETITE_STATEMENT',
    title                 VARCHAR     NOT NULL  COMMENT 'Document title',
    version               VARCHAR     NOT NULL  COMMENT 'Version string, e.g. v2.3',
    effective_date        DATE        NOT NULL  COMMENT 'Date the document took effect',
    jurisdiction          VARCHAR(2)  NOT NULL  COMMENT 'Jurisdiction it applies to',
    full_text             VARCHAR     NOT NULL  COMMENT 'Complete document content',
    synthetic_watermark   VARCHAR     NOT NULL  DEFAULT 'SYNTHETIC_DATA_PAPERTRAIL_2026' COMMENT 'Always SYNTHETIC_DATA_PAPERTRAIL_2026',

    CONSTRAINT pk_regulatory_document PRIMARY KEY (document_id)
)
COMMENT = 'Bank policy, regulatory guidance, or procedural document for Cortex Search';

-- ============================================================
-- 11. REGULATORY_DOCUMENT_CLAUSE
-- ============================================================
CREATE OR REPLACE TABLE REGULATORY_DOCUMENT_CLAUSE (
    clause_id       VARCHAR NOT NULL  COMMENT 'Clause identifier',
    document_id     VARCHAR NOT NULL  COMMENT 'FK → REGULATORY_DOCUMENT',
    clause_number   VARCHAR NOT NULL  COMMENT 'Section number, e.g. 4.2.1',
    clause_title    VARCHAR NOT NULL  COMMENT 'Section heading',
    clause_text     VARCHAR NOT NULL  COMMENT 'Full clause text',

    CONSTRAINT pk_clause PRIMARY KEY (clause_id)
)
COMMENT = 'Individually addressable section within a regulatory document — the unit of citation';
