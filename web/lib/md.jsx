/* A deliberately small markdown renderer for agent answers.
 * Handles only what the agent actually emits: bold, inline code, bullet lists
 * and paragraphs. Builds React elements rather than injecting HTML, so a model
 * response can never introduce markup into the page. */
import { Fragment } from 'react';

function inline(text, keyBase) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let m;
  let i = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('**')) {
      out.push(<strong key={`${keyBase}-b${i++}`}>{tok.slice(2, -2)}</strong>);
    } else {
      out.push(
        <code key={`${keyBase}-c${i++}`} style={{ fontFamily: 'var(--mono)', fontSize: '.88em' }}>
          {tok.slice(1, -1)}
        </code>,
      );
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text }) {
  if (!text) return null;
  const lines = String(text).split('\n');
  const nodes = [];
  let bullets = [];

  const flush = () => {
    if (!bullets.length) return;
    nodes.push(
      <ul key={`ul-${nodes.length}`} style={{ margin: '0 0 12px', paddingLeft: 20 }}>
        {bullets.map((b, i) => (
          <li key={i} style={{ marginBottom: 4 }}>{inline(b, `li${nodes.length}-${i}`)}</li>
        ))}
      </ul>,
    );
    bullets = [];
  };

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    if (bullet) { bullets.push(bullet[1]); return; }
    flush();
    if (!line.trim()) return;
    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      nodes.push(
        <div key={`h-${idx}`} style={{ fontFamily: 'var(--cond)', fontWeight: 600, fontSize: 17, margin: '14px 0 6px', color: 'var(--ink)' }}>
          {inline(heading[2], `h${idx}`)}
        </div>,
      );
      return;
    }
    nodes.push(
      <p key={`p-${idx}`} style={{ margin: '0 0 12px' }}>{inline(line, `p${idx}`)}</p>,
    );
  });
  flush();

  return <Fragment>{nodes}</Fragment>;
}
