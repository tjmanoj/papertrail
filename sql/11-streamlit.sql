-- 11-streamlit.sql  Deploy PaperTrail Streamlit app (idempotent)
-- Requires: papertrail_app.py and environment.yml already PUT to the stage.

CREATE STAGE IF NOT EXISTS PAPERTRAIL.GOLD.STREAMLIT_STAGE;

-- PUT commands (run from local machine, not in worksheet):
-- PUT 'file:///.../streamlit/papertrail_app.py' @PAPERTRAIL.GOLD.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- PUT 'file:///.../streamlit/environment.yml'    @PAPERTRAIL.GOLD.STREAMLIT_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

CREATE OR REPLACE STREAMLIT PAPERTRAIL.GOLD.PAPERTRAIL_APP
  ROOT_LOCATION  = '@PAPERTRAIL.GOLD.STREAMLIT_STAGE'
  MAIN_FILE      = 'papertrail_app.py'
  QUERY_WAREHOUSE = PAPERTRAIL_WH;

ALTER WAREHOUSE PAPERTRAIL_WH SUSPEND;
