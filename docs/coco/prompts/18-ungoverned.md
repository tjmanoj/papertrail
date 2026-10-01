Run the UNGOVERNED half of the governance experiment.
GOVERNANCE.GOVERNANCE_EXPERIMENT exists and is empty. Read its DDL first and
match its columns; adapt it if needed.

BE EFFICIENT - do not make 25 separate agent round-trips. Generate in bulk:

1. Build the raw DDL context string once: the CREATE TABLE statements for
   RAW.TRANSACTION, RAW.ACCOUNT, RAW.COUNTERPARTY, RAW.ALERT, RAW.CASE_INVESTIGATION
   including column comments. This is the ungoverned analyst's full context -
   generous and fair.

2. In ONE SQL statement, generate 25 candidate queries: a VALUES list of the 5
   questions CROSS JOINed with run numbers 1-5, each row calling
   AI_COMPLETE('claude-sonnet-5', <ddl_context> || <instruction> || <question>)
   asking for a single Snowflake SQL query and nothing else. Persist the raw
   generations to a staging table.

   The 5 questions:
   a) What was the total suspicious transaction volume for Q3 2026?
   b) What is our total exposure to counterparty CP-STRUCT-01?
   c) What was the alert closure rate for 2026?
   d) What share of investigation cases resulted in a SAR filing?
   e) How many high risk counterparties do we have in Singapore?

   FAIRNESS: do not mention reversals, pending status, value vs booking date,
   entity resolution, cohort vs snapshot, or any governance decision in the
   prompt. Ask for correct SQL and nothing more. Do not reveal governed answers.

3. Strip markdown fences from each generation, then EXECUTE each of the 25
   queries one by one. Record into GOVERNANCE_EXPERIMENT with path='UNGOVERNED':
   question, run_number, generated_sql, answer_numeric, error.
   A query that errors is a legitimate result - record the error, never retry
   until it succeeds.

4. Report per question: the distinct numeric answers, min, max, spread, and how
   many of the 5 runs errored.

Suspend PAPERTRAIL_WH. Report the table only.
