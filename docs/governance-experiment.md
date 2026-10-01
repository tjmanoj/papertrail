# Governance Experiment - Governed vs Ungoverned SQL Generation

## Hypothesis

We originally hypothesised two things:

1. **Variance hypothesis:** An ungoverned LLM (raw AI_COMPLETE against the base tables)
   would produce *inconsistent* SQL across repeated runs of the same question - different
   joins, different filters, different answers each time.
2. **Correctness hypothesis:** Even when consistent, the ungoverned path would silently
   miss governance decisions encoded in the semantic view, producing *wrong but
   confident* answers.

**The variance hypothesis was not supported.** The correctness hypothesis was.

## Method

### Setup

- **Database:** `PAPERTRAIL` on Snowflake, with schemas `RAW`, `CURATED`, `GOLD`,
  `GOVERNANCE`.
- **Governed path:** Cortex Analyst querying the semantic view
  `PAPERTRAIL.GOLD.PAPERTRAIL_SEMANTIC`, which encodes metric definitions, verified
  queries, date-basis rules, reversal/settlement filters, and entity-resolution logic.
- **Ungoverned path:** `SNOWFLAKE.CORTEX.AI_COMPLETE('llama3.1-70b', ...)` with a prompt
  that provides the DDL of the RAW schema tables and asks for a SQL answer. No semantic
  view, no metric definitions, no governance guardrails.
- **Warehouse:** `PAPERTRAIL_WH` (XS, AUTO_SUSPEND = 60).

### Fairness rules

- Both paths received the same 5 questions, in the same wording.
- Both paths had access to the same underlying data (the GOLD tables are materialised
  from RAW; no rows are added or removed).
- The ungoverned path received full DDL for all RAW tables - it was not handicapped.
- The governed path received no hints beyond the semantic view definition.
- Neither path was cherry-picked: all runs are recorded in
  `PAPERTRAIL.GOVERNANCE.GOVERNANCE_EXPERIMENT`.

### Questions

| ID | Question |
|----|----------|
| Q1 | What was the total suspicious transaction volume for Q3 2026? |
| Q2 | What is our total exposure to counterparty CP-STRUCT-01? |
| Q3 | What was the alert closure rate for 2026? |
| Q4 | What share of investigation cases resulted in a SAR filing? |
| Q5 | How many high risk counterparties do we have in Singapore? |

### Runs

- **Ungoverned:** 5 runs per question (25 rows total, path = `UNGOVERNED`).
- **Governed:** 3 runs per question (15 rows total, path = `GOVERNED`).
  We reduced to 3 after the ungoverned path showed zero variance - the stability
  question was already answered.

## Results - Stability

**Both paths were perfectly stable.** Every run of every question produced
byte-identical SQL and identical numeric results within its path.

| Path | Questions | Runs/Question | Unique SQL per Question | Variance |
|------|-----------|---------------|------------------------|----------|
| UNGOVERNED | 5 | 5 | 1 | 0 |
| GOVERNED | 5 | 3 | 1 | 0 |

The variance hypothesis - that an ungoverned LLM would produce inconsistent SQL - was
**not supported**. The model was deterministic across all runs.

## Results - Correctness

| Q | Question | Ungoverned | Governed | Abs Diff | Rel Diff | Verdict |
|---|----------|-----------|----------|----------|----------|---------|
| Q1 | Suspicious txn volume Q3 2026 | $8,797,923.12 | $4,295,229.27 | $4,502,693.85 | +104.8% | **DIVERGE** |
| Q2 | Exposure to CP-STRUCT-01 | $87,185.10 | $87,185.10 | $0.00 | 0% | AGREE |
| Q3 | Alert closure rate 2026 | 0.636364 (63.6%) | 63.64% | 0 | 0% | AGREE |
| Q4 | SAR filing share | 0.064516 (6.5%) | 6.45% | 0 | 0% | AGREE |
| Q5 | High-risk counterparties in SG | 23 | 36 | 13 | +56.5% | **DIVERGE** |

Q3 and Q4 agree on the underlying value; the ungoverned path returns a 0-to-1 ratio
while the governed path returns a percentage. The numeric difference is presentation,
not substance.

Q2 agrees because CP-STRUCT-01 happens to have no beneficial-ownership links in the
data, so direct exposure equals entity-resolved exposure for this specific counterparty.
The *methodology* differs (see SQL diff below), but the result coincides.

