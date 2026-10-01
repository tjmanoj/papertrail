Fix two broken detectors in evals/run_eval.py. Read the file first.

Current honest scorecard:
  STRUCTURING           P1.000 R1.000 F1.000   good
  DORMANT_REACTIVATION  P1.000 R1.000 F1.000   good
  SANCTIONS_NEAR_MATCH  P1.000 R1.000 F1.000   good, and correctly rejected the
                                                known false positive
  ROUND_TRIPPING        P0.333 R1.000 F0.500   6 false positives
  VELOCITY_SPIKE        P0.050 R0.667 F0.093   38 false positives
  MULE_NETWORK          P0.000 R0.000 F0.000   found none of 5 - broken
  OVERALL               F0.324

THE RULE THAT MATTERS: you may NOT tune against ground_truth.csv. Do not look at
which counterparties are in it and work backwards. Do not add id patterns, do not
special-case CP-MULE or CP-VELOCITY prefixes, do not adjust a threshold because
it makes a known positive appear.

What you MAY do - and what I want - is derive each detector from the THRESHOLD
THE REGULATION ACTUALLY STATES. Read the clause text in
RAW.REGULATORY_DOCUMENT_CLAUSE and implement what it says. If AML policy 8.1
defines a velocity spike as exceeding 5 times the trailing average, implement
exactly that rather than an arbitrary cut-off. That is tuning to the policy,
which is the whole thesis of the product, and it is defensible to a judge.

Do this:

1. MULE_NETWORK is finding nothing. Diagnose why before changing it - read the
   clause (around 9.1 in the AML policy), read how the typology is actually
   planted in data/generate.py, and tell me what the detector was looking for
   versus what exists. Then implement the clause faithfully. The pattern is
   several unrelated individuals receiving from a common originator and
   forwarding to a common beneficiary inside a short window.

2. VELOCITY_SPIKE throws 38 false positives. Find the threshold the clause
   states and implement it exactly, including any sustained-period or minimum
   volume qualifier the clause carries. Do not simply raise a number until the
   count drops.

3. ROUND_TRIPPING has 6 false positives. Check the clause for the tolerance and
   window it specifies and apply them.

4. For each detector, add a comment naming the clause it implements and quoting
   the operative sentence, so a reader can check the detector against the rule.

5. Re-run the harness and show me the new scorecard. Report honestly - if a
   typology is still weak, say so and explain what the clause does not give you
   enough to detect.

Suspend PAPERTRAIL_WH. Report the before/after and the clause each detector now
implements.
