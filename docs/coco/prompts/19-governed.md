Run the GOVERNED half of the experiment, then do the real analysis.

The ungoverned half is recorded (25 rows, path='UNGOVERNED'). It showed ZERO
variance - identical SQL every run. So the hypothesis that an ungoverned LLM is
inconsistent is WRONG, and we will not pretend otherwise. The real question is
whether it is CORRECT.

1. Run the same 5 questions through Cortex Analyst over PAPERTRAIL_SEMANTIC,
   N=3 each (3 is enough since we are testing stability, not sampling).
   Record into GOVERNANCE_EXPERIMENT with path='GOVERNED': question, run_number,
   generated_sql, answer_numeric. Report whether the governed path was stable.

2. THE REAL ANALYSIS. For each of the 5 questions produce:
   - the ungoverned answer
   - the governed answer
   - the absolute and relative difference
   - AGREE or DIVERGE
   - where they diverge, the SPECIFIC governance decision the ungoverned SQL
     missed. Diff the two SQL statements and name the cause precisely - did it
     include reversals, use booking date instead of value date, count pending,
     use direct exposure instead of entity-resolved, include stale risk ratings,
     scope the alert status differently? Quote the relevant fragment of each
     query as evidence.

   I expect Q1 (8,797,923 ungoverned vs ~4,295,229 governed) and Q5 (23 vs 36)
   to diverge, and Q2/Q3/Q4 to agree. Confirm or correct that.

3. State the honest headline. Something of this shape if the data supports it:
   the ungoverned path is perfectly consistent and perfectly confident, and on
   N of 5 questions it is materially wrong, with no signal to the reader that
   anything is wrong. Give the real N and the real magnitudes.

4. Rewrite docs/governance-experiment.md with: the method, the fairness rules,
   the full results, the per-question SQL diffs, and the honest conclusion -
   including the fact that our original hypothesis about variance was not
   supported. A reader must be able to see we reported what we found rather
   than what we wanted.

Suspend PAPERTRAIL_WH. Report the comparison table and the headline.
