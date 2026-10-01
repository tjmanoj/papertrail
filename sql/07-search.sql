-- 07-search.sql — Cortex Search over the regulatory clause corpus
-- Idempotent: CREATE OR REPLACE / IF NOT EXISTS throughout.
-- Prerequisite: 01-raw.sql (creates regulatory tables), 02-load.sql (loads data).

USE DATABASE PAPERTRAIL;
USE SCHEMA RAW;
USE WAREHOUSE PAPERTRAIL_WH;

-- ============================================================
-- 1. PDF Stage for unstructured regulatory documents
-- ============================================================
CREATE STAGE IF NOT EXISTS REGULATORY_PDF_STAGE
  DIRECTORY = (ENABLE = TRUE)
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
  COMMENT = 'Internal stage for regulatory policy PDFs parsed by AI_PARSE_DOCUMENT';

-- After running this script, upload PDFs with:
--   PUT 'file:///.../data/out/pdf/<DOC-ID>.pdf' @PAPERTRAIL.RAW.REGULATORY_PDF_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE
-- Then refresh the directory:
--   ALTER STAGE REGULATORY_PDF_STAGE REFRESH;

-- ============================================================
-- 2. Parsed-document table (AI_PARSE_DOCUMENT output)
-- ============================================================
CREATE OR REPLACE TABLE REGULATORY_DOCUMENT_PARSED (
    document_id       VARCHAR        NOT NULL  COMMENT 'FK → REGULATORY_DOCUMENT, derived from PDF filename',
    filename          VARCHAR        NOT NULL  COMMENT 'PDF filename on stage',
    parsed_content    VARIANT        NOT NULL  COMMENT 'Full AI_PARSE_DOCUMENT JSON output',
    extracted_text    VARCHAR                  COMMENT 'Concatenated page text from parsed output',
    page_count        NUMBER                   COMMENT 'Number of pages in the PDF',
    parsed_at         TIMESTAMP_NTZ  NOT NULL  DEFAULT CURRENT_TIMESTAMP() COMMENT 'When parsing occurred',

    CONSTRAINT pk_reg_doc_parsed PRIMARY KEY (document_id)
)
COMMENT = 'AI_PARSE_DOCUMENT output for regulatory PDFs — proves we can ingest PDFs we are handed';

-- Populate from staged PDFs (re-runnable: table is replaced above)
INSERT INTO REGULATORY_DOCUMENT_PARSED
  (document_id, filename, parsed_content, extracted_text, page_count)
WITH raw_parsed AS (
    SELECT
        REPLACE(relative_path, '.pdf', '') AS document_id,
        relative_path                      AS filename,
        AI_PARSE_DOCUMENT(
            TO_FILE('@PAPERTRAIL.RAW.REGULATORY_PDF_STAGE', relative_path),
            {'mode': 'OCR'}
        ) AS parsed_result
    FROM DIRECTORY(@PAPERTRAIL.RAW.REGULATORY_PDF_STAGE)
)
SELECT
    document_id,
    filename,
    parsed_result                          AS parsed_content,
    parsed_result:content::VARCHAR         AS extracted_text,
    parsed_result:metadata:pageCount::INT  AS page_count
FROM raw_parsed;

-- ============================================================
-- 3. Cortex Search Service — clause-level retrieval
-- ============================================================
-- The search column is an enriched composite of document title, clause title,
-- clause number, document type, and clause text.  This lets the embedding model
-- see topical context (e.g. "Sanctions Screening" in the title) that would
-- otherwise be invisible when the index only covers clause_text.
--
-- clause_role is a derived attribute that distinguishes clauses that DEFINE or
-- SET a rule from those that merely REFERENCE or RECORD-KEEP about it.  The
-- derivation uses general text-pattern heuristics, not the eval test set.
-- ============================================================
USE SCHEMA GOLD;

CREATE OR REPLACE CORTEX SEARCH SERVICE REGULATION_SEARCH
  ON search_text
  PRIMARY KEY (clause_id)
  ATTRIBUTES document_title, document_type, clause_number, clause_title, clause_text, jurisdiction, clause_role
  WAREHOUSE = PAPERTRAIL_WH
  TARGET_LAG = '1 day'
  EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
  COMMENT = 'Hybrid search over regulatory clauses — powers the provenance copilot'
AS (
    SELECT
        c.clause_id,

        -- Enriched search column: topical context + full clause body
        d.title || ' — ' || c.clause_title
            || ' (§' || c.clause_number || ', ' || d.document_type || '): '
            || c.clause_text
            AS search_text,

        -- Original fields kept as attributes for citation / display
        c.clause_text,
        d.title        AS document_title,
        d.document_type,
        c.clause_number,
        c.clause_title,
        d.jurisdiction,

        -- Derived clause role — general heuristic, NOT fitted to eval queries.
        -- Priority order: REFERENCES first (record-keeping / cross-ref clauses),
        -- then DEFINES (clauses that establish rules), else OPERATIONALISES.
        CASE
            WHEN LOWER(c.clause_text) RLIKE '.*(must be retained|must be documented|must be logged|must maintain a log|retention period|retrieval standard|disposal|record.keeping|audit trail).*'
                 AND NOT LOWER(c.clause_title) RLIKE '.*(detection|screening|monitoring|threshold|trigger|filing threshold|escalation).*'
            THEN 'REFERENCES'
            WHEN LOWER(c.clause_text) RLIKE '.*(defined as|shall maintain automated|shall monitor|must be initiated when|must be filed|must be screened|must be reported|must occur within|must be conducted|must generate|shall generate|shall not|has zero tolerance).*'
                 OR LOWER(c.clause_title) RLIKE '.*(detection|definition|trigger|identification|scope|threshold|filing threshold|escalation path).*'
            THEN 'DEFINES'
            ELSE 'OPERATIONALISES'
        END AS clause_role

    FROM PAPERTRAIL.RAW.REGULATORY_DOCUMENT_CLAUSE c
    JOIN PAPERTRAIL.RAW.REGULATORY_DOCUMENT d
      ON c.document_id = d.document_id
);

-- ============================================================
-- 4. Suspend warehouse (cost discipline)
-- ============================================================
ALTER WAREHOUSE PAPERTRAIL_WH SUSPEND;
