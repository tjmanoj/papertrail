-- 10-experiment.sql — Governance experiment: governed vs ungoverned paths
-- Idempotent: CREATE OR REPLACE throughout.
-- Prerequisite: 00-foundation.sql (GOVERNANCE schema exists).

USE DATABASE PAPERTRAIL;
USE SCHEMA GOVERNANCE;
USE WAREHOUSE PAPERTRAIL_WH;

-- ============================================================
-- Experiment results table
-- ============================================================
CREATE TABLE IF NOT EXISTS GOVERNANCE_EXPERIMENT (
    experiment_id       VARCHAR       DEFAULT UUID_STRING()  COMMENT 'Unique run identifier',
    question_id         VARCHAR       NOT NULL               COMMENT 'Q1–Q5 identifier',
    question_text       VARCHAR       NOT NULL               COMMENT 'The natural-language question',
    path                VARCHAR       NOT NULL               COMMENT 'GOVERNED or UNGOVERNED',
    run_number          INTEGER       NOT NULL               COMMENT '1–5 within each (question, path)',
    generated_sql       VARCHAR                              COMMENT 'SQL produced by the LLM or Cortex Analyst',
    answer_numeric      NUMBER(38,6)                         COMMENT 'Numeric answer if applicable',
    answer_text         VARCHAR                              COMMENT 'Full text answer',
    error               VARCHAR                              COMMENT 'Error message if query failed',
    run_at              TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() COMMENT 'When this run was recorded',

    CONSTRAINT pk_experiment PRIMARY KEY (experiment_id)
)
COMMENT = 'Phase 7a governance experiment: measures divergence between governed (semantic view) and ungoverned (raw LLM SQL) paths over the same data and questions.';
