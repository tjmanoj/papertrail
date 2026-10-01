# PaperTrail - project brief for CoCo

Team **Provenance** · Snowflake CoCo CLI Hackathon 2026, GCC Edition
Problem statement 1 - *Risk, Fraud and Regulatory Intelligence Copilot*

## What we are building

An audit-ready risk and regulatory copilot for a fictional bank. A compliance
analyst asks a question in plain English; the system answers through a **governed
semantic view**, and can then emit a **regulatory finding** in which every figure
is a footnote that resolves to its metric definition, the exact SQL that produced
it, the source rows, and the clause of regulation it satisfies.

The thesis in one line: **finding the risk signal is cheap; defending the number
is expensive.** PaperTrail defends the number.

## Non-negotiable constraints

1. **Everything native to Snowflake.** No LangChain, LangGraph, external vector
   stores, or third-party LLM APIs. If Snowflake has a feature for it, use that
   feature. This is a judged criterion, not a preference.
2. **Synthetic data only.** Never real, scraped, or production data. Generated
   data must be *referentially consistent* - foreign keys resolve, dates order
   sensibly, and fraud signal is genuinely present rather than random noise.
   Every generated document carries a synthetic watermark.
3. **No figure without provenance.** If a number cannot be traced to governed SQL
   and source rows, the system must decline to state it. This is enforced
   structurally in SQL, not by asking a model nicely.
4. **Cost discipline.** Warehouse is XS with `AUTO_SUSPEND = 60`. Never create a
   larger warehouse or disable auto-suspend. Never leave a warehouse resumed at
   the end of a session.

## Conventions

- All DDL lives in `sql/`, numbered in run order, and must be **idempotent**  -
  `CREATE OR REPLACE` / `IF NOT EXISTS` throughout, so the entire project can be
  rebuilt from scratch in any account. Never create an object only in-session;
  if it matters, it belongs in a numbered file.
- Semantic view definition and its verified queries live in `semantic/`.
- Reusable skills live in `skills/<skill-name>/`, each with its own `README.md`
  explaining the interface so another team could lift it out and use it.
- Python for data generation lives in `data/`.
- Evaluation questions, ground truth and score reports live in `evals/`.
- Database `PAPERTRAIL`, schemas `RAW`, `CURATED`, `GOLD`, `GOVERNANCE`.

## Naming

Business-facing names, not warehouse-internal ones: a compliance officer should
recognise every metric and dimension in the semantic view. Prefer
`counterparty_exposure_usd` over `cp_exp_amt`.

## How I want you to work

- Explain what you are about to change before changing it, and say why.
- Prefer one working component over three half-built ones.
- When a Snowflake feature could replace code we would otherwise write, say so.
- If a request would breach a constraint above, refuse and explain - do not
  quietly work around it.
