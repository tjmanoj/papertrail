Fix a reproducibility defect in data/generate.py. Read CORTEX.md first.

THE BUG: the generator claims to be deterministic (fixed SEED, random.seed and
np.random.seed are set) but line ~49 mints IDs with uuid.uuid4().hex[:12].
uuid4 draws from os.urandom and is NOT controlled by random.seed(), so every
run produces different account_id, alert_id, case_id and similar values.

Why it matters: data/out/ground_truth.csv references specific entity IDs. If the
data is ever regenerated the answer key silently stops matching, and our claim
that the project rebuilds identically in any Snowflake account is false.

Do this:

1. Replace the uuid4-based ID helper with a seed-deterministic one that still
   produces stable, collision-free, same-shaped IDs (same prefix, same length,
   hex-like). Derive it from the seeded `random` stream or a counter hashed with
   a fixed salt. Audit the whole file for any OTHER non-deterministic source -
   uuid, os.urandom, datetime.now, time(), set/dict iteration order affecting
   output order, unstable sort - and fix each one.

2. Add a determinism self-test: a mode or script that generates twice into two
   temp directories and compares SHA-256 of every output file, reporting PASS
   only if all hashes match. Wire it as `python data/generate.py --verify-determinism`
   or a separate data/verify_determinism.py - your choice, but document it.

3. Regenerate data/out/ from scratch with the fix, including a regenerated
   ground_truth.csv so key and data come from the same run.

4. Run the determinism self-test twice and show me the PASS output.

5. Verify locally, before touching Snowflake: every ground_truth entity ID must
   resolve against the regenerated CSVs, and foreign keys must have zero orphans.
   Report a table of results.

Do NOT load into Snowflake in this session - I will do that next. Do not change
sql/ or the RAW schema. Report concisely.
