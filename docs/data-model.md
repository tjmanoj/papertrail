# PaperTrail - Data Model Design

> Design-only document. No objects created. Written before any DDL beyond
> foundation schemas so a judge can see the thinking that preceded the build.

---

## 1. Entities

### Assumptions about the fictional bank

- Mid-size commercial bank, primarily domestic (Australia) with limited
  cross-border correspondent banking.
- Regulated under AUSTRAC AML/CTF Act, APRA Prudential Standards, and
  voluntarily aligns reporting to FATF Recommendations.
- Two operational jurisdictions for demo: **AU** (full portfolio) and **SG**
  (limited branch, cross-border transactions only).
- Currency is USD throughout synthetic data for simplicity; real banks would
  multi-currency, but the governance story doesn't depend on FX conversion.

---

### 1.1 COUNTERPARTY

**Business meaning:** Any legal person or entity the bank has a relationship with
 -  individual retail customers, corporate clients, correspondent banks,
beneficial owners. One row per counterparty.

| Column | Type | Description |
|---|---|---|
| `counterparty_id` | VARCHAR PK | Stable internal identifier |
| `counterparty_type` | VARCHAR | `INDIVIDUAL`, `CORPORATE`, `CORRESPONDENT_BANK` |
| `full_legal_name` | VARCHAR | Name as on legal docs |
| `country_of_incorporation` | VARCHAR(2) | ISO 3166-1 alpha-2 |
| `country_of_residence` | VARCHAR(2) | For individuals |
| `date_of_birth` | DATE | Individuals only; NULL for corporates |
| `industry_code` | VARCHAR | ANZSIC division code |
| `risk_rating` | VARCHAR | `LOW`, `MEDIUM`, `HIGH`, `VERY_HIGH` |
| `risk_rating_date` | TIMESTAMP_NTZ | When last assessed |
| `kyc_refresh_due_date` | DATE | Next mandatory KYC review |
| `onboarding_date` | DATE | Relationship start |
| `pep_flag` | BOOLEAN | Politically Exposed Person |
| `source_of_wealth` | VARCHAR | Declared source |
| `relationship_manager_id` | VARCHAR | FK to staff |
| `jurisdiction` | VARCHAR(2) | Booking jurisdiction (AU or SG) |

**Grain:** One row per counterparty.
**Key:** `counterparty_id`.
**Relationships:** Parent of ACCOUNT. Referenced by ALERT, CASE, WATCHLIST_MATCH.

---

### 1.2 ACCOUNT

**Business meaning:** A product-holding unit - a savings account, term deposit,
loan facility, or correspondent nostro/vostro. One row per account.

| Column | Type | Description |
|---|---|---|
| `account_id` | VARCHAR PK | |
| `counterparty_id` | VARCHAR FK | Owner |
| `account_type` | VARCHAR | `SAVINGS`, `CURRENT`, `TERM_DEPOSIT`, `LOAN`, `NOSTRO`, `VOSTRO` |
| `currency_code` | VARCHAR(3) | ISO 4217 |
| `opened_date` | DATE | |
| `closed_date` | DATE | NULL if open |
| `status` | VARCHAR | `ACTIVE`, `DORMANT`, `CLOSED`, `FROZEN` |
| `branch_code` | VARCHAR | |
| `jurisdiction` | VARCHAR(2) | AU or SG |
| `average_monthly_balance_usd` | NUMBER(18,2) | Rolling 3-month average; updated monthly |

**Grain:** One row per account.
**Key:** `account_id`.
**Relationships:** Child of COUNTERPARTY. Parent of TRANSACTION.

---

### 1.3 TRANSACTION

**Business meaning:** A single monetary movement - a credit or debit on an
account. Wire transfers appear as two rows (debit on sender, credit on
receiver) linked by `transfer_reference`.

