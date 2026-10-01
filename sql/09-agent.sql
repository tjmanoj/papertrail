-- 09-agent.sql — PaperTrail Cortex Agent (Analyst + Search)
-- Idempotent: CREATE OR REPLACE, safe to re-run.
-- Prerequisites:
--   06-semantic.sql  → PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC
--   07-search.sql    → PAPERTRAIL.GOLD.REGULATION_SEARCH

USE DATABASE PAPERTRAIL;
USE SCHEMA GOLD;
USE WAREHOUSE PAPERTRAIL_WH;

CREATE OR REPLACE AGENT PAPERTRAIL.GOLD.PAPERTRAIL_AGENT
  COMMENT = 'Risk and regulatory copilot — routes numeric questions through governed SQL, regulatory questions through clause search'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto

  instructions:
    response: >
      You are PaperTrail, a compliance copilot for a bank's AML/CTF team.
      Your answers must be precise, auditable, and grounded in governed data.

      ABSOLUTE RULES — these override everything else:

      1. NEVER state, estimate, project, or forecast a number you did not
         obtain from the Risk_Analyst tool in the current conversation turn.
         If you cannot retrieve a figure, say "I cannot determine this from
         governed data" and explain what is missing. Do not approximate.

      2. When citing a regulatory requirement, always retrieve the specific
         clause using the Regulation_Search tool. Do not paraphrase regulations
         from memory.

      3. When a question involves BOTH a number AND a regulatory requirement,
         use BOTH tools: Risk_Analyst for the figure, Regulation_Search for
         the applicable clause. Combine them in your answer.

      4. For questions about future values, predictions, or forecasts: refuse.
         State that PaperTrail reports governed historical data and cannot
         project future values.

      Format currency values with a dollar sign and commas. Format percentages
      to two decimal places. Keep answers concise and professional.

    orchestration: >
      TOOL ROUTING — follow these rules strictly:

      - Questions asking for counts, totals, rates, averages, volumes, scores,
        or any quantitative metric: use Risk_Analyst.

      - Questions asking about rules, policies, regulations, thresholds,
        reporting requirements, or what a regulation says: use Regulation_Search.

      - Questions that need BOTH a number AND a regulatory citation (e.g.
        "how many X and what does the policy say about it"): use BOTH tools.
        Call Risk_Analyst first for the data, then Regulation_Search for the
        applicable regulation.

      - Questions about future projections or estimates: do NOT call either
        tool. Decline the question directly.

  tools:
    - tool_spec:
        type: "cortex_analyst_text_to_sql"
        name: "Risk_Analyst"
        description: >
          Generates governed SQL over the PaperTrail semantic view to answer
          quantitative AML/CTF compliance questions: suspicious transaction
          volumes, counterparty exposure, alert closure rates, SAR filing
          rates, structuring indicator scores, case resolution times, and
          high-risk counterparty counts. Use this for ANY question that
          requires a number.

    - tool_spec:
        type: "cortex_search"
        name: "Regulation_Search"
        description: >
          Searches the regulatory clause corpus (AML/CTF policies, sanctions
          screening procedures, transaction monitoring rules, SAR filing
          guidelines) to find specific regulatory requirements, thresholds,
          reporting timelines, and compliance obligations. Use this for ANY
          question about what a regulation requires, what a policy says, or
          what the compliance obligations are.

  tool_resources:
    Risk_Analyst:
      semantic_view: "PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC"
      execution_environment:
        type: warehouse
        warehouse: "PAPERTRAIL_WH"

    Regulation_Search:
      search_service: "PAPERTRAIL.GOLD.REGULATION_SEARCH"
      max_results: "5"
      columns_and_descriptions:
        SEARCH_TEXT:
          description: "Enriched text combining document title, clause title, clause number, and full clause body"
          type: "string"
          searchable: true
          filterable: false
        CLAUSE_TEXT:
          description: "The full text of the regulatory clause"
          type: "string"
          searchable: false
          filterable: false
        DOCUMENT_TITLE:
          description: "Title of the regulatory document this clause belongs to"
          type: "string"
          searchable: false
          filterable: true
        DOCUMENT_TYPE:
          description: "Type of regulatory document (POLICY, PROCEDURE, GUIDELINE)"
          type: "string"
          searchable: false
          filterable: true
        CLAUSE_NUMBER:
          description: "Section number of the clause (e.g. 3.1, 4.2)"
          type: "string"
          searchable: false
          filterable: false
        CLAUSE_TITLE:
          description: "Title of the specific clause within the document"
          type: "string"
          searchable: false
          filterable: false
        JURISDICTION:
          description: "Jurisdiction this regulation applies to (AU, SG, or BOTH)"
          type: "string"
          searchable: false
          filterable: true
        CLAUSE_ROLE:
          description: "Whether this clause DEFINES, OPERATIONALISES, or REFERENCES a rule"
          type: "string"
          searchable: false
          filterable: true
  $$;
