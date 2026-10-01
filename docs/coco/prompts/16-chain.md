Finish Phase 6b. The four skills already exist under skills/ with SKILL.md and
README.md each, plus skills/README.md. Do NOT rewrite them.

1. REGISTER: run `cortex skill add ./skills` (or the correct invocation for a
   directory of skills) and then `cortex skill list` to confirm all four are
   discovered. Report the exact commands and the output.

2. PROVE THE CHAIN END TO END. Pick a counterparty from our data with genuine
   structuring signal - the planted structuring typology counterparties are
   prefixed CP-STRUCT. Then run the four skills in sequence for real:
     risk-scanner    -> provenance bundle(s) for the relevant governed metrics
     regulation-linker -> the AML policy clause(s) that govern structuring
     finding-writer  -> the assembled finding text with footnote markers
     provenance-logger -> persist to GOVERNANCE.FINDINGS + FINDING_FOOTNOTES

   Actually execute this. Do not simulate it or describe what would happen.

3. SHOW ME THE EVIDENCE:
   a) the full finding text as written
   b) SELECT the finding row from GOVERNANCE.FINDINGS including its content_hash
   c) SELECT its footnote rows from GOVERNANCE.FINDING_FOOTNOTES
   d) For ONE footnote, walk the complete resolution chain and show each step:
        the figure as it appears in the finding
        -> the governed metric definition it came from
        -> the exact generated SQL
        -> the source row ids
        -> the regulation clause number and text
      Then RE-RUN that stored SQL and confirm it still returns the same figure.
      That last step is the whole product - a number that can be re-derived
      from its own footnote.

4. Test the guarantee: show what finding-writer does when handed a figure that
   is NOT in any provenance bundle. It must fail validation rather than emit
   the finding. Report what actually happened.

5. Suspend PAPERTRAIL_WH.

Be honest if any step fails. Report the registration output and all the evidence.