| Column | Type | Description |
|---|---|---|
| `transaction_id` | VARCHAR PK | |
| `account_id` | VARCHAR FK | |
| `transaction_date` | DATE | Value date (settlement) |
| `transaction_timestamp` | TIMESTAMP_NTZ | Exact booking time |
| `transaction_type` | VARCHAR | `WIRE_IN`, `WIRE_OUT`, `CASH_DEPOSIT`, `CASH_WITHDRAWAL`, `INTERNAL_TRANSFER`, `POS`, `ATM`, `FEE` |
| `amount_usd` | NUMBER(18,2) | Always positive; direction from type |
| `originator_name` | VARCHAR | For wire-ins: who sent it |
| `originator_country` | VARCHAR(2) | |
| `beneficiary_name` | VARCHAR | For wire-outs: who receives |
| `beneficiary_country` | VARCHAR(2) | |
| `transfer_reference` | VARCHAR | Links debit/credit legs |
| `channel` | VARCHAR | `BRANCH`, `ONLINE`, `MOBILE`, `SWIFT` |
| `is_reversal` | BOOLEAN | TRUE if this reverses a prior txn |
| `reversed_transaction_id` | VARCHAR | FK to the original, if reversal |
| `status` | VARCHAR | `SETTLED`, `PENDING`, `REVERSED`, `FAILED` |
| `reporting_entity_jurisdiction` | VARCHAR(2) | Which branch booked it |

**Grain:** One row per transaction.
**Key:** `transaction_id`.
**Relationships:** Child of ACCOUNT. Referenced by ALERT (via alert triggers).

**Design note on reversals:** Reversals are separate rows with `is_reversal =
TRUE`, not updates. This is deliberate - netting out reversals vs. counting
gross is one of the most common sources of divergence (see Governed Metrics).

---

### 1.4 ALERT

**Business meaning:** An automated detection signal from a monitoring rule - a
threshold breach, pattern match, or model score. One alert can involve multiple
transactions.

| Column | Type | Description |
|---|---|---|
| `alert_id` | VARCHAR PK | |
| `counterparty_id` | VARCHAR FK | Primary subject |
| `rule_id` | VARCHAR | Which detection rule fired |
| `rule_name` | VARCHAR | Human-readable rule name |
| `alert_date` | DATE | When the rule fired |
| `alert_timestamp` | TIMESTAMP_NTZ | |
| `typology` | VARCHAR | `STRUCTURING`, `RAPID_MOVEMENT`, `DORMANT_REACTIVATION`, `SANCTIONS_NEAR_MATCH`, `VELOCITY_SPIKE`, `ROUND_TRIPPING` |
| `severity` | VARCHAR | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `status` | VARCHAR | `OPEN`, `ESCALATED`, `CLOSED_NO_ACTION`, `CLOSED_SAR_FILED` |
| `assigned_analyst_id` | VARCHAR | |
| `jurisdiction` | VARCHAR(2) | |
| `narrative` | VARCHAR | Auto-generated description |

**Grain:** One row per alert.
**Key:** `alert_id`.
**Relationships:** Child of COUNTERPARTY. Parent of ALERT_TRANSACTION (bridge).
Optionally escalated to CASE.

---

### 1.5 ALERT_TRANSACTION (bridge)

**Business meaning:** Which specific transactions triggered or are evidentially
linked to an alert.

| Column | Type | Description |
|---|---|---|
| `alert_id` | VARCHAR FK | |
| `transaction_id` | VARCHAR FK | |

**Grain:** One row per (alert, transaction) pair.
**Key:** Composite (`alert_id`, `transaction_id`).

---

### 1.6 CASE

**Business meaning:** An investigation opened by a compliance analyst, often
grouping one or more alerts for a single counterparty. Tracks the decision
lifecycle from open to SAR filing or closure.

| Column | Type | Description |
|---|---|---|
| `case_id` | VARCHAR PK | |
| `counterparty_id` | VARCHAR FK | |
| `opened_date` | DATE | |
| `closed_date` | DATE | NULL if open |
| `status` | VARCHAR | `OPEN`, `UNDER_REVIEW`, `ESCALATED_TO_MLRO`, `SAR_FILED`, `CLOSED_NO_ACTION` |
| `priority` | VARCHAR | `ROUTINE`, `URGENT`, `CRITICAL` |
| `assigned_analyst_id` | VARCHAR | |
| `jurisdiction` | VARCHAR(2) | |
| `resolution_narrative` | VARCHAR | Free-text outcome |

