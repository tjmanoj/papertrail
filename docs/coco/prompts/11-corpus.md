PHASE 5a — expand the regulatory corpus and render it as real PDFs.
Read CORTEX.md and docs/data-model.md section 3 first.

WHY: the corpus is currently 6 documents / 18 clauses / 6,468 characters.
Cortex Search over 18 chunks demonstrates nothing - any query looks good. The
real claim is retrieving the CORRECT clause out of many plausible neighbours,
so the corpus needs genuine depth and some deliberately confusable clauses.

CRITICAL CONSTRAINT - do not perturb existing entity IDs.
data/generate.py uses a single global counter for uid(), so inserting new
entities mid-stream would shift every downstream ID and force a full Snowflake
reload of 240k transactions. Avoid that:
  - Generate the expanded regulatory corpus AFTER all other entities, or from a
    separate independently-seeded RNG that does not draw from the shared stream.
  - Afterwards, these files MUST be byte-identical to now (verify by SHA-256):
    account.csv, alert.csv, alert_transaction.csv, case_alert.csv,
    case_investigation.csv, counterparty.csv, transaction.csv,
    watchlist_entry.csv, watchlist_screening_result.csv, ground_truth.csv
    Only regulatory_document.csv and regulatory_document_clause.csv may change.
  Reference hashes are in /private/tmp/claude-501/-Users-manoj-Documents-Tj-h2skill-snowflake-coco/4cc63bea-adc4-4f54-a486-73a857faf1c4/scratchpad/pre-phase5-hashes.txt

WHAT TO BUILD:

1. Expand to roughly 10-12 documents and 70-90 clauses total. Keep the existing
   6 documents and their 18 clauses intact and extend around them. Add document
   types a real AML/risk function holds, e.g.: transaction monitoring standards,
   PEP handling procedure, enhanced due diligence standard, record-keeping and
   retention policy, alert investigation handbook, training and attestation
   policy, trade-finance red flags guidance.

2. Quality requirements for clause text - this is the important part:
   - Each clause 250-600 characters of plausible regulatory prose, numbered in
     the house style already used (e.g. "5.2", with a clause_title).
   - Keep the existing pattern where clauses reference our governed metrics and
     typologies by name, so a finding can cite the clause that justifies it.
   - Include DELIBERATELY CONFUSABLE NEIGHBOURS: several clauses on adjacent
     topics that a naive keyword search would wrongly return. For example more
     than one clause mentioning thresholds and dollar amounts, several
     mentioning reporting deadlines with DIFFERENT deadlines (24 hours vs 72
     hours vs 3 business days), and more than one about dormancy. Retrieval
     precision is only meaningful if wrong answers are available.
   - Every document keeps the synthetic watermark.

3. Render each document as a REAL PDF into data/out/pdf/<document_id>.pdf, with
   the clause numbering and titles visible as structure, and the synthetic
   watermark on every page. reportlab is NOT installed - either pip install it
   into the environment or render via the available `soffice` binary. Your choice,
   but the output must be genuine PDFs, not renamed text files.

4. Regenerate, then VERIFY and report:
   - SHA-256 of all 12 CSVs against the reference list; confirm the 10 unchanged
     files are byte-identical and name the 2 that changed.
   - `python3 data/generate.py --verify-determinism` must still PASS.
   - counts: documents, clauses, total clause characters, clauses per document.
   - the PDFs exist, their page counts, and that they are valid PDFs
     (check the %PDF header and that a text extraction returns the clause text).

Do NOT touch Snowflake in this session. Report concisely.
