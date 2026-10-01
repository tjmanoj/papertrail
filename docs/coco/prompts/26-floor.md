Apply a minimum-baseline floor to the VELOCITY_SPIKE detector in
evals/run_eval.py. This is the last change to the detectors.

JUSTIFICATION, which must be quoted in the code comment and the report:
  TXN Monitoring §2.3: "Monetary thresholds used in monitoring rules must be
  reviewed semi-annually and recalibrated against transaction volume
  distributions. Internal thresholds (e.g., velocity multiples, dormancy
  windows) may be tightened but must not be relaxed below the levels specified
  in the AML Policy without MLRO sign-off."
  A floor TIGHTENS the rule, which §2.3 permits; it does not relax it.

EVIDENCE that the floor is warranted, from the data distribution:
  97 counterparties trip the 5x rule. 32 of them have a trailing average below
  5 transactions per month. The worst ratios (54x, 48x, 37x) all come from a
  trailing average of exactly 1 - a single batch against a baseline of one.
  The multiplier is not statistically meaningful at those volumes.

RULES:
 - Derive the floor from the VOLUME DISTRIBUTION, not from the answer key. Pick
   it by looking at where the trailing-average distribution makes a 5x ratio
   meaningful, and state your reasoning. Do NOT try several values and keep
   whichever maximises F1, and do not check which counterparties are planted.
 - State the chosen floor and its justification in a code comment and in the report.

Then:
 1. Re-run the harness and report the new scorecard.
 2. Update evals/report.md: the floor, its §2.3 justification, the distribution
    evidence, and the new figures.
 3. In the report, state plainly that CP-VELOCITY-00 remains a FALSE NEGATIVE
    and explain why - its trailing baseline is high enough that no single month
    reaches 5x, so catching it would require relaxing the multiplier below the
    AML Policy level, which §2.3 forbids without MLRO sign-off. We are not doing
    that to improve a score.
 4. Add a short section to the report titled "Why this is not 100%" making the
    case that a perfect score against self-authored data, detectors and answer
    key would be less credible than a measured one, and listing what we chose
    NOT to do: no tuning to the key, no dropping the weak typology, no
    loosening of ground truth.

Suspend PAPERTRAIL_WH. Report the before/after scorecard.