**Grain:** One row per investigation case.
**Key:** `case_id`.
**Relationships:** Child of COUNTERPARTY. Links to ALERT via CASE_ALERT bridge.

---

### 1.7 CASE_ALERT (bridge)

| Column | Type | Description |
|---|---|---|
| `case_id` | VARCHAR FK | |
| `alert_id` | VARCHAR FK | |

---

### 1.8 WATCHLIST_ENTRY

**Business meaning:** A sanctions/PEP/adverse-media record from an external
watchlist provider. One row per listed entity.

| Column | Type | Description |
|---|---|---|
| `watchlist_entry_id` | VARCHAR PK | |
| `list_source` | VARCHAR | `OFAC_SDN`, `UN_SANCTIONS`, `EU_SANCTIONS`, `AUSTRAC_PRESCRIBED`, `PEP_LIST` |
| `listed_name` | VARCHAR | Name as listed |
| `listed_name_normalised` | VARCHAR | Uppercased, diacritics stripped |
| `country` | VARCHAR(2) | |
| `listed_date` | DATE | |
| `delisted_date` | DATE | NULL if still active |
| `entity_type` | VARCHAR | `INDIVIDUAL`, `ENTITY`, `VESSEL`, `AIRCRAFT` |
| `identifying_information` | VARCHAR | DOB, passport, etc. |

**Grain:** One row per watchlist entry.
**Key:** `watchlist_entry_id`.
**Relationships:** Matched against COUNTERPARTY in screening.

---

### 1.9 WATCHLIST_SCREENING_RESULT

**Business meaning:** The output of matching a counterparty against the watchlist.
Records every match attempt, including true negatives (no match) and false
positives (match dismissed).

| Column | Type | Description |
|---|---|---|
| `screening_id` | VARCHAR PK | |
| `counterparty_id` | VARCHAR FK | |
| `watchlist_entry_id` | VARCHAR FK | NULL if no match |
| `screening_date` | TIMESTAMP_NTZ | |
| `match_score` | NUMBER(5,2) | 0-100 fuzzy similarity |
| `match_status` | VARCHAR | `CONFIRMED_MATCH`, `FALSE_POSITIVE`, `PENDING_REVIEW`, `NO_MATCH` |
| `reviewed_by` | VARCHAR | Analyst who adjudicated |

---

### 1.10 REGULATORY_DOCUMENT

**Business meaning:** A bank policy, regulatory guidance, or procedural document
stored as unstructured text for Cortex Search to index.

| Column | Type | Description |
|---|---|---|
| `document_id` | VARCHAR PK | |
| `document_type` | VARCHAR | `AML_POLICY`, `SANCTIONS_PROCEDURE`, `STR_GUIDANCE`, `KYC_POLICY`, `LIQUIDITY_GUIDANCE`, `RISK_APPETITE_STATEMENT` |
| `title` | VARCHAR | |
| `version` | VARCHAR | e.g. `v2.3` |
| `effective_date` | DATE | |
| `jurisdiction` | VARCHAR(2) | Which jurisdiction it applies to |
| `full_text` | VARCHAR | Complete document content |
| `synthetic_watermark` | VARCHAR | Always `SYNTHETIC_DATA_PAPERTRAIL_2026` |

**Grain:** One row per document version.
**Key:** `document_id`.

---

### 1.11 REGULATORY_DOCUMENT_CLAUSE

**Business meaning:** An individually addressable section within a regulatory
document - the unit of citation in a finding.

| Column | Type | Description |
|---|---|---|
| `clause_id` | VARCHAR PK | |
| `document_id` | VARCHAR FK | |
| `clause_number` | VARCHAR | e.g. `4.2.1` |
| `clause_title` | VARCHAR | |
| `clause_text` | VARCHAR | |

**Grain:** One row per clause.
**Key:** `clause_id`.
**Relationships:** Child of REGULATORY_DOCUMENT. Referenced by provenance footnotes.

---

### Entity-Relationship Summary

