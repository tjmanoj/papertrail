-- 08-governance.sql - Provenance tables for audit-ready findings
-- Idempotent: CREATE OR REPLACE throughout, safe to re-run.
-- Prerequisite: 00-foundation.sql (creates GOVERNANCE schema).
--
-- Design rationale (architecture.md §8):
--   A figure in a finished finding must resolve to four things:
--     (a) the governed metric definition it came from
--     (b) the exact SQL that produced it
--     (c) the source row keys behind that SQL
--     (d) the regulation clause that makes it matter
--   These two tables capture exactly that chain.

USE DATABASE PAPERTRAIL;
USE SCHEMA GOVERNANCE;
USE WAREHOUSE PAPERTRAIL_WH;

-- ============================================================
-- 1. FINDINGS - one row per completed regulatory finding
-- ============================================================
-- Append-only by policy: no UPDATE or DELETE in application code.
-- If a finding is superseded, a new row is inserted with
-- supersedes_finding_id pointing to the prior finding.

CREATE OR REPLACE TABLE FINDINGS (
    finding_id             VARCHAR        NOT NULL
        COMMENT 'UUID - immutable primary key for this finding',
    question_text          VARCHAR        NOT NULL
        COMMENT 'The analyst question that triggered this finding',
    finding_text           VARCHAR        NOT NULL
        COMMENT 'Assembled prose finding with numbered footnote markers',
    content_hash           VARCHAR        NOT NULL
        COMMENT 'SHA-256 of finding_text - tamper-evidence for the audit record',
    analyst_role           VARCHAR        NOT NULL
        COMMENT 'CURRENT_ROLE() at generation time - ties finding to RBAC context',
    analyst_jurisdiction   VARCHAR
        COMMENT 'Jurisdiction derived from role (AU, SG, GLOBAL) - scopes the data the finding covers',
    model_used             VARCHAR
        COMMENT 'LLM model that assembled the finding prose (e.g. snowflake-llama-agentic-large)',
    supersedes_finding_id  VARCHAR
        COMMENT 'If this finding restates a prior one, the prior finding_id - preserves full history without updates',
    created_at             TIMESTAMP_NTZ  NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'Append-only timestamp - establishes point-in-time context for reproducibility',

    CONSTRAINT pk_findings PRIMARY KEY (finding_id),
    CONSTRAINT fk_supersedes FOREIGN KEY (supersedes_finding_id) REFERENCES FINDINGS (finding_id)
)
COMMENT = 'Append-only audit trail of regulatory findings - every figure traceable to governed SQL and source rows';


-- ============================================================
-- 2. FINDING_FOOTNOTES - one row per cited figure in a finding
-- ============================================================
-- Each footnote is the provenance chain for one number:
--   metric definition  → generated SQL → source rows → regulation clause

CREATE OR REPLACE TABLE FINDING_FOOTNOTES (
    footnote_id          VARCHAR        NOT NULL
        COMMENT 'UUID - unique identifier for this footnote',
    finding_id           VARCHAR        NOT NULL
        COMMENT 'FK to FINDINGS - which finding contains this footnote',
    footnote_number      INTEGER        NOT NULL
        COMMENT 'Position in the finding text ([1], [2], ...) - display ordering',

    -- (a) Metric definition from the semantic view
    metric_name          VARCHAR        NOT NULL
        COMMENT 'Governed metric name from the semantic view (e.g. total_suspicious_transaction_volume_usd)',
    metric_definition    VARCHAR
        COMMENT 'Business-language definition of the metric - from the semantic view YAML',

    -- (b) Exact SQL that produced the number
    generated_sql        VARCHAR        NOT NULL
        COMMENT 'The SQL Cortex Analyst generated - an auditor can re-run this to verify the figure',

    -- The figure itself
    result_value         VARCHAR        NOT NULL
        COMMENT 'The number as it appears in the finding text - stored as VARCHAR to preserve formatting',

    -- (c) Source rows behind the SQL
    source_row_ids       ARRAY
        COMMENT 'PKs from the source table that contributed to the figure - enables drill-to-row audit',
    source_table         VARCHAR
        COMMENT 'Fully qualified table name the rows came from (e.g. PAPERTRAIL.GOLD.FACT_TRANSACTION)',

    -- (d) Regulation clause that makes the figure matter
    clause_id            VARCHAR
        COMMENT 'FK to REGULATORY_DOCUMENT_CLAUSE - the specific clause this figure satisfies',
    clause_number        VARCHAR
        COMMENT 'Human-readable clause reference (e.g. §3.1) for display in the finding',
    clause_text_excerpt  VARCHAR
        COMMENT 'First 200 chars of the clause - enough context without duplicating the full corpus',

    created_at           TIMESTAMP_NTZ  NOT NULL  DEFAULT CURRENT_TIMESTAMP()
        COMMENT 'When this footnote was persisted',

    CONSTRAINT pk_footnotes PRIMARY KEY (footnote_id),
    CONSTRAINT fk_footnote_finding FOREIGN KEY (finding_id) REFERENCES FINDINGS (finding_id)
)
COMMENT = 'Provenance chain for every figure in a finding: metric → SQL → source rows → regulation clause';
