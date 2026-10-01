# PaperTrail — Detection Evaluation Report

## Method

Six detection queries run against `PAPERTRAIL.GOLD.*` and `PAPERTRAIL.RAW.WATCHLIST_SCREENING_RESULT`. Each query implements the thresholds and logic stated in the bank's regulatory document clauses — the detector does **not** know the planted counterparty IDs. Results are scored at **counterparty level** against the hold-out `ground_truth.csv` (never loaded into Snowflake).

### Regulatory clause → detection rule mapping

| Typology | Regulatory Basis |
|----------|-----------------|
| STRUCTURING | AML Policy §5.2 — cash deposits $8K–$9,999, 3+ in rolling 7-day window |
| ROUND_TRIPPING | Risk Appetite §5.1 — wire out/in within 10 days, amounts ±5%, name-token match |
| DORMANT_REACTIVATION | Correspondent Banking §3.1 — dormant 12+ months, >$50K in 14 days |
| VELOCITY_SPIKE | AML Policy §8.1 / TXN Monitoring §5.4 — monthly count >5× trailing 6-month avg |
| MULE_NETWORK | AML Policy §9.1 — 3+ CPs, same originator→beneficiary, 72h, <10% retention |
| SANCTIONS_NEAR_MATCH | Sanctions Proc §3.2 — score ≥60, status not FALSE_POSITIVE/NO_MATCH |

## Per-Typology Results

| Typology | TP | FP | FN | Precision | Recall | F1 | Detected | GT Positives |
|----------|---:|---:|---:|----------:|-------:|---:|---------:|-------------:|
| STRUCTURING | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 | 4 | 4 |
| ROUND_TRIPPING | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 | 3 | 3 |
| DORMANT_REACTIVATION | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 | 2 | 2 |
| VELOCITY_SPIKE | 2 | 30 | 1 | 0.062 | 0.667 | 0.114 | 32 | 3 |
| MULE_NETWORK | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 | 5 | 5 |
| SANCTIONS_NEAR_MATCH | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1 | 1 |
| **OVERALL** | **17** | **30** | **1** | **0.362** | **0.944** | **0.523** | | |

## Confusion Detail

### STRUCTURING

- **True positives** (4): CP-STRUCT-00, CP-STRUCT-01, CP-STRUCT-02, CP-STRUCT-03
- **False positives**: 0 counterparties flagged not in ground truth

### ROUND_TRIPPING

- **True positives** (3): CP-ROUNDTRIP-00, CP-ROUNDTRIP-01, CP-ROUNDTRIP-02
- **False positives**: 0 counterparties flagged not in ground truth

### DORMANT_REACTIVATION

- **True positives** (2): CP-DORMANT-00, CP-DORMANT-01
- **False positives**: 0 counterparties flagged not in ground truth

### VELOCITY_SPIKE

- **True positives** (2): CP-VELOCITY-01, CP-VELOCITY-02
- **False negatives** (1): CP-VELOCITY-00
- **False positives**: 30 counterparties flagged not in ground truth

### MULE_NETWORK

- **True positives** (5): CP-MULE-00, CP-MULE-01, CP-MULE-02, CP-MULE-03, CP-MULE-04
- **False positives**: 0 counterparties flagged not in ground truth

### SANCTIONS_NEAR_MATCH

- **True positives** (1): CP-SANCTIONS-00
- **False positives**: 0 counterparties flagged not in ground truth

## Sanctions Near-Match: Honest Assessment

The detector correctly distinguished CP-SANCTIONS-00 (true positive, score 82.5, PENDING_REVIEW) from CP-SANCTIONS-01 (false positive, score 78.0, adjudicated FALSE_POSITIVE). The governed query respects the analyst adjudication status — it does not re-flag screenings that have already been reviewed and dismissed. A naive score-only detector would flag both and inflate recall while destroying precision.

## Velocity Spike: Honest Assessment

The velocity detector flagged 32 counterparties; only 2 are in ground truth, yielding 30 false positives. This is expected: the regulatory 5× threshold (AML Policy §8.1) is deliberately sensitive. In synthetic data with variable transaction volumes, many counterparties with low baselines legitimately exceed 5× in a single month. Production systems mitigate this with seasonal adjustment and minimum-activity floors. The harness applies the regulation as written.

Missed counterparties: CP-VELOCITY-00. These counterparties have elevated but inconsistent baselines — their trailing 6-month average is high enough that no single month exceeds the 5× threshold. The planted signal was present but masked by prior volatility.

## What This Harness Does NOT Prove

1. **Completeness of the GOLD layer.** The detection queries rely on FACT_TRANSACTION, DIM_ACCOUNT, and WATCHLIST_SCREENING_RESULT. If these tables are stale or incomplete, detection degrades silently.
2. **Real-world false positive rates.** The synthetic data has ~800 counterparties. In a production portfolio of 100K+, false positive rates for velocity and structuring would be materially different.
3. **Temporal accuracy.** Detection queries run retrospectively over all data. A real surveillance system processes transactions in near-real-time windows; batch vs. streaming differences are not captured.
4. **Regulatory completeness.** Only 6 typologies are tested. The regulatory framework defines additional controls (PEP monitoring, EDD triggers, concentration limits) that are not evaluated here.
5. **Adversarial robustness.** Planted signals are cooperative — they behave exactly as the typology describes. Real launderers adapt.
