/** Pulls the readable parts out of the agent's streamed response envelope.
 *  Shared by the live API route and the pre-captured sample on the page. */
export function summarise(raw) {
  let parsed;
  try { parsed = typeof raw === 'string' ? JSON.parse(raw) : raw; }
  catch { return { answer: String(raw ?? ''), tools: [], sql: null, thinking: null }; }

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
      const query = b.tool_use.input?.query || b.tool_use.input?.sql;
      if (query && !sql) sql = query;
    }
    const res = b.tool_results || b.tool_result;
    if (res) {
      const query = res?.content?.[0]?.json?.sql || res?.json?.sql;
      if (query && !sql) sql = query;
    }
  }

  return {
    answer: text.join('\n\n').trim() || 'The agent returned no text.',
    tools,
    sql,
    thinking,
  };
}
