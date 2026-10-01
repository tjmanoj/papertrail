import { withSnowflake } from '../../../lib/snowflake';
import { summarise } from '../../../lib/agent';

export const runtime = 'nodejs';
export const maxDuration = 60;
export const dynamic = 'force-dynamic';

export async function POST(request) {
  let question;
  try { ({ question } = await request.json()); }
  catch { return Response.json({ error: 'Invalid request body.' }, { status: 400 }); }

  if (!question || typeof question !== 'string' || question.length > 500) {
    return Response.json({ error: 'Ask a question of 500 characters or fewer.' }, { status: 400 });
  }

  try {
    const result = await withSnowflake(async (q) => {
      const body = JSON.stringify({
        messages: [{ role: 'user', content: [{ type: 'text', text: question }] }],
      });
      const rows = await q(
        `SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN('PAPERTRAIL.GOLD.PAPERTRAIL_AGENT', ?) AS R`,
        [body],
      );
      return summarise(rows[0]?.R);
    });
    return Response.json(result);
  } catch (err) {
    return Response.json(
      { error: 'The agent could not be reached.', detail: String(err.message || err).slice(0, 300) },
      { status: 502 },
    );
  }
}
