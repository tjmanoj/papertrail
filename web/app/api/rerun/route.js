import { withSnowflake } from '../../../lib/snowflake';

export const runtime = 'nodejs';
export const maxDuration = 60;
export const dynamic = 'force-dynamic';

/**
 * Re-executes the SQL stored on a footnote and compares the result to the figure
 * recorded when the finding was written. This is the product's central claim, so
 * the SQL is read from the database by footnote id rather than accepted from the
 * client - a caller cannot substitute their own query.
 */
export async function POST(request) {
  let footnoteId;
  try { ({ footnoteId } = await request.json()); }
  catch { return Response.json({ error: 'Invalid request body.' }, { status: 400 }); }

  if (!footnoteId || typeof footnoteId !== 'string') {
    return Response.json({ error: 'A footnote id is required.' }, { status: 400 });
  }

  try {
    const result = await withSnowflake(async (q) => {
      const meta = await q(
        `SELECT FOOTNOTE_NUMBER, METRIC_NAME, RESULT_VALUE, GENERATED_SQL
           FROM PAPERTRAIL.GOVERNANCE.FINDING_FOOTNOTES
          WHERE FOOTNOTE_ID = ?`,
        [footnoteId],
      );
      if (!meta.length) return { error: 'No such footnote.' };

      const { FOOTNOTE_NUMBER, METRIC_NAME, RESULT_VALUE, GENERATED_SQL } = meta[0];
      const started = Date.now();
      const rows = await q(GENERATED_SQL);

      // Find the value in the returned row that corresponds to the stored figure.
      const row = rows[0] || {};
      const numbers = Object.entries(row)
        .filter(([, v]) => typeof v === 'number' || (!isNaN(parseFloat(v)) && v !== null))
        .map(([k, v]) => [k, parseFloat(v)]);

      const stored = parseFloat(RESULT_VALUE);
      const hit = numbers.find(([, v]) => Math.abs(v - stored) < 0.005);

      return {
        footnoteNumber: FOOTNOTE_NUMBER,
        metricName: METRIC_NAME,
        storedValue: stored,
        rerunValue: hit ? hit[1] : (numbers[0]?.[1] ?? null),
        matchedColumn: hit ? hit[0] : (numbers[0]?.[0] ?? null),
        matches: Boolean(hit),
        elapsedMs: Date.now() - started,
        sql: GENERATED_SQL,
        row,
      };
    });
    return Response.json(result);
  } catch (err) {
    return Response.json(
      { error: 'Could not re-run the query.', detail: String(err.message || err).slice(0, 300) },
      { status: 502 },
    );
  }
}
