One last honest attempt at VELOCITY_SPIKE in evals/run_eval.py, then we report
whatever we get.

Current: P 0.065, R 0.667, F 0.118 — 29 false positives, 2 of 3 true positives.
Every other typology now scores F1 1.000.

The detector implements the numeric half of the rule but not all of it. Two
parts of the policy are unimplemented:

  AML Policy §8.1, second sentence: "The monitoring system must distinguish
  between legitimate seasonal increases (e.g., payroll periods) and anomalous
  spikes indicative of layering or account takeover."

  TXN Monitoring §5.4: "For BUSINESS-type accounts with established seasonal
  patterns the multiplier may be raised to 8x... The multiplier must never
  exceed 10x regardless of account type."

  PEP Handling §3.1: "the velocity multiplier is reduced from 5x to 3x" for PEPs.

Do this:

1. Implement the differentiated multipliers the clauses actually specify:
   3x for PEP counterparties, 8x for BUSINESS-type accounts, 5x otherwise.
   Never above 10x.

2. Attempt the §8.1 seasonality discriminator as far as the clause supports.
   A spike that recurs at a regular interval across the trailing window is
   seasonal; a one-off spike against an otherwise flat baseline is anomalous.
   Implement something defensible from the data you have. If the clause does
   not give you enough to do this properly, implement what you can and SAY SO.

3. STILL NO TUNING AGAINST GROUND TRUTH. Do not look up which counterparties
   are planted. Every threshold must trace to a quoted clause.

4. Re-run and report the new scorecard.

5. Then give me an honest verdict on one question: after implementing everything
   the clauses actually specify, is the residual false-positive rate a defect in
   our detector, or a property of a policy that states a precise number and a
   vague qualitative test? Answer plainly either way - do not reach for the
   flattering interpretation. If our detector is still weak, say it is weak.

Suspend PAPERTRAIL_WH.
