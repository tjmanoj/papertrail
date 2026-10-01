PHASE 7a — the governance experiment. Read CORTEX.md first.

PURPOSE: PaperTrail claims that a governed semantic layer makes the same question
return the same number, while an ungoverned LLM over the same raw tables does not.
Every competing team asserts something like this. We are going to MEASURE it.

THE EXPERIMENT MUST BE FAIR. If we handicap the ungoverned path the result is
worthless and a judge will see through it. Rules:
  - The ungoverned path gets the SAME underlying data, full raw table DDL
    including column comments, and a competent prompt asking it to write correct
    SQL. It is a capable analyst with no semantic layer - not a strawman.
  - Do not tell the ungoverned path the governed answer, and do not hint at the
    governance decisions (reversals, pending, date basis, entity resolution).
    That knowledge living only in the semantic layer is precisely the point.
  - Same questions, same model for both paths where possible.

BUILD IT:

1. Create GOVERNANCE.GOVERNANCE_EXPERIMENT to store every run:
   question, path ('GOVERNED'|'UNGOVERNED'), run_number, generated_sql,
   answer_numeric, answer_text, error, run_at.

2. Pick 5 questions whose answers are genuinely sensitive to the governance
   decisions documented in docs/data-model.md section 2 - that is where
   divergence should appear. Suggested:
   a) total suspicious transaction volume for Q3 2026
   b) exposure to counterparty CP-STRUCT-01
   c) alert closure rate for 2026
   d) SAR filing rate
   e) number of high risk counterparties in Singapore

3. UNGOVERNED PATH: for each question, run N=5 independent attempts. Each
   attempt: give AI_COMPLETE the raw table DDL and the question, ask for a single
   SQL query, then EXECUTE that SQL and record the numeric answer. Record errors
   as errors - a query that fails is a legitimate outcome and must be reported,
   not retried until it works.

4. GOVERNED PATH: the same 5 questions, N=5 each, through Cortex Analyst over
   PAPERTRAIL_SEMANTIC. Record generated SQL and answer.

5. ANALYSE and report a table per question:
   - distinct numeric answers returned by each path
   - min, max, and spread (max/min) where numeric
   - count of failed/errored attempts
   - whether the governed path was stable across all 5 runs
   Then an overall summary: governed distinct-answer count vs ungoverned.

6. Write the result to docs/governance-experiment.md with the method stated
   plainly, including the fairness rules above, so a sceptical reader can judge
   whether the comparison was honest.

BE HONEST. If the ungoverned path happens to be stable on some questions, report
that. If the governed path varies, report that too - it would be a real finding
about our own semantic view. A believable result beats a flattering one.

Put DDL in sql/10-experiment.sql. Suspend PAPERTRAIL_WH.
