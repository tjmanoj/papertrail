Improve retrieval precision on PAPERTRAIL.GOLD.REGULATION_SEARCH.

BASELINE (measured, keep it - we will report the before/after):
  top-1 precision 4/6, top-3 6/6.
  Misses: (a) "How quickly must a confirmed sanctions match be reported?" ranked
  DOC-RECORD-RETENTION-4-1 above the correct DOC-SANCTIONS-PROC-4-1.
  (c) "What transaction pattern counts as structuring?" ranked the variants
  clause DOC-TXN-MONITORING-8-1 above the canonical definition DOC-AML-POLICY-5-2.

Diagnosis to test: the indexed text is clause_text alone, so topical signal that
lives in clause_title and document_title is invisible to the index, and a
record-keeping clause that merely MENTIONS a deadline outranks the operational
clause that SETS it.

Do this:

1. Rebuild the search service indexing an enriched search column - a composite of
   document_title, document_type, clause_number, clause_title and clause_text,
   so topical context is searchable, while keeping all five fields available as
   attributes for citation. Keep the service name and keep the DDL idempotent in
   sql/07-search.sql.

2. Consider whether a clause's ROLE should be explicit - e.g. a derived attribute
   distinguishing a clause that DEFINES or SETS a rule from one that merely
   REFERENCES it for record-keeping. If you add such a signal, derive it from the
   text rather than hand-labelling the six test cases - I do not want the test
   set fitted.

3. IMPORTANT: do not tune against only these 6 queries. Add 6 more realistic
   analyst questions of your own covering other parts of the corpus, so we
   measure on 12 and cannot accidentally overfit. State your 6 additions and the
   clause you consider correct for each, with reasoning.

4. Re-measure on all 12 and report a table: query, top hit, correct clause,
   correct at top-1 Y/N, correct within top-3 Y/N.
   Give final precision as top-1 X/12 and top-3 Y/12, plus the original 6 scored
   separately so the before/after on those is directly comparable.

5. Be honest. If the change does not help, say so and revert rather than
   reporting a number you had to massage.

Suspend PAPERTRAIL_WH. Report the before/after clearly.