**2 of 5 questions diverge materially.** Q1 overstates by 105%. Q5 understates by 36%.

## Per-Question SQL Diffs and Root Causes

### Q1 - Suspicious Transaction Volume Q3 2026

**Verdict: DIVERGE - $8,797,923 (ungoverned) vs $4,295,229 (governed), +105%**

Three governance decisions cause the divergence:

**1. Date basis: `transaction_date` vs `value_date`**

The ungoverned query uses `t.TRANSACTION_DATE BETWEEN '2026-07-01' AND '2026-09-30'`.
The governed query uses `ft.value_date >= '2026-07-01' AND ft.value_date < '2026-10-01'`.

The semantic view specifies: *"VALUE_DATE is the GOVERNED DATE BASIS for transaction
reporting - all date-filtered metrics on transactions use VALUE_DATE, not booking_date
or transaction_timestamp. This prevents cross-period discrepancies from
booking-vs-settlement timing differences."*

**2. Missing reversal exclusion**

The ungoverned query has no filter for reversals. The governed query requires
`ft.is_reversal = FALSE`. The semantic view specifies: *"Reversals excluded
(IS_REVERSAL = FALSE) to avoid double-counting the economic event."*

**3. Missing settlement filter**

The ungoverned query includes all transactions. The governed query requires
`ft.is_settled = TRUE`. The semantic view specifies: *"Only SETTLED transactions  -
PENDING may never clear and should not inflate the risk signal."*

**4. Alert-linkage scope**

The ungoverned query joins to all alerts regardless of status:
```sql
-- UNGOVERNED
SELECT DISTINCT al.COUNTERPARTY_ID
FROM RAW.ALERT al
WHERE al.ALERT_DATE BETWEEN '2026-07-01' AND '2026-09-30'
```

The governed query uses the pre-computed `IS_ALERT_LINKED_ACTIVE` flag, which is TRUE
only when linked to an alert in `OPEN` or `ESCALATED` status. The semantic view
specifies: *"Only transactions linked to currently active alerts count as suspicious.
Historically closed alerts (including CLOSED_SAR_FILED) are excluded because the volume
metric measures current exposure, not historical."*

Additionally, the ungoverned path uses an indirect join chain
(TRANSACTION → ACCOUNT → counterparty_id ∈ ALERT.counterparty_id) rather than the
governed direct transaction-to-alert linkage, which could include transactions from
unrelated accounts of the same counterparty.

```sql
-- UNGOVERNED (complete)
SELECT SUM(t.AMOUNT_USD)
FROM RAW.TRANSACTION t
JOIN RAW.ACCOUNT a ON t.ACCOUNT_ID = a.ACCOUNT_ID
WHERE t.TRANSACTION_DATE BETWEEN '2026-07-01' AND '2026-09-30'
  AND a.COUNTERPARTY_ID IN (
    SELECT DISTINCT al.COUNTERPARTY_ID
    FROM RAW.ALERT al
    WHERE al.ALERT_DATE BETWEEN '2026-07-01' AND '2026-09-30'
  );

-- GOVERNED (complete)
SELECT SUM(
  CASE WHEN ft.is_alert_linked_active = TRUE
       AND ft.is_reversal = FALSE
       AND ft.is_settled = TRUE
  THEN ft.amount_usd ELSE 0 END
) AS total_suspicious_transaction_volume_usd
FROM PAPERTRAIL.GOLD.FACT_TRANSACTION ft
WHERE ft.value_date >= '2026-07-01' AND ft.value_date < '2026-10-01';
```

### Q2 - Exposure to CP-STRUCT-01

**Verdict: AGREE - $87,185.10 both paths**

The methodology differs: the ungoverned path sums `AVERAGE_MONTHLY_BALANCE_USD` from
`RAW.ACCOUNT` (direct exposure), while the governed path reads `RESOLVED_EXPOSURE_USD`
from `GOLD.DIM_COUNTERPARTY` (entity-resolved exposure including beneficial ownership
via `CURATED.ENTITY_LINK`). The values coincide because CP-STRUCT-01 has no beneficial
ownership links in the synthetic data.

For a counterparty *with* beneficial ownership links, these would diverge - the
ungoverned path would understate exposure, potentially missing concentration-limit
breaches.

