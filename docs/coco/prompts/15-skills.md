PHASE 6b — the four reusable CoCo skills. Read CORTEX.md and
docs/architecture.md section 6 first.

THIS IS THE HEADLINE BONUS. The hackathon brief states verbatim: "Reusable and
shareable skills: Publish custom skills or agent skills that other teams could
reuse. Clearly documented, reusable skills remain the headline bonus."
So these must be genuinely reusable by a stranger, not stubs that only work for
our demo. Judge them by: could another team lift one out and use it?

Available: PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC, PAPERTRAIL.GOLD.REGULATION_SEARCH,
PAPERTRAIL.GOLD.PAPERTRAIL_AGENT, GOVERNANCE.FINDINGS, GOVERNANCE.FINDING_FOOTNOTES.

Build four skills under skills/<name>/, each with a SKILL.md carrying proper YAML
frontmatter (name, description) in the format CoCo discovers, plus a README.md
documenting the interface:

1. skills/risk-scanner/
   Runs a governed metric query and returns a provenance bundle:
   {metric, metric_definition, generated_sql, rows, source_row_ids}.
   Never writes. Never generates prose. Only queries and packages evidence.

2. skills/regulation-linker/
   Given a metric name or a risk description, retrieves the governing clause(s)
   via Cortex Search and returns full citation metadata. Pure retrieval - never
   runs analytical SQL, never computes.

3. skills/finding-writer/
   Takes provenance bundles plus clause citations and assembles a formal
   regulatory finding. CRITICAL: it must be structurally incapable of stating a
   figure it was not given - it emits footnote references to the bundles it
   received, so an ungrounded number has no path into the output. Explain in the
   SKILL.md HOW this is enforced, not merely that it is intended.

4. skills/provenance-logger/
   Persists a finished finding and its footnotes to the GOVERNANCE tables,
   append-only, with the content hash. Never updates or deletes.

Requirements for all four:
- Parameterised. No hardcoded counterparty ids, dates or demo values.
- State inputs, outputs, preconditions, failure modes, and a worked example.
- Say explicitly what the skill will NOT do - the boundary is what makes them
  composable.
- Each must be independently runnable, not only as part of the chain.

Then:
5. Register them: `cortex skill add ./skills` (or the correct invocation) and
   confirm with `cortex skill list` that all four are discovered.

6. PROVE THE CHAIN. Run all four end to end on a real case from our data - pick
   a counterparty with genuine structuring signal - to produce one complete
   finding in GOVERNANCE.FINDINGS with its footnotes. Then show me:
   - the finding text
   - its footnote rows, and for ONE footnote, demonstrate the full resolution:
     figure -> metric definition -> exact SQL -> source row ids -> clause
   - confirm the content hash was stored

7. Write skills/README.md as an index explaining how the four compose, suitable
   for another team to read first.

Suspend PAPERTRAIL_WH. Report what was built and the end-to-end proof.
