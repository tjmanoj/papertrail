# PaperTrail

**An audit-ready risk and regulatory copilot, built natively on Snowflake.**

Team **Provenance** · Snowflake CoCo CLI Hackathon 2026, GCC Edition
Problem statement 1 — *Risk, Fraud and Regulatory Intelligence Copilot*

---

## Try it in two minutes

| | |
|---|---|
| **Live app** (no login required) | **https://papertrail-provenance.vercel.app** |
| **Native app** (Streamlit in Snowflake) | `PAPERTRAIL.GOLD.PAPERTRAIL_APP` |

Three things a judge can do without taking our word for anything:

1. **Ask → "What will next quarter's suspicious volume be?"**
   The agent refuses. It reports governed historical data and will not estimate.
   The guardrail is structural, not a politeness instruction.

2. **File → "Re-run this SQL now."**
   Takes the SQL stored on a finding's own footnote, executes it against Snowflake
   live, and shows whether the figure still holds. It returns **30.23** against a
   stored **30.23**, in about 300 ms.

3. **Prove → read the headline.**
   We set out to show an ungoverned model answers inconsistently. It doesn't.
   The measured result is worse than that, and it is on the page.

---

## The problem

In a bank's GCC, finding the risk signal is the cheap part. **Defending the number
is the expensive part.** An analyst answers "which transactions breached our AML
thresholds last month" in ten minutes, then spends two days assembling an evidence
pack an auditor will accept.

Dashboards hand you numbers nobody can defend. PaperTrail's output is not a chat
reply — it is a **filing**, in which every figure is a footnote that resolves to:

```
30.23%
  → metric        structuring_indicator_score
  → definition    "% of cash deposits in the $8,000–$9,999 band. Denominator is
                   CASH_DEPOSIT only. Settled, non-reversal transactions only."
  → SQL           stored verbatim, re-runnable — and it re-runs to 30.23
  → source rows   43 transaction ids, TX-00229881, TX-00229891, …
  → clause        §5.2 AML Policy — "detect transaction structuring … deliberately
                   kept below the $10,000 AUD reporting threshold"
```

**Target user:** a compliance analyst or MLRO at a mid-size commercial bank who has
to put their name on the number.

---

## Results

Everything below is measured and reproducible. Nothing is asserted.

### Detection, scored against a held-out answer key

`data/out/ground_truth.csv` was generated alongside the data, **never loaded into
Snowflake**, and is read only by the local harness. The detectors implement
thresholds quoted from regulatory clauses and cannot see which counterparties are
planted.

| Typology | Precision | Recall | F1 |
|---|---:|---:|---:|
| Structuring | 1.000 | 1.000 | **1.000** |
| Round-tripping | 1.000 | 1.000 | **1.000** |
| Dormant reactivation | 1.000 | 1.000 | **1.000** |
| Mule network | 1.000 | 1.000 | **1.000** |
| Sanctions near-match | 1.000 | 1.000 | **1.000** |
| Velocity spike | 0.091 | 0.667 | 0.160 |
| **Overall** | **0.459** | **0.944** | **0.618** |

**We find 17 of 18 planted positives.** All precision loss is one detector, and
[`evals/report.md`](evals/report.md) explains exactly why we did not remove it to
reach 1.000 — velocity monitoring is a regulatory requirement, not an optional
enhancement.

The sanctions case is the one worth inspecting: ground truth plants one true match
**and one near-match already adjudicated a false positive**. The detector respects
the adjudication and flags only the true one. A score-only detector catches both,
scores perfect recall, and is worse.

### Governance — measured, not claimed

We expected an ungoverned LLM to answer inconsistently. Across 25 runs the
generated SQL was **byte-identical every time**. The hypothesis was wrong, and the
real finding is sharper:

| Question | Ungoverned | Governed | |
|---|---:|---:|---|
| Suspicious volume, Q3 | 8,797,923 | 4,295,229 | **+105 %** |
| Exposure to CP-STRUCT-01 | 87,185 | 87,185 | agree |
| Alert closure rate | 63.6 % | 63.6 % | agree |
| SAR filing share | 6.5 % | 6.5 % | agree |
| High-risk in Singapore | 23 | 36 | **−36 %** |

**The ungoverned path is perfectly consistent, perfectly confident, and materially
wrong on two of five** — sounding identical when it is right and when it is not.
The $4.5M overstatement comes from four missed decisions at once: booking date
rather than value date, reversals counted, unsettled counted, and transactions on
already-closed alerts treated as suspicious.