```
COUNTERPARTY ──1:N── ACCOUNT ──1:N── TRANSACTION
      │                                    │
      │                                    │ (via ALERT_TRANSACTION)
      ├──1:N── ALERT ────────N:M──────────┘
      │           │
      │           │ (via CASE_ALERT)
      ├──1:N── CASE
      │
      ├──1:N── WATCHLIST_SCREENING_RESULT ──N:1── WATCHLIST_ENTRY
      │
REGULATORY_DOCUMENT ──1:N── REGULATORY_DOCUMENT_CLAUSE
```

---

## 2. Governed Metrics

Each metric below includes the **business definition**, the **intended SQL
semantics**, and - critically - the **specific ways ungoverned computation
diverges**. This section is the core argument for why a semantic view matters.

---

### 2.1 `total_suspicious_transaction_volume_usd`

**Business definition:** The total USD value of transactions linked to alerts
that are currently open or escalated, within a specified date range.

**Intended SQL semantics:**
```sql
SUM(t.amount_usd)
WHERE a.status IN ('OPEN', 'ESCALATED')
  AND t.is_reversal = FALSE
  AND t.status = 'SETTLED'
  -- date filter on t.transaction_date (value/settlement date)
```

**Why it diverges ungoverned:**

| Divergence | What happens | Impact |
|---|---|---|
| **Reversals included** | Analyst A counts gross volume including reversed transactions. Analyst B nets them out. A reports 40% higher. | Overstated risk to board; audit finding for inflated SAR narrative. |
| **Pending vs settled** | Analyst A includes `PENDING` transactions because they were flagged. Analyst B restricts to `SETTLED` because pending txns may never clear. | Different filing thresholds hit; inconsistent STR/SAR triggers. |
| **Date basis** | Analyst A filters on `transaction_timestamp` (booking). Analyst B filters on `transaction_date` (value/settlement). A transaction booked 31 Dec but settled 2 Jan appears in different reporting periods. | Quarter-end risk figures diverge between teams. Regulatory report inconsistency. |
| **Alert status scope** | Analyst A includes `CLOSED_SAR_FILED` (historically suspicious). Analyst B only counts currently open. | Trend analysis shows different trajectories for the same data. |

---

### 2.2 `counterparty_exposure_usd`

**Business definition:** The net balance exposure to a single counterparty across
all their active accounts.

**Intended SQL semantics:**
```sql
SUM(ac.average_monthly_balance_usd)
WHERE ac.status = 'ACTIVE'
  AND ac.counterparty_id = :target
```

**Why it diverges ungoverned:**

| Divergence | What happens | Impact |
|---|---|---|
| **Dormant accounts included** | One analyst includes dormant accounts (status = `DORMANT`) because the money is still there. Another excludes them per policy. | Concentration risk reports differ by millions. |
| **Entity resolution** | Counterparty has a personal account and is a beneficial owner of a corporate. Analyst A sums only direct accounts. Analyst B manually resolves and includes the corporate. | Same counterparty, different exposure - potentially breaching large-exposure limits without knowing. |
| **Loan vs deposit netting** | Analyst A nets loans against deposits (net exposure). Analyst B reports gross across all product types. | Regulatory capital calculation is wrong if method isn't consistent. |
| **Currency conversion date** | If multi-currency existed, the FX rate date (trade date, report date, month-end fix) changes the number. We use USD throughout, but the metric definition must still specify "no FX conversion applied" to prevent a future analyst from adding one ad hoc. |

---

### 2.3 `alert_closure_rate`

**Business definition:** Percentage of alerts closed (any disposition) within a
given period out of all alerts opened in that same period.

**Intended SQL semantics:**
```sql
COUNT(CASE WHEN status LIKE 'CLOSED%' THEN 1 END)
  / NULLIF(COUNT(*), 0) * 100
WHERE alert_date BETWEEN :start AND :end
```

**Why it diverges ungoverned:**

| Divergence | What happens | Impact |
|---|---|---|
| **Cohort vs snapshot** | Analyst A measures alerts *opened* in the period and checks if they're closed (cohort). Analyst B counts any alert closed in the period regardless of when it opened (snapshot). Cohort rates are lower because recent alerts haven't aged. | Management believes team is slow (cohort) or fast (snapshot) depending on who reports. |
| **Denominator includes auto-closed** | Some rules auto-close below-threshold alerts. Including these inflates the closure rate. Excluding them shows a more realistic analyst workload picture. | Board KPI becomes meaningless if auto-closed alerts dominate. |
| **Timezone** | Alert timestamps are NTZ. An analyst in SG and one in AU interpret "today's alerts" differently, shifting alerts across period boundaries. | Daily ops dashboards disagree; incident response is delayed. |

