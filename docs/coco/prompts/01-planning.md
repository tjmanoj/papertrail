PHASE 1 PLANNING SESSION for PaperTrail. Read CORTEX.md first.

DESIGN ONLY. Create NO Snowflake objects, generate NO data, write NO DDL.
This session's only outputs are two design documents. A judge will read them as
evidence the system was designed before it was built, so they must stand alone.

Write docs/data-model.md covering:

1. ENTITIES. The things a mid-size commercial bank's AML and risk function
   actually works with: counterparties, accounts, transactions, alerts, cases,
   watchlist/sanctions entries, regulatory documents. For each give: what it is
   in business terms, its grain, its key, its relationships, and a realistic
   column set using business-facing names.

2. GOVERNED METRICS. For each metric give: the business definition a compliance
   officer would recognise, the exact intended SQL semantics, and — most
   importantly — WHY IT IS DANGEROUS UNGOVERNED. Name the specific, plausible
   ways two analysts would compute it differently and land on different numbers
   (different date basis, inclusion of reversals, netting vs gross, timezone
   boundary, pending vs settled, entity resolution). This asymmetry is the whole
   pitch of the product, so be concrete and realistic rather than generic.

3. UNSTRUCTURED SIDE. What regulatory documents such a bank holds — AML policy,
   sanctions screening procedure, STR/SAR filing guidance, KYC refresh policy,
   Basel liquidity guidance. What clauses each contains, and which structured
   metric needs to cite which clause.

4. PLANTED SIGNAL. Where risk signal will be deliberately planted in the
   synthetic data so detection is genuinely detectable rather than noise. Name
   the specific typologies — structuring/smurfing, round-tripping, dormant
   account reactivation, sanctions near-match, velocity spike, mule networks —
   and exactly how each manifests in the data at row level.

Write docs/architecture.md covering:

5. THE PATH. End to end: signal -> evidence -> documented finding. What happens
   at each step, which specific Snowflake feature performs it, what the handoff
   between steps looks like.

6. SKILL DECOMPOSITION. Exactly four reusable CoCo skills: names, the single
   responsibility of each, inputs, outputs, and how they chain. The submission
   deck must show "which CoCo CLI skills are used and how they connect", so make
   the boundaries crisp and non-overlapping.

7. ROW-LEVEL GOVERNANCE. Where Row Access Policies apply, and what two analyst
   personas in different jurisdictions legitimately see differently, with a
   realistic regulatory justification for the difference.

8. PROVENANCE MECHANISM. How a single figure in a finished finding resolves down
   to its metric definition, the exact SQL, the source rows, and the regulation
   clause. Be specific about what must be persisted to make that possible.

9. RISKS AND OPEN QUESTIONS. What you think will be hard, and what might not
   work in three days.

Be opinionated and concrete. Where you must assume something about how a bank
operates, state it explicitly as an assumption. Do not pad.
