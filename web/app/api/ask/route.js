import { withSnowflake } from '../../../lib/snowflake';

export const runtime = 'nodejs';
export const maxDuration = 60;
export const dynamic = 'force-dynamic';

/** Pulls the readable parts out of the agent's streamed response envelope. */
function summarise(raw) {
  let parsed;
  try { parsed = typeof raw === 'string' ? JSON.parse(raw) : raw; }
  catch { return { answer: String(raw), tools: [], sql: null, thinking: null }; }

  const blocks = [];
  const collect = (node) => {
    if (Array.isArray(node)) return node.forEach(collect);
    if (!node || typeof node !== 'object') return;
    if (node.content) collect(node.content);
    blocks.push(node);
  };
  collect(parsed);

  const tools = [];
  let sql = null;
  let thinking = null;
  const text = [];

  for (const b of blocks) {
    if (b.type === 'text' && typeof b.text === 'string') text.push(b.text);
    if (b.type === 'thinking' && b.thinking?.text && !thinking) thinking = b.thinking.text;
    if (b.tool_use) {
      const name = b.tool_use.name || b.tool_use.tool_name;
      if (name && !tools.includes(name)) tools.push(name);
      const q = b.tool_use.input?.query || b.tool_use.input?.sql;
      if (q && !sql) sql = q;
    }
    if (b.tool_results || b.tool_result) {
      const r = b.tool_results || b.tool_result;
      const q = r?.content?.[0]?.json?.sql || r?.json?.sql;
      if (q && !sql) sql = q;
    }
  }

  return {
    answer: text.join('\n\n').trim() || 'The agent returned no text.',
    tools,
    sql,
    thinking,
  };
}

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