---

### 2.4 `sar_filing_rate`

**Business definition:** Percentage of investigations (cases) that result in a
SAR/STR filing, over a period.

**Intended SQL semantics:**
```sql
COUNT(CASE WHEN status = 'SAR_FILED' THEN 1 END)
  / NULLIF(COUNT(*), 0) * 100
WHERE opened_date BETWEEN :start AND :end
```

**Why it diverges ungoverned:**

| Divergence | What happens | Impact |
|---|---|---|
| **Denominator** | Analyst A counts all cases opened. Analyst B excludes cases still in `OPEN` status (not yet decided). B always reports a higher rate. | Regulator asks "what's your SAR rate?" and gets a different answer from each team. |
| **Multiple SARs per case** | A single case can result in an initial SAR and a supplemental. Counting supplementals inflates the numerator. | Misleading trend: filing rate appears to rise when it's actually refiling on old cases. |
| **Jurisdiction filter** | AU analyst reports AU cases; SG analyst reports SG cases. Neither reports cross-border cases that involve both jurisdictions. | Regulatory gap: nobody owns the cross-border case in the KPI. |

---

### 2.5 `structuring_indicator_score`

**Business definition:** A rule-based composite score (0-100) measuring how
closely a counterparty's recent cash transaction pattern matches known
structuring typologies (multiple deposits just below reporting threshold).

**Intended SQL semantics:**
```sql
-- Counts cash deposits in trailing 30 days that are between
-- $8,000 and $9,999 (just below $10K reporting threshold)
-- and divides by total cash deposits to get a ratio, then scales 0-100.
ROUND(
  COUNT(CASE WHEN transaction_type = 'CASH_DEPOSIT'
              AND amount_usd BETWEEN 8000 AND 9999 THEN 1 END)
  / NULLIF(COUNT(CASE WHEN transaction_type = 'CASH_DEPOSIT' THEN 1 END), 0)
  * 100, 2
)
-- over trailing 30 calendar days from current_date
```

**Why it diverges ungoverned:**

| Divergence | What happens | Impact |
|---|---|---|
| **Threshold band** | One analyst uses 8,000-9,999. Another uses 9,000-9,999 (tighter band). A third uses 5,000-9,999 (broad). All defensible; all give different scores. | No consistent alert calibration; model validation is impossible. |
| **Lookback window** | 30 days vs 7 days vs calendar month. Structuring patterns across month-end boundaries are missed or double-counted. | Seasonal smurfing activity falls through the cracks. |
| **Cash-equivalent inclusion** | Does a money order purchased at a branch count as a cash deposit? Different analysts decide differently. Our model restricts to `CASH_DEPOSIT` explicitly. | Typology detection coverage varies by analyst interpretation. |

---

### 2.6 `days_to_case_resolution`

**Business definition:** Calendar days between a case being opened and receiving
a terminal status (`SAR_FILED` or `CLOSED_NO_ACTION`).

**Intended SQL semantics:**
```sql
DATEDIFF('day', opened_date, closed_date)
WHERE closed_date IS NOT NULL
```

**Why it diverges ungoverned:**

| Divergence | What happens | Impact |
|---|---|---|
| **Business days vs calendar days** | Analyst A uses calendar days. Analyst B uses business days (excludes weekends/holidays). A case closed in 10 calendar days = 8 business days. | SLA compliance looks different; regulator expects one, management reports the other. |
| **Re-opened cases** | A case closed and re-opened resets for one analyst, accumulates for another. | Mean resolution time either hides or exaggerates rework. |
| **ESCALATED_TO_MLRO as terminal?** | Some analysts treat MLRO escalation as "resolved from analyst perspective." Metric should only count truly terminal states. | Premature closure inflates performance KPIs. |

---

### 2.7 `high_risk_counterparty_count`

