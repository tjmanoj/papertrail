# Phase 1 - Planning

**Surface:** CoCo CLI (Cortex Code v1.1.87), headless via `cortex exec`
**Connection:** AT72852 · account `xd71507.ap-southeast-7.aws`
**Session ID:** `2d46d885-edae-47cb-a49b-1fa09041d237`
**Date:** 2026-10-01
**Effort:** high · **Model:** auto

## Intent

Design the system before building any of it. The PS1 brief requires CoCo to be
used to "explore the data, frame the problem, draft the solution design, and
outline the data model, ontology, and workflow **before any build begins**."
This session produced design documents only - no Snowflake objects, no DDL, no
data. Git history shows this commit landing before the first build commit.

## Prompt

Verbatim prompt: [`prompts/01-planning.md`](prompts/01-planning.md)

## Outputs

| File | Lines | Contents |
|---|---|---|
| [`docs/data-model.md`](../data-model.md) | 593 | 11 entities with grain/keys/relationships; 7 governed metrics each with a divergence analysis; 6 regulatory documents with a clause-to-metric mapping; 6 planted risk typologies specified at row level |
| [`docs/architecture.md`](../architecture.md) | 369 | signal → evidence → finding path; the four skills with boundaries; row-access personas with regulatory justification; the provenance mechanism; risks |

## Decisions that came out of it

- **Reversals are modelled explicitly** (`is_reversal`) rather than omitted, because
  gross-vs-net is one of the most realistic ways two analysts diverge on suspicious
  volume. The data model is deliberately built to make ungoverned divergence possible.
- **Seven governed metrics**, each justified by a concrete divergence mode - date basis,
  pending vs settled, cohort vs snapshot, denominator scope, entity resolution,
  business vs calendar days, stale ratings.
- **`finding-writer` cannot hallucinate figures by construction** - it receives
  provenance bundles and emits footnote references, rather than being asked not to
  invent numbers.
- **Row access policies justified against real regimes** - AUSTRAC Part 8.1 and
  MAS Notice 626 §13 - so the persona toggle reflects a real legal constraint.
- **Provenance persisted in two tables** (`GOVERNANCE.FINDINGS`,
  `GOVERNANCE.FINDING_FOOTNOTES`) so any figure resolves to metric definition,
  SQL, source row keys and regulation clause.

## Transcript

- [`transcripts/01-planning-stdout.txt`](transcripts/01-planning-stdout.txt)
- [`transcripts/01-planning-final.txt`](transcripts/01-planning-final.txt)
- Retrievable in full via `cortex conversations transcript 2d46d885-edae-47cb-a49b-1fa09041d237`
