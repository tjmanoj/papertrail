-- 06-semantic.sql — Deploy the governed semantic view
-- Idempotent: CREATE OR REPLACE, safe to re-run.
--
-- Source of truth: semantic/papertrail_semantic.sv.yaml
-- Deploy with:
--   cortex agent-studio sv-deploy \
--     --file-path semantic/papertrail_semantic.sv.yaml \
--     --fqn PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC
--
-- Or run this file after staging the YAML:

USE WAREHOUSE PAPERTRAIL_WH;
USE DATABASE PAPERTRAIL;
USE SCHEMA GOLD;

-- Stage for semantic view YAML
CREATE STAGE IF NOT EXISTS PAPERTRAIL.GOLD.SEMANTIC_STAGE
  COMMENT = 'Holds semantic view YAML definitions for deployment';

-- After uploading the YAML to the stage with:
--   PUT file://semantic/papertrail_semantic.sv.yaml @PAPERTRAIL.GOLD.SEMANTIC_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--
-- Deploy:
--   SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
--     'PAPERTRAIL.GOLD',
--     SNOWFLAKE.CORTEX.READ_FILE('@PAPERTRAIL.GOLD.SEMANTIC_STAGE/papertrail_semantic.sv.yaml')
--   );
--
-- For CI/CD or one-command rebuild, use the cortex CLI deploy shown above.
-- The semantic view is CREATE-OR-REPLACE internally, so re-runs are safe.