**Business definition:** Count of counterparties currently rated HIGH or VERY_HIGH.

**Intended SQL semantics:**
```sql
COUNT(DISTINCT counterparty_id)
WHERE risk_rating IN ('HIGH', 'VERY_HIGH')
```

**Why it diverges ungoverned:**

| Divergence | What happens | Impact |
|---|---|---|
| **Stale ratings** | Analyst A counts current rating. Analyst B filters to ratings assessed within the last 12 months. Stale ratings from 3 years ago that were never refreshed inflate A's count. | Board report shows inflated risk population; or deflated if stale ratings were originally LOW and counterparty behaviour changed. |
| **Relationship status** | Should exited/closed counterparties still count? One analyst includes all, another restricts to counterparties with at least one active account. | Denominator for "% high risk" is different; trend analysis is unreliable. |

---

## 3. Unstructured / Regulatory Document Side

### Documents the bank holds

| Document | What it contains | Key clauses |
|---|---|---|
| **AML/CTF Policy** | The bank's overarching anti-money-laundering framework: risk appetite, customer due diligence tiers, enhanced due diligence triggers, transaction monitoring philosophy, SAR filing obligations. | CDD requirements by risk tier; EDD triggers (PEPs, high-risk jurisdictions); threshold reporting obligations (cash > $10K); tipping-off prohibition. |
| **Sanctions Screening Procedure** | Operational procedure for real-time and batch screening of counterparties and transactions against sanctions lists. | Screening frequency; match threshold; escalation path for potential matches; de-escalation for confirmed false positives; record-keeping requirements. |
| **STR/SAR Filing Guidance** | Internal guidance on when and how to file Suspicious Transaction Reports. | Triggers for filing; narrative requirements; timeframes (72-hour AUSTRAC obligation); quality review steps; supplemental filing rules. |
| **KYC Refresh Policy** | Defines refresh cycles for customer due diligence based on risk rating. | HIGH = annual refresh; MEDIUM = biennial; LOW = triennial; trigger-based refresh on adverse media or transaction anomaly; documentation requirements. |
| **Risk Appetite Statement** | Board-approved document defining acceptable risk levels for AML, sanctions, fraud. | Maximum acceptable alert ageing; target SAR filing rate range; concentration limits; correspondent banking risk limits. |
| **Correspondent Banking Due Diligence** | Specific due diligence for nostro/vostro relationships. | Downstream correspondent restrictions; payable-through account controls; nested correspondent identification. |

### Clause-to-metric mapping

This is what makes PaperTrail's provenance chain complete - a metric in a
finding doesn't just cite its SQL, it cites *why* that metric matters
regulatorily.

| Metric | Cites clause from | Regulatory reason |
|---|---|---|
| `total_suspicious_transaction_volume_usd` | STR Filing Guidance §3.1 - Filing thresholds | Volume determines whether threshold reporting is triggered |
| `counterparty_exposure_usd` | Risk Appetite Statement §2.4 - Concentration limits | Exposure above limit requires board notification |
| `alert_closure_rate` | AML/CTF Policy §7.3 - Monitoring effectiveness | Rate below target triggers enhanced monitoring review |
| `sar_filing_rate` | STR Filing Guidance §4.1 - Filing rate expectations | Abnormally low rate is a regulatory red flag (defensive filing) |
| `structuring_indicator_score` | AML/CTF Policy §5.2 - Structuring detection | Threshold avoidance is a prescribed typology under AUSTRAC |
| `days_to_case_resolution` | AML/CTF Policy §7.5 - Investigation timeliness | Cases open > 90 days require MLRO escalation |
| `high_risk_counterparty_count` | KYC Refresh Policy §2.1 - Risk-based refresh | Count drives resource planning for annual KYC reviews |

---

## 4. Planted Signal

Synthetic data will contain deliberately embedded risk signal so that
detection is genuine, not an artifact of random noise. Each typology below
describes exactly how it manifests at the row level.

### 4.1 Structuring / Smurfing

**Typology:** Counterparty splits cash deposits to stay below the $10,000
reporting threshold.

