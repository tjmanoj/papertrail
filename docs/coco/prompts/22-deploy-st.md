Deploy the Streamlit app to Snowflake. The files exist:
  streamlit/papertrail_app.py  (591 lines)
  streamlit/environment.yml

Do this and nothing else:

1. Create stage PAPERTRAIL.GOLD.STREAMLIT_STAGE if needed.
2. PUT both files into it (the repo path contains a space - quote it).
   Absolute dir: /Users/manoj/Documents/Tj/h2skill/snowflake coco/papertrail/streamlit/
3. CREATE OR REPLACE STREAMLIT PAPERTRAIL.GOLD.PAPERTRAIL_APP
     ROOT_LOCATION = '@PAPERTRAIL.GOLD.STREAMLIT_STAGE'
     MAIN_FILE = 'papertrail_app.py'
     QUERY_WAREHOUSE = PAPERTRAIL_WH;
4. SHOW STREAMLITS IN SCHEMA PAPERTRAIL.GOLD - confirm it exists and report its
   url_id so I can construct the Snowsight URL.
5. Write all of this into sql/11-streamlit.sql, idempotent.
6. Suspend PAPERTRAIL_WH.

If the app fails to create, report the exact error - do not rewrite the app code
to work around it without telling me what was wrong.
