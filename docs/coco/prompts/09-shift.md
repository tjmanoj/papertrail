Fix a demo-blocking data problem. Read CORTEX.md first.

THE PROBLEM: data/generate.py anchors the dataset to
  START_DATE = 2025-01-01, END_DATE = 2026-06-30
Today is 2026-10-01 and judging runs 5-22 October. So "last quarter" (Q3 2026)
contains only 71 of 240,798 transactions, and every time-relative question a
judge asks returns a near-empty result. The governed SQL is correct; the data
simply sits in the past.

THE FIX: shift the whole 18-month window forward by 3 months to
  START_DATE = 2025-04-01, END_DATE = 2026-09-30
so "last month" = September 2026, "last quarter" = Q3 2026, and "this year"
covers January-September 2026, all densely populated during judging.

Do this:

1. Update START_DATE and END_DATE.

2. AUDIT THE WHOLE FILE for any other hardcoded date that must move with them so
   the dataset stays internally coherent. I know of at least line ~305
   (onboard_date 2022-06-01) and line ~337 (rand_date over 2026-01-01..2026-03-01).
   Decide for each whether it is an absolute historical date that should stay put
   or a window-relative date that must shift, and say which you chose and why.
   Pay particular attention to the six planted typologies - their windows must
   land inside the new range, and DORMANT_REACTIVATION in particular needs its
   dormancy period and reactivation burst to still make sense.

3. Keep determinism. Do not introduce datetime.now() or any floating anchor -
   the dates must stay fixed constants so output is reproducible.

4. Regenerate data/out/ in full, including ground_truth.csv.

5. Run `python3 data/generate.py --verify-determinism` and show me the PASS output.

6. Verify locally and report:
   - new min/max transaction date, and a count per month for the final 6 months
   - transactions falling in Q3 2026 (should now be tens of thousands, not 71)
   - every ground_truth entity ID still resolves against the regenerated CSVs
   - zero orphan foreign keys

Do NOT load into Snowflake yet - that is the next session. Report concisely.