**Row-level manifestation:**
- 3-5 counterparties will have clusters of `CASH_DEPOSIT` transactions with
  amounts in the $8,000-$9,950 range.
- Deposits occur across 2-3 different accounts owned by the same counterparty.
- Frequency: 3-6 deposits within any rolling 7-day window.
- At least one "slip-up" deposit of exactly $9,999 to make the pattern obvious.
- Normal counterparties have occasional cash deposits but with amounts that are
  uniformly distributed and not clustered near the threshold.

### 4.2 Round-Tripping

**Typology:** Funds leave an account via wire transfer and return (possibly
through an intermediary) within a short period, often to create the appearance
of legitimate business activity.

**Row-level manifestation:**
- A counterparty sends a `WIRE_OUT` to a beneficiary in a different country.
- Within 5-10 days, a `WIRE_IN` of a similar amount (within 2%) arrives from
  the same or related originator country.
- The `originator_name` on the return wire is a different legal entity but
  shares a word with the counterparty name (e.g., "Apex Holdings" sends,
  "Apex Trading Ltd" returns).
- 2-3 counterparties will exhibit this pattern with 3+ round-trip cycles.

### 4.3 Dormant Account Reactivation

**Typology:** An account that has been inactive for 12+ months suddenly receives
significant transaction volume, suggesting it is being used as a pass-through.

**Row-level manifestation:**
- 2 accounts will have `status = 'DORMANT'` with no transactions for 14+ months.
- A sudden burst of 10+ transactions within a 2-week window, totalling over
  $50,000.
- Account status flips from `DORMANT` to `ACTIVE` immediately before the burst.
- Transactions are a mix of `WIRE_IN` and `WIRE_OUT` - money passes through
  rather than accumulating.

### 4.4 Sanctions Near-Match

**Typology:** A counterparty's name is suspiciously similar to a sanctioned
entity but not identical - potential evasion through spelling variation.

**Row-level manifestation:**
- 2 watchlist entries will have names that differ from existing counterparties
  by minor variations: transposed letters, missing diacritics, abbreviated
  first name.
- `match_score` in WATCHLIST_SCREENING_RESULT for these will be 75-89 (below
  the typical auto-confirm threshold of 90 but above the auto-dismiss
  threshold of 60).
- One will be a genuine false positive (different person). One will be a true
  positive that should have been caught (same person, name variant).

### 4.5 Velocity Spike

**Typology:** Transaction volume or count for a counterparty suddenly exceeds
their historical norm by a large multiple, suggesting their account may be
compromised or used for layering.

**Row-level manifestation:**
- 3 counterparties will have a stable baseline of 5-10 transactions per month
  for 6+ months.
- In one specific month, they will have 40-80 transactions - a 5x-10x spike.
- The spike transactions will be predominantly `WIRE_IN` followed by `WIRE_OUT`
  within 24-48 hours (layering pattern).
- Amounts will be varied (not round numbers) to avoid simple threshold rules.

### 4.6 Mule Network

**Typology:** A set of seemingly unrelated counterparties who all receive funds
from the same originator and rapidly forward them to a common beneficiary  -
a classic money mule structure.

**Row-level manifestation:**
- 4-5 counterparties who have no overt relationship (different names, addresses,
  onboarding dates).
- All receive `WIRE_IN` from the same `originator_name` within a 3-day window.
- All send `WIRE_OUT` to the same `beneficiary_name` within 48 hours of receipt.
- The amounts fan out from originator (one large sum) and consolidate to
  beneficiary (many smaller sums minus a ~5% "commission" retained by each mule).
- These counterparties are all `INDIVIDUAL` type, onboarded within the last 6
  months, and rated `LOW` risk - the mules were not flagged at onboarding.

### Signal density

Assumption: ~200 counterparties, ~500 accounts, ~50,000 transactions over 18
months. Of these:

- ~15 counterparties will exhibit at least one planted typology.
- ~8% of transactions will be part of a planted pattern.
- The rest is legitimate noise: payroll, rent, supplier payments, ATM
  withdrawals. Normal distribution of amounts with realistic daily/weekly
  patterns.

This density means the signal is findable but not trivially obvious - a
compliance analyst needs the system to surface it, which is the point.
