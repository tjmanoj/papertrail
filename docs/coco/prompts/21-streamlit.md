Write a Streamlit in Snowflake app. WRITE FILES ONLY - do not deploy, do not
query Snowflake, do not read other files. Everything you need is below. Start
writing immediately.

Create streamlit/papertrail_app.py and streamlit/environment.yml.

Runs inside Snowflake, so use:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
No connection handling needed.

OBJECTS IT READS (all exist):
  PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC      semantic view, 7 metrics, 10 verified queries
  PAPERTRAIL.GOLD.REGULATION_SEARCH        cortex search, 72 clauses
  PAPERTRAIL.GOLD.PAPERTRAIL_AGENT         cortex agent (Risk_Analyst + Regulation_Search tools)
  PAPERTRAIL.GOVERNANCE.FINDINGS           finding_id, finding_text, content_hash, created_at
  PAPERTRAIL.GOVERNANCE.FINDING_FOOTNOTES  footnote_number, metric_name, metric_definition,
                                           generated_sql, result_value, source_row_ids,
                                           source_table, clause_number, clause_text_excerpt
  PAPERTRAIL.GOVERNANCE.GOVERNANCE_EXPERIMENT  question, path('GOVERNED'|'UNGOVERNED'),
                                           run_number, generated_sql, answer_numeric
  PAPERTRAIL.GOLD.FACT_TRANSACTION / DIM_COUNTERPARTY / DIM_ACCOUNT / FACT_ALERT / FACT_CASE
  PAPERTRAIL.CURATED.*                     4 dynamic tables

Use SELECT ... with column names defensively (SELECT * then access by name) so a
column-name mismatch degrades gracefully instead of crashing the page. Wrap each
page body in try/except and show a readable message on failure.

FOUR PAGES via st.sidebar.radio:

1. "Ask"
   Text input plus 4 example buttons:
     - What was our total suspicious transaction volume last quarter?
     - How quickly must a confirmed sanctions match be reported?
     - Which counterparties breach our concentration limit, and what is the limit?
     - What will next quarter's suspicious volume be?        <- the agent refuses this
   Call the agent and render the answer. Show tools used and the generated SQL in
   an expander. Caption under the 4th example: "the agent declines to forecast -
   it reports governed historical data only".

2. "Prove"
   Headline, stated exactly: "Both paths are perfectly stable. The ungoverned one
   is confidently wrong on 2 of 5."
   Read GOVERNANCE_EXPERIMENT. Per question show ungoverned vs governed answer,
   the difference, and AGREE / DIVERGE. For divergent ones show both SQL
   statements side by side in columns.
   Hardcode ONLY the explanatory text of what was missed:
     Q1 suspicious volume: booking date instead of value date; reversals included;
        unsettled included; transactions on already-closed alerts counted.
     Q5 high-risk in Singapore: filtered RISK_RATING='HIGH' literally, dropping
        VERY_HIGH entities that KYC policy 2.1 requires be counted.
   Add a note that Q2 agrees only by coincidence - it computes direct exposure
   rather than entity-resolved, and would diverge for any counterparty with
   beneficial-ownership links.

3. "File"
   Select a finding. Render finding_text. Below it list footnotes; for each show
   metric_name, metric_definition, result_value, clause_number, clause_text_excerpt,
   source_table, first 5 source_row_ids, and the generated_sql in an expander.
   A button "Re-run this SQL" executes the stored generated_sql live and shows
   the returned value beside result_value with a match indicator.
   Show content_hash and a note that it is SHA-256 of finding_text.

4. "Evidence"
   Metric tiles from live counts: FACT_TRANSACTION rows, DIM_COUNTERPARTY rows,
   findings, footnotes. Then static facts: 7 governed metrics, 10 verified
   queries, 72 indexed clauses, 11 regulatory PDFs parsed with AI_PARSE_DOCUMENT,
   4 registered CoCo skills, retrieval precision 11/12 top-1 and 12/12 top-3,
   9 dynamic tables.

STYLING - inject CSS via st.markdown(unsafe_allow_html=True):
  dark navy ground #0A1020, panels #121A2B, text #E6ECF5, muted #8EA0B8,
  one cyan accent #35B6E8, borders #223047.
  Hide the Streamlit menu and footer. Tabular numerals on figures
  (font-variant-numeric: tabular-nums). Generous padding. No emoji anywhere.
  Headings in a condensed sans stack. It must read like a compliance tool.

environment.yml: name sf_env, channels snowflake, dependencies python 3.11 plus
streamlit and snowflake-snowpark-python.

Write both files now. Report only the file paths and line counts when done.
