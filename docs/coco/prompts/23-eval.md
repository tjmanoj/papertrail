PHASE 8 — the scored evaluation. Read CORTEX.md first.

This is the number the submission deck requires under "measurable outcomes", so
it must be real. A flattering number we cannot defend is worse than a modest one
we can.

THE HOLD-OUT RULE: data/out/ground_truth.csv has never been loaded into Snowflake
and must stay that way. The harness reads it LOCALLY and compares against what
Snowflake returns. Do not load it, do not stage it, do not join to it in SQL.

Build evals/run_eval.py — a standalone harness that:

1. Reads data/out/ground_truth.csv locally. It holds 6 planted typologies
   (STRUCTURING, ROUND_TRIPPING, DORMANT_REACTIVATION, VELOCITY_SPIKE,
   MULE_NETWORK, SANCTIONS_NEAR_MATCH) with the counterparty, account,
   transaction and alert ids involved.

2. For each typology, runs a DETECTION query against the governed GOLD layer -
   the kind of query a real surveillance process would run, derived from the
   governed metrics and the thresholds stated in the regulatory clauses. For
   example structuring uses the $8,000-$9,999 band and the clustering rule from
   AML policy section 5.2. Write these as governed SQL, not as lookups of known
   ids - the detector must not know the answer.

3. Scores the result against ground truth at COUNTERPARTY level:
   true positives, false positives, false negatives, then precision, recall and
   F1 per typology AND overall.

   CRITICAL - the sanctions case is the honest test. Ground truth marks
   CP-SANCTIONS-00 as a TRUE positive and CP-SANCTIONS-01 as a FALSE positive
   (a near-match that should NOT be escalated). A detector that flags both gets
   100% recall and looks great. Score precision properly so that flagging the
   false positive COSTS us. Report whether we correctly distinguished them.

4. Writes evals/report.md with: the method, the per-typology table, the overall
   figures, the confusion counts, and an explicit statement of what the harness
   does NOT prove.

5. Prints the summary to stdout.

Then RUN it and show me the real output.

BE HONEST. If recall is poor on a typology, report it and explain why rather
than loosening the detector until it passes. If precision suffers because of the
sanctions false positive, say so. I would rather ship 0.78 F1 that is true than
0.95 that is tuned.

Suspend PAPERTRAIL_WH. Report the scorecard.
