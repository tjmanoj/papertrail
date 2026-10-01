Continue Phase 4. The semantic view YAML already exists at
semantic/papertrail_semantic.sv.yaml (46 KB, 10 verified queries). Do NOT
regenerate or redesign it.

1. Deploy it to Snowflake as PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC using
   `cortex agent-studio sv-deploy` (or SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML).
   Confirm with SHOW SEMANTIC VIEWS that it exists.

2. Write the deploy step into sql/06-semantic.sql, idempotent.

3. VALIDATE with Cortex Analyst against the deployed view. Ask each question
   below and report in a table: the question, the SQL Analyst generated, the
   answer it returned, and PASS/FAIL on whether the SQL honoured the governed
   semantics defined in docs/data-model.md section 2.
     a) What was our total suspicious transaction volume last quarter?
     b) Which counterparties have the highest exposure?
     c) What is our alert closure rate this year?
     d) How many high risk counterparties do we have in Singapore?
     e) What share of cases resulted in a SAR filing?

   For each, check specifically: did it exclude reversals where it should, use
   the correct date basis, scope the denominator correctly, and use the
   entity-resolved exposure rather than direct-only?

   BE HONEST about failures. I need the true accuracy rate, not a flattering
   summary. If Analyst ignored a governance rule, say so and quote the SQL.

4. Suspend PAPERTRAIL_WH.

Report the deployment result and the full validation table.
