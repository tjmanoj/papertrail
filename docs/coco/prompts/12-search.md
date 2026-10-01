PHASE 5b — Cortex Search over the regulatory corpus. Read CORTEX.md first.

State: data/out/ now has 11 regulatory documents and 72 clauses (28,413 chars),
plus 11 real PDFs in data/out/pdf/. Only regulatory_document.csv and
regulatory_document_clause.csv changed; all other CSVs are byte-identical to
what is already loaded, so do NOT reload the transaction or entity tables.

1. Reload ONLY the two regulatory tables into PAPERTRAIL.RAW (TRUNCATE + COPY).
   Confirm 11 documents and 72 clauses land.

2. UNSTRUCTURED PROCESSING - this is a judged capability, so make it real.
   Create a stage PAPERTRAIL.RAW.REGULATORY_PDF_STAGE, PUT all 11 PDFs into it,
   then use AI_PARSE_DOCUMENT to parse them inside Snowflake. Persist the parsed
   output into a table RAW.REGULATORY_DOCUMENT_PARSED with the document id, the
   extracted text, and page count. Report how the parsed text compares to the
   clause text we already hold - this proves we can ingest a PDF we were handed
   rather than only data we generated.

3. Create a CORTEX SEARCH SERVICE named PAPERTRAIL.GOLD.REGULATION_SEARCH over
   the clause corpus. Index the clause text, and make document title, document
   type, clause number, clause title and jurisdiction available as attributes so
   every hit can be cited precisely. Pick a sensible TARGET_LAG and warehouse.

4. TEST RETRIEVAL PRECISION - the important part. The corpus deliberately
   contains confusable neighbours: 17 clauses mentioning deadlines (24h / 48h /
   72h / 3, 5, 10 business days), 13 about dormancy, 13 with dollar thresholds.
   Run these and report, for EACH: the query, the top 3 hits with their clause
   numbers and documents, and whether the TOP hit is the correct clause:
     a) How quickly must a confirmed sanctions match be reported?
     b) What is the deadline for filing a suspicious transaction report?
     c) What transaction pattern counts as structuring?
     d) When does an account count as dormant?
     e) What is the maximum permitted exposure to a single counterparty?
     f) How long must we retain investigation records?
   Be honest where the top hit is wrong or ambiguous. I want the real precision
   figure, not a flattering one. State it as correct-top-hits / 6.

5. Write the DDL into sql/07-search.sql, idempotent. Suspend PAPERTRAIL_WH.

Report: load confirmation, AI_PARSE_DOCUMENT results, the search service, and
the full retrieval precision table.