```sql
-- UNGOVERNED
SELECT SUM(a.AVERAGE_MONTHLY_BALANCE_USD)
FROM RAW.COUNTERPARTY cp
JOIN RAW.ACCOUNT a ON a.COUNTERPARTY_ID = cp.COUNTERPARTY_ID
WHERE cp.COUNTERPARTY_ID = 'CP-STRUCT-01';

-- GOVERNED
SELECT dc.resolved_exposure_usd
FROM PAPERTRAIL.GOLD.DIM_COUNTERPARTY dc
WHERE dc.counterparty_id = 'CP-STRUCT-01';
```

### Q3 - Alert Closure Rate 2026

**Verdict: AGREE - 63.64% both paths**

Both count alerts with CLOSED-prefix statuses and divide by total alerts in 2026. The
ungoverned path explicitly names `CLOSED_NO_ACTION` and `CLOSED_SAR_FILED`; the governed
path uses `LIKE 'CLOSED%'`. These return the same rows given the current status enum.
The ungoverned returns a 0-to-1 ratio; the governed returns a percentage.

### Q4 - SAR Filing Share

**Verdict: AGREE - 6.45% both paths**

Both filter `STATUS = 'SAR_FILED'` and divide by total cases. The ungoverned queries
`RAW.CASE_INVESTIGATION`; the governed queries `GOLD.FACT_CASE`. Same underlying data,
same logic. Ungoverned returns a ratio, governed returns a percentage.

### Q5 - High-Risk Counterparties in Singapore

**Verdict: DIVERGE - 23 (ungoverned) vs 36 (governed), -36%**

The root cause is one governance decision:

**`RISK_RATING = 'HIGH'` vs `IS_HIGH_RISK = TRUE`**

The ungoverned query filters `RISK_RATING = 'HIGH'` on `RAW.COUNTERPARTY`. The governed
query filters `IS_HIGH_RISK = TRUE` on `GOLD.DIM_COUNTERPARTY`.

The semantic view defines IS_HIGH_RISK as: *"TRUE when risk_rating is HIGH or VERY_HIGH.
This is the governed flag used by the high_risk_counterparty_count metric - it includes
both HIGH and VERY_HIGH per KYC Refresh Policy section 2.1."*

The ungoverned path misses all `VERY_HIGH`-rated counterparties. There are 13
counterparties in Singapore rated `VERY_HIGH` that the ungoverned count excludes.

```sql
-- UNGOVERNED
SELECT COUNT(*)
FROM RAW.COUNTERPARTY
WHERE RISK_RATING = 'HIGH' AND JURISDICTION = 'SG';

-- GOVERNED
SELECT COUNT(DISTINCT dc.counterparty_id)
FROM PAPERTRAIL.GOLD.DIM_COUNTERPARTY dc
WHERE dc.is_high_risk = TRUE AND dc.jurisdiction = 'SG';
```

## Conclusion

Our original hypothesis about variance was wrong: the ungoverned LLM produced
byte-identical SQL across every run. It is perfectly consistent.

The actual finding is worse than inconsistency: **the ungoverned path is perfectly
consistent and perfectly confident, and on 2 of 5 questions it is materially wrong,
with no signal to the reader that anything is wrong.**

- **Q1** overstates suspicious transaction volume by **$4.5M (105%)** because it
  includes reversals, unsettled transactions, closed-alert-linked transactions, and
  uses booking date instead of settlement date.
- **Q5** understates the high-risk counterparty count by **13 entities (36%)** because
  it applies a literal `RISK_RATING = 'HIGH'` filter instead of the governed
  `IS_HIGH_RISK` flag that includes `VERY_HIGH` per KYC policy.
- **Q2** agrees on this specific counterparty but uses a structurally different
  methodology (direct vs entity-resolved exposure) that would diverge for counterparties
  with beneficial ownership links.

The governed path is not valuable because it reduces variance - variance was never the
problem. It is valuable because it encodes compliance decisions that a general-purpose
LLM has no way to know: which date field is authoritative, which statuses constitute
"high risk", whether reversals should be excluded, and how to resolve beneficial
ownership. These are institutional decisions, not statistical properties of the data,
and they cannot be inferred from DDL alone.

A compliance officer receiving the ungoverned Q1 figure ($8.8M instead of $4.3M) would
report double the actual suspicious volume. A KYC team receiving the ungoverned Q5
figure (23 instead of 36) would miss 13 high-risk entities in their jurisdiction review.
Both answers arrive with full confidence and no disclaimer.

The semantic view does not make the answers *more consistent*. It makes them *correct*.
