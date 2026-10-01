PHASE 6a — the provenance spine and the Cortex Agent.
Read CORTEX.md and docs/architecture.md (sections 5 and 8) first.

Available: PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC (7 governed metrics, 10 verified
queries) and PAPERTRAIL.GOLD.REGULATION_SEARCH (72 clauses, 11/12 top-1).

1. GOVERNANCE TABLES — sql/08-governance.sql, idempotent.
   Create GOVERNANCE.FINDINGS and GOVERNANCE.FINDING_FOOTNOTES exactly as
   docs/architecture.md section 8 specifies. The hard requirement: any figure
   appearing in a finished finding must resolve to
     (a) the governed metric definition it came from
     (b) the exact SQL that produced it
     (c) the source row keys behind that SQL
     (d) the regulation clause that makes it matter
   Design the columns so all four are recoverable for every footnote. Include a
   content hash on the finding and an append-only created_at. Add comments
   explaining why each column exists.

2. CORTEX AGENT — create a Cortex Agent that has BOTH tools:
   - Cortex Analyst over PAPERTRAIL_SEMANTIC for anything numeric
   - Cortex Search over REGULATION_SEARCH for anything about rules or policy
   Write explicit tool-routing instructions so it uses Analyst for figures and
   Search for regulatory questions, and BOTH when a question needs a number
   justified by a rule.
   Its system prompt must enforce the product's core rule: it may not state a
   figure it cannot attribute to governed SQL. If it cannot ground a number, it
   must say so rather than estimate. Make this a structural instruction, not a
   politeness request.
   Put the DDL in sql/09-agent.sql, idempotent.

3. TEST the agent on five questions and report, for each, which tool(s) it
   chose, the answer, and whether the routing was correct:
   a) "What was our total suspicious transaction volume last quarter?"       -> expect Analyst
   b) "How quickly must a confirmed sanctions match be reported?"            -> expect Search
   c) "Our structuring alerts are up this quarter. How many, and what does
       our AML policy require us to do about them?"                          -> expect BOTH
   d) "Which counterparties breach our concentration limit, and what is the
       limit?"                                                               -> expect BOTH
   e) "What will next quarter's suspicious volume be?"                       -> expect a REFUSAL;
       it cannot know this and must not estimate. Report exactly what it said.

   Be honest about mis-routing or any case where it invented a number.

4. Suspend PAPERTRAIL_WH.

Report the table design rationale, the agent config, and the full routing test.