Q2 agrees **by coincidence** — it computes direct exposure rather than
entity-resolved, and matches only because that counterparty has no
beneficial-ownership links. Method and per-question SQL diffs:
[`docs/governance-experiment.md`](docs/governance-experiment.md).

### Retrieval and routing

| Measure | Result |
|---|---|
| Clause retrieval, top-1 | **11 / 12** |
| Clause retrieval, top-3 | **12 / 12** |
| Agent tool-routing | **5 / 5** including the question it must refuse |

The corpus was built to make retrieval *hard*: 17 clauses carry competing
deadlines, 13 define dormancy differently, 13 state dollar thresholds. Precision
measured over a corpus with no plausible wrong answers would prove nothing.

---

## Architecture

```
          11 regulatory PDFs                     synthetic banking data
                  │                                       │
        AI_PARSE_DOCUMENT                          COPY INTO  →  RAW (11 tables)
                  │                                       │
                  │                              Dynamic Tables  →  CURATED (4)
                  │                                       │   entity resolution,
                  │                                       │   explicit governance
                  │                                       │   columns
                  │                              Dynamic Tables  →  GOLD (5)
                  │                                       │
         CORTEX SEARCH                            SEMANTIC VIEW
      72 clauses, cited                    7 governed metrics, 10 verified queries
                  │                                       │
                  └───────────────┬───────────────────────┘
                                  │
                          CORTEX AGENT
               routes: figures → Analyst, rules → Search, both when
               a number needs a rule — and refuses what it cannot ground
                                  │
            ┌─────────────────────┼─────────────────────┐
     risk-scanner        regulation-linker        finding-writer
   governed query +        clause retrieval      assembles the finding;
   provenance bundle       with citations        cannot state a figure
            │                     │              it was not given
            └─────────────────────┴──────────┬───────────┘
                                             │
                                   provenance-logger
                              append-only, content-hashed
                                             │
                        GOVERNANCE.FINDINGS + FINDING_FOOTNOTES
                                             │
                      ┌──────────────────────┴───────────────────┐
            Streamlit in Snowflake                    public web app
              (native, needs login)              (open to anyone, live queries)
```

### The four CoCo skills, and how they connect

Each has a single responsibility and an explicit boundary — the boundaries are what
make them composable, and what would let another team lift one out.

| Skill | Does | Explicitly will **not** |
|---|---|---|
| [`risk-scanner`](skills/risk-scanner/) | Runs a governed metric query, returns a provenance bundle | Never writes, never generates prose |
| [`regulation-linker`](skills/regulation-linker/) | Retrieves governing clauses with full citation metadata | Never runs analytical SQL, never computes |
| [`finding-writer`](skills/finding-writer/) | Assembles the finding with footnote markers | **Cannot** state a figure it was not given |
| [`provenance-logger`](skills/provenance-logger/) | Persists finding + footnotes with content hash | Never updates, never deletes |

They chain: `risk-scanner` and `regulation-linker` run independently and feed
`finding-writer`, whose output goes to `provenance-logger`.

**How `finding-writer` blocks a hallucinated number** — two layers, neither of which
is a prompt asking nicely:

1. **Input containment.** The prompt it builds contains only numbered facts extracted
   from provenance bundles. The model gets no database access and no SQL execution.
   There is no path for an ungoverned number to enter.
2. **Output validation.** Every number in the generated text must appear in an input
   fact, and every `[N]` marker must map to a real one. Validation failure returns an
   error, never the finding.

---

## Snowflake features used

| Feature | Where |
|---|---|
| Semantic Views + verified queries | 7 governed metrics, 10 VQRs — the core of the product |
| Cortex Analyst | every figure |
| Cortex Search | 72 clauses with citation attributes |
| Cortex Agents | tool routing, refusal behaviour |
| `AI_PARSE_DOCUMENT` | 11 regulatory PDFs parsed inside Snowflake |
| Dynamic Tables | 9, across CURATED and GOLD |
| Data Metric Functions | 17 null/duplicate checks on GOLD |
| Row Access Policies | AU/SG analyst personas, justified against AUSTRAC Part 8.1 and MAS Notice 626 §13 |
| Streamlit in Snowflake | the native app |

No LangChain, no external vector store, no third-party LLM API. Where Snowflake has
a feature, we used it.

---

## How CoCo was used

The brief requires CoCo across the full lifecycle and says judges will look for
evidence at every stage. [`docs/coco/`](docs/coco/) is that evidence — **11 full
session transcripts (220 KB) and 26 verbatim prompts**, exported from CoCo's own
conversation store, not written afterwards.

Any transcript can be re-derived on a machine with this project's connection:

```bash
cortex conversations list
cortex conversations transcript <session-id>
```

| Phase | Evidence |
|---|---|
| **Planning** | [`01-planning.md`](docs/coco/01-planning.md) — a design-only session; the commit lands *before* any build commit, visible in `git log` |
| **Development** | [`02-development.md`](docs/coco/02-development.md) — pipelines, semantic view, search, agent, skills |
| **Execution** | orchestration and scheduled runs |
| **Testing** | [`04-validation.md`](docs/coco/04-validation.md) — audits, the eval harness, edge cases |

### Three sessions failed, and they are kept

| Session | What happened | How it was caught |
|---|---|---|
| `dbfd0f33` | Exceeded its window; the calling shell lost stdout | A follow-up query found RAW tables **empty** |
| `bf873376` | Terminated before executing the load | Same |
| `9bc3452c` | Reported success having created 2 of 5 GOLD objects and 0 DMFs | An audit session queried Snowflake directly |

The pattern across all three: **the agent's summary said success; the database said
otherwise.** Every claim in this repo is therefore verified by querying Snowflake,
never by reading a transcript. That discipline also caught a generator that declared
itself deterministic while minting IDs with `uuid.uuid4()` — which ignores
`random.seed()` and silently invalidated the answer key.

---

## Reproduce it from scratch

Every object is idempotent DDL and every row is generated, so the whole project
rebuilds in any Snowflake account:

```bash
# 1. Data — byte-for-byte reproducible
python3 data/generate.py
python3 data/generate.py --verify-determinism     # 12/12 files, SHA-256 identical

# 2. Snowflake, in order
snow sql -f sql/00-foundation.sql      # warehouse (XS, 60s auto-suspend), db, schemas
snow sql -f sql/01-raw.sql             # 11 RAW tables
snow sql -f sql/02-load.sql            # stage + COPY INTO
snow sql -f sql/03-curated.sql         # 4 dynamic tables
snow sql -f sql/04-gold.sql            # 5 dynamic tables
snow sql -f sql/05-quality.sql         # 17 data metric functions
snow sql -f sql/06-semantic.sql        # semantic view + verified queries
snow sql -f sql/07-search.sql          # PDF stage, AI_PARSE_DOCUMENT, Cortex Search
snow sql -f sql/08-governance.sql      # findings + footnotes
snow sql -f sql/09-agent.sql           # Cortex Agent
sql/10-experiment.sql  sql/11-streamlit.sql

# 3. Score it
python3 evals/run_eval.py --connection <your-connection>
```

The determinism self-test is what makes this exact rather than approximate: the
answer key regenerates in lockstep with the data, so a rebuild in a second account
produces identical ids.

---

## Judging

| Criterion | Where to look |
|---|---|
| **Real-world relevance** (30 %) | The [problem](#the-problem) — defending the number, not finding it. Clauses reference AUSTRAC and MAS regimes; metrics carry the governance decision a compliance officer would recognise |
| **Technical execution** (40 %) | [Snowflake features](#snowflake-features-used) · [architecture](#architecture) · [4 skills](#the-four-coco-skills-and-how-they-connect) · [CoCo evidence](#how-coco-was-used) · `sql/` |
| **Solution completeness** (30 %) | A public link that opens · a native app · [scored evaluation](#results) · [reproduce from scratch](#reproduce-it-from-scratch) · failures recorded rather than pruned |

---

## What this does not do

Stated plainly, because a reviewer will find these anyway:

- **Velocity-spike detection is weak** — 20 false positives. Kept because the
  regulation requires it; not removed to flatter the score.
- **`CP-VELOCITY-00` is a miss.** Its spike peaks at 2.4× its own baseline, below
  the 5× the policy defines. Catching it would mean relaxing the multiplier below
  the AML Policy level.
- **The agent's routing is imperfect.** Asked to forecast, it loads semantic context
  before refusing. Right outcome, loose routing.
- **Planted signals are cooperative.** They behave exactly as the typology describes.
  Real launderers adapt.
- **Scale is synthetic.** 809 counterparties. False-positive rates on a 100k-party
  portfolio would differ materially.
- `evals/report.md` lists five further things the harness does not prove.

---

## Data

**All data is synthetic.** No production, scraped or real customer data is used
anywhere. Counterparties, transactions, alerts and cases are generated by
`data/generate.py`; the 11 regulatory documents are fictional and every page carries
a `SYNTHETIC_DATA_PAPERTRAIL_2026` watermark. The bank does not exist.
