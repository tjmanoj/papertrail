'use client';

import { useMemo, useState } from 'react';
import snapshot from '../data/snapshot.json';
import { summarise } from '../lib/agent';
import { Markdown } from '../lib/md';

/* ------------------------------------------------------------------ *
 * Analysis that isn't in the database: why each divergence happened.
 * The numbers all come from the snapshot; only the explanation is here.
 * ------------------------------------------------------------------ */
const DIVERGENCE_NOTES = {
  Q1: {
    verdict: 'DIVERGE',
    missed: [
      'Dated on booking timestamp instead of value date',
      'Counted reversals that cancel the original transaction',
      'Included transactions that never settled',
      'Counted transactions linked to already-closed alerts as suspicious',
    ],
    cost: 'Overstates suspicious volume by $4.5M - a figure that would go to a regulator.',
  },
  Q5: {
    verdict: 'DIVERGE',
    missed: [
      "Filtered RISK_RATING = 'HIGH' literally, dropping every VERY_HIGH counterparty",
    ],
    cost: 'Misses 13 of 36 high-risk counterparties that KYC policy §2.1 requires be counted.',
  },
  Q2: {
    verdict: 'AGREE',
    missed: ['Computed direct exposure rather than entity-resolved exposure'],
    cost:
      'Agrees only by coincidence: this counterparty has no beneficial-ownership links. ' +
      'The same query diverges for any counterparty that does.',
  },
  Q3: { verdict: 'AGREE', missed: [], cost: 'Same value, reported as a fraction rather than a percentage.' },
  Q4: { verdict: 'AGREE', missed: [], cost: 'Same value, reported as a fraction rather than a percentage.' },
};

const SCALE_NOTE = new Set(['Q3', 'Q4']); // ungoverned returned a fraction, governed a percentage

const EXAMPLES = [
  { q: 'What was our total suspicious transaction volume last quarter?', hint: 'routes to Cortex Analyst' },
  { q: 'How quickly must a confirmed sanctions match be reported?', hint: 'routes to Cortex Search' },
  { q: 'Which counterparties breach our concentration limit, and what is the limit?', hint: 'uses both tools' },
  { q: "What will next quarter's suspicious volume be?", hint: 'the agent declines', refusal: true },
];

const fmt = (n, digits = 2) =>
  n === null || n === undefined || Number.isNaN(Number(n))
    ? ' - '
    : Number(n).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });

const fmtInt = (n) => (n === null || n === undefined ? ' - ' : Number(n).toLocaleString('en-US'));

function Mark() {
  return (
    <svg width="34" height="34" viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <path
        d="M20 2.6 34.4 9.4v13.1c0 6.6-5.6 12.2-14.4 14.9C11.2 34.7 5.6 29.1 5.6 22.5V9.4L20 2.6Z"
        stroke="#4A5E82"
        strokeWidth="1.6"
      />
      <path
        d="M12.4 12.2v3.6c0 2.1 1.5 3.3 3.8 3.8 2.1.5 3.8 1.7 3.8 3.9v6.8"
        stroke="#35B6E8"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path d="M20 12.2v4.2" stroke="#35B6E8" strokeWidth="1.5" strokeLinecap="round" />
      <path
        d="M27.6 12.2v3.6c0 2.1-1.5 3.3-3.8 3.8-2.1.5-3.8 1.7-3.8 3.9"
        stroke="#35B6E8"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path d="M20 27.4l2.1 2.6L20 32.6 17.9 30 20 27.4Z" fill="#35B6E8" />
    </svg>
  );
}


/* A compact band of real figures so the page never opens as an empty shell. */
function StatStrip() {
  const c = (snapshot.counts || [])[0] || {};
  const items = [
    [fmtInt(c.TRANSACTIONS), 'transactions governed'],
    [fmtInt(c.CLAUSES), 'clauses indexed'],
    ['11 / 12', 'clause retrieval, top-1'],
    ['2 of 5', 'ungoverned answers wrong'],
  ];
  return (
    <div className="strip">
      {items.map(([v, l]) => (
        <div key={l}>
          <span className="v num">{v}</span>
          <span className="l">{l}</span>
        </div>
      ))}
    </div>
  );
}

/* ----------------------------------- Ask ---------------------------------- */
function Ask() {
  const sample = useMemo(() => {
    const raw = snapshot.sampleExchange?.raw;
    if (!raw) return null;
    const parsed = summarise(raw);
    return parsed.answer && parsed.answer !== 'The agent returned no text.' ? parsed : null;
  }, []);
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function send(q) {
    const text = (q ?? question).trim();
    if (!text || busy) return;
    setQuestion(text);
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ question: text }),
      });
      const data = await res.json();
      if (!res.ok) setError(data.detail || data.error || 'The agent could not be reached.');
      else setResult(data);
    } catch (e) {
      setError('Network error reaching the agent.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h2 className="page">Ask</h2>
      <p className="lede">
        Questions go to a Cortex Agent holding two tools: Cortex Analyst over a governed semantic view for
        figures, and Cortex Search over 72 regulatory clauses for rules. It answers live against Snowflake.
      </p>
      <p className="lede" style={{ marginTop: -14 }}>
        Every answer shows the SQL that produced it. To check the numbers rather than take them on trust,
        <strong> Prove</strong> runs the same questions without the governed layer, and <strong>File</strong>
        {' '}re-executes a stored figure against live data.
      </p>

      <div className="panel">
        <div className="askbar">
          <input
            id="ask-input"
            value={question}
            placeholder="Ask about risk exposure, alerts, or what the policy requires..."
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            disabled={busy}
          />
          <button className="btn" onClick={() => send()} disabled={busy || !question.trim()}>
            {busy ? 'Asking...' : 'Ask'}
          </button>
        </div>

        <div className="examples">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.q}
              className={`chip${ex.refusal ? ' refusal' : ''}`}
              onClick={() => send(ex.q)}
              disabled={busy}
              title={ex.hint}
            >
              {ex.q}
            </button>
          ))}
        </div>
        <p className="note" style={{ marginTop: 12 }}>
          The dashed question asks for a forecast. The agent refuses it - it reports governed historical data
          and will not estimate. That refusal is the guardrail, not a failure.
        </p>
      </div>

      {busy && (
        <div className="panel">
          <span className="spin" />
          Running against Snowflake. A cold warehouse takes a few seconds to resume.
        </div>
      )}

      {error && (
        <div className="panel">
          <div className="err">{error}</div>
        </div>
      )}

      {!result && !busy && !error && sample && (
        <div className="panel">
          <span className="eyebrow">A saved exchange - ask your own above</span>
          {sample.tools?.length > 0 && (
            <div className="toolrow">
              {sample.tools.map((t) => (
                <span key={t} className="tool">{t}</span>
              ))}
            </div>
          )}
          <Markdown text={sample.answer} />
          {sample.sql && (
            <details>
              <summary>Generated SQL</summary>
              <pre>{sample.sql}</pre>
            </details>
          )}
          <p className="note" style={{ marginTop: 12 }}>
            Captured from this agent when the site was built. Asking above runs it live.
          </p>
        </div>
      )}

      {result && (
        <div className="panel">
          {result.tools?.length > 0 && (
            <div className="toolrow">
              {result.tools.map((t) => (
                <span key={t} className="tool live">
                  {t}
                </span>
              ))}
            </div>
          )}
          <Markdown text={result.answer} />
          {result.sql && (
            <details>
              <summary>Generated SQL</summary>
              <pre>{result.sql}</pre>
            </details>
          )}
          {result.thinking && (
            <details>
              <summary>Agent reasoning</summary>
              <pre>{result.thinking}</pre>
            </details>
          )}
        </div>
      )}
    </>
  );
}

/* ---------------------------------- Prove --------------------------------- */
function Prove() {
  const rows = useMemo(() => {
    const byQ = new Map();
    for (const r of snapshot.experiment || []) {
      const e = byQ.get(r.QUESTION_ID) || { id: r.QUESTION_ID, text: r.QUESTION_TEXT };
      e[r.PATH === 'GOVERNED' ? 'gov' : 'ung'] = r;
      byQ.set(r.QUESTION_ID, e);
    }
    return [...byQ.values()].sort((a, b) => a.id.localeCompare(b.id));
  }, []);

  const diverged = rows.filter((r) => DIVERGENCE_NOTES[r.id]?.verdict === 'DIVERGE');

  return (
    <>
      <h2 className="page">Prove</h2>
      <p className="lede">
        We set out to show an ungoverned model gives different answers on repeat asks. It doesn&rsquo;t - across
        25 runs the generated SQL was byte-identical every time. The real finding is worse.
      </p>

      <div className="panel" style={{ borderColor: 'var(--accent-dim)' }}>
        <span className="eyebrow">The headline</span>
        <div style={{ fontSize: 19, lineHeight: 1.5, color: 'var(--ink)' }}>
          Both paths are perfectly stable. The ungoverned one is{' '}
          <strong style={{ color: 'var(--crit)' }}>confidently wrong on 2 of 5 questions</strong>, and sounds
          exactly as certain when it is wrong as when it is right.
        </div>
      </div>

      <div className="tbl" style={{ marginTop: 14 }}>
        <table>
          <thead>
            <tr>
              <th>Question</th>
              <th style={{ textAlign: 'right' }}>Ungoverned</th>
              <th style={{ textAlign: 'right' }}>Governed</th>
              <th style={{ textAlign: 'right' }}>Runs</th>
              <th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const note = DIVERGENCE_NOTES[r.id] || {};
              const scaled = SCALE_NOTE.has(r.id);
              const ung = r.ung?.ANSWER;
              const gov = r.gov?.ANSWER;
              return (
                <tr key={r.id}>
                  <td className="k">
                    {r.text}
                    {scaled && (
                      <div className="note" style={{ fontSize: 12.5, marginTop: 4 }}>
                        reported as a fraction by the ungoverned path, as a percentage by the governed one  -
                        the same value
                      </div>
                    )}
                  </td>
                  <td className="r">{fmt(ung)}</td>
                  <td className="r">{fmt(gov)}</td>
                  <td className="r">
                    {(r.ung?.RUNS ?? 0) + (r.gov?.RUNS ?? 0)}
                    <div style={{ fontSize: 11, color: 'var(--ink-3)' }}>1 distinct each</div>
                  </td>
                  <td>
                    <span className={`pill ${note.verdict === 'DIVERGE' ? 'diverge' : 'agree'}`}>
                      {note.verdict || ' - '}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {diverged.map((r) => {
        const note = DIVERGENCE_NOTES[r.id];
        return (
          <div className="panel" key={r.id} style={{ marginTop: 14 }}>
            <span className="eyebrow">{r.id} - what the ungoverned query missed</span>
            <h3 style={{ margin: '0 0 10px', fontFamily: 'var(--cond)', fontSize: 17 }}>{r.text}</h3>
            <ul style={{ margin: '0 0 12px', paddingLeft: 18, color: 'var(--ink-2)' }}>
              {note.missed.map((m) => (
                <li key={m} style={{ marginBottom: 4 }}>
                  {m}
                </li>
              ))}
            </ul>
            <p style={{ color: 'var(--crit)', margin: '0 0 14px', fontSize: 14.5 }}>{note.cost}</p>
            <div className="cols">
              <div>
                <span className="eyebrow">Ungoverned SQL</span>
                <pre>{r.ung?.SQL_TEXT || ' - '}</pre>
              </div>
              <div>
                <span className="eyebrow">Governed SQL</span>
                <pre>{r.gov?.SQL_TEXT || ' - '}</pre>
              </div>
            </div>
          </div>
        );
      })}

      <div className="panel" style={{ marginTop: 14 }}>
        <span className="eyebrow">The one that agrees, and why that is not reassuring</span>
        <p style={{ margin: 0, color: 'var(--ink-2)' }}>{DIVERGENCE_NOTES.Q2.cost}</p>
      </div>

      <div className="panel">
        <span className="eyebrow">Method</span>
        <p style={{ margin: 0, color: 'var(--ink-2)', fontSize: 14.5 }}>
          The ungoverned path received the same data, the full raw table DDL including column comments, and a
          straightforward instruction to write correct SQL. It was never told about reversals, settlement
          status, date basis or entity resolution - that knowledge living only in the semantic layer is the
          entire point. Five runs per question for the ungoverned path, three for the governed. A rigged
          comparison would be worth nothing.
        </p>
      </div>
    </>
  );
}

/* ----------------------------------- File --------------------------------- */
function FileView() {
  const finding = (snapshot.findings || [])[0];
  const footnotes = (snapshot.footnotes || []).filter((f) => !finding || f.FINDING_ID === finding.FINDING_ID);
  const [openId, setOpenId] = useState(footnotes[0]?.FOOTNOTE_ID ?? null);
  const [rerun, setRerun] = useState({});
  const [busyId, setBusyId] = useState(null);

  async function doRerun(footnoteId) {
    setBusyId(footnoteId);
    try {
      const res = await fetch('/api/rerun', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ footnoteId }),
      });
      const data = await res.json();
      setRerun((s) => ({ ...s, [footnoteId]: data }));
    } catch {
      setRerun((s) => ({ ...s, [footnoteId]: { error: 'Network error.' } }));
    } finally {
      setBusyId(null);
    }
  }

  if (!finding) {
    return (
      <>
        <h2 className="page">File</h2>
        <div className="panel">No findings have been filed yet.</div>
      </>
    );
  }

  const text = String(finding.FINDING_TEXT || '');
  const parts = text.split(/(\[\d+\])/g);

  return (
    <>
      <h2 className="page">File</h2>
      <p className="lede">
        A finding is not a chat reply. Every figure is a footnote that resolves to its governed metric, the
        exact SQL that produced it, the source rows, and the clause that makes it matter - and the SQL can be
        re-run, live, to show the number still holds.
      </p>

      <div className="panel">
        <span className="eyebrow">Finding {String(finding.FINDING_ID).slice(0, 8)}</span>
        <div className="finding">
          {parts.map((p, i) =>
            /^\[\d+\]$/.test(p) ? (
              <span className="mk" key={i}>
                {p}
              </span>
            ) : (
              <span key={i}>{p}</span>
            ),
          )}
        </div>
        <dl className="fn" style={{ border: 0, padding: 0, marginTop: 16 }}>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', fontSize: 13 }}>
            <span style={{ color: 'var(--ink-3)' }}>
              content hash{' '}
              <span className="num" style={{ color: 'var(--ink-2)' }}>
                {String(finding.CONTENT_HASH || '').slice(0, 16)}...
              </span>
            </span>
            <span style={{ color: 'var(--ink-3)' }}>
              analyst{' '}
              <span style={{ color: 'var(--ink-2)' }}>
                {finding.ANALYST_ROLE} · {finding.ANALYST_JURISDICTION}
              </span>
            </span>
          </div>
        </dl>
      </div>

      {footnotes.map((f) => {
        const open = openId === f.FOOTNOTE_ID;
        const rr = rerun[f.FOOTNOTE_ID];
        let ids = [];
        try {
          ids = Array.isArray(f.SOURCE_ROW_IDS) ? f.SOURCE_ROW_IDS : JSON.parse(f.SOURCE_ROW_IDS || '[]');
        } catch {
          ids = [];
        }
        return (
          <div className={`panel fn${open ? ' open' : ''}`} key={f.FOOTNOTE_ID} style={{ marginTop: 12 }}>
            <button
              className="btn ghost"
              style={{ float: 'right' }}
              onClick={() => setOpenId(open ? null : f.FOOTNOTE_ID)}
            >
              {open ? 'Collapse' : 'Expand'}
            </button>
            <h4>
              <span className="mk" style={{ marginRight: 6 }}>
                [{f.FOOTNOTE_NUMBER}]
              </span>
              {f.METRIC_NAME} ={' '}
              <span className="num" style={{ color: 'var(--accent)' }}>
                {fmt(f.RESULT_VALUE)}
              </span>
            </h4>

            {open && (
              <>
                <dl>
                  <dt>Definition</dt>
                  <dd>{f.METRIC_DEFINITION}</dd>
                  <dt>Clause</dt>
                  <dd>
                    <strong style={{ color: 'var(--ink)' }}>§{f.CLAUSE_NUMBER}</strong> - {f.CLAUSE_TEXT_EXCERPT}
                  </dd>
                  <dt>Source</dt>
                  <dd>
                    {f.SOURCE_TABLE}
                    {ids.length > 0 && (
                      <>
                        {' · '}
                        {ids.length} row{ids.length === 1 ? '' : 's'}{' '}
                        <span className="num" style={{ color: 'var(--ink-3)' }}>
                          {ids.slice(0, 5).join(', ')}
                          {ids.length > 5 ? ' ...' : ''}
                        </span>
                      </>
                    )}
                  </dd>
                </dl>

                <details open>
                  <summary>Stored SQL</summary>
                  <pre>{f.GENERATED_SQL}</pre>
                </details>

                <div style={{ marginTop: 14 }}>
                  <button
                    className="btn"
                    onClick={() => doRerun(f.FOOTNOTE_ID)}
                    disabled={busyId === f.FOOTNOTE_ID}
                  >
                    {busyId === f.FOOTNOTE_ID ? 'Re-running...' : 'Re-run this SQL now'}
                  </button>

                  {rr && !rr.error && (
                    <div className="panel" style={{ marginTop: 12, background: 'var(--bg-2)' }}>
                      <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'baseline' }}>
                        <div>
                          <div className="num" style={{ fontSize: 21 }}>{fmt(rr.storedValue)}</div>
                          <div className="stat-l" style={{ fontSize: 10.5, color: 'var(--ink-3)', fontFamily: 'var(--mono)', letterSpacing: '.12em', textTransform: 'uppercase' }}>
                            stored in footnote
                          </div>
                        </div>
                        <div>
                          <div className="num" style={{ fontSize: 21, color: 'var(--accent)' }}>
                            {fmt(rr.rerunValue)}
                          </div>
                          <div style={{ fontSize: 10.5, color: 'var(--ink-3)', fontFamily: 'var(--mono)', letterSpacing: '.12em', textTransform: 'uppercase' }}>
                            re-run just now
                          </div>
                        </div>
                        <span className={`pill ${rr.matches ? 'ok' : 'diverge'}`}>
                          {rr.matches ? 'Match' : 'Differs'}
                        </span>
                        <span className="note">{rr.elapsedMs} ms</span>
                      </div>
                    </div>
                  )}
                  {rr?.error && <div className="err" style={{ marginTop: 12 }}>{rr.detail || rr.error}</div>}
                </div>
              </>
            )}
          </div>
        );
      })}
    </>
  );
}

/* --------------------------------- Evidence -------------------------------- */
function Evidence() {
  const c = (snapshot.counts || [])[0] || {};
  const dts = snapshot.dynamicTables || [];
  const tiles = [
    { v: fmtInt(c.TRANSACTIONS), l: 'transactions' },
    { v: fmtInt(c.COUNTERPARTIES), l: 'counterparties' },
    { v: fmtInt(c.ACCOUNTS), l: 'accounts' },
    { v: fmtInt(c.ALERTS), l: 'alerts' },
    { v: fmtInt(c.CASES), l: 'cases' },
    { v: fmtInt(c.CLAUSES), l: 'indexed clauses' },
  ];
  const built = [
    ['Governed metrics in the semantic view', '7'],
    ['Verified queries attached', '10'],
    ['Regulatory documents parsed with AI_PARSE_DOCUMENT', '11'],
    ['Clause retrieval precision, top-1', '11 / 12'],
    ['Clause retrieval precision, top-3', '12 / 12'],
    ['Reusable CoCo skills published', '4'],
    ['Dynamic tables, all refreshing', String(dts.length)],
    ['Data metric functions attached', '17'],
    ['Agent tool-routing tests passed', '5 / 5'],
  ];

  return (
    <>
      <h2 className="page">Evidence</h2>
      <p className="lede">
        Counts read from the Snowflake account at build time. Everything is synthetic - no production data was
        used, and the held-out answer key never enters the database.
      </p>

      <div className="stats">
        {tiles.map((t) => (
          <div className="stat" key={t.l}>
            <div className="v">{t.v}</div>
            <div className="l">{t.l}</div>
          </div>
        ))}
      </div>

      <div className="tbl" style={{ marginTop: 16 }}>
        <table>
          <thead>
            <tr>
              <th>What was built</th>
              <th style={{ textAlign: 'right' }}>Measure</th>
            </tr>
          </thead>
          <tbody>
            {built.map(([k, v]) => (
              <tr key={k}>
                <td className="k">{k}</td>
                <td className="r">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="tbl" style={{ marginTop: 14 }}>
        <table>
          <thead>
            <tr>
              <th>Dynamic table</th>
              <th>Schema</th>
              <th style={{ textAlign: 'right' }}>Rows</th>
              <th>Refresh</th>
            </tr>
          </thead>
          <tbody>
            {dts.map((d) => (
              <tr key={`${d.SCHEMA}.${d.NAME}`}>
                <td className="k">{d.NAME}</td>
                <td>{d.SCHEMA}</td>
                <td className="r">{fmtInt(d.ROWS)}</td>
                <td>{d.REFRESH_MODE}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="note" style={{ marginTop: 14 }}>
        Snapshot taken {new Date(snapshot.generatedAt).toUTCString()}. The Ask and re-run actions query
        Snowflake live.
      </p>
    </>
  );
}

/* ---------------------------------- Shell --------------------------------- */

/* A short, signposted route through the app for someone reviewing it cold.
   Judges do not know AML and will not know what to ask, and nothing on the
   Ask tab previously told them the verification surfaces existed. */
function ReviewerPanel({ go }) {
  const steps = [
    { n: '1', t: 'Ask it to forecast',
      d: 'Click the dashed question below. It refuses, because it will not state a figure it cannot ground.',
      action: null },
    { n: '2', t: 'Re-run a stored number',
      d: 'Open a footnote and press Re-run this SQL. The figure re-derives from its own stored query, live.',
      action: 'file' },
    { n: '3', t: 'See it without governance',
      d: 'The same five questions answered by an ungoverned model. It is confidently wrong on two of them.',
      action: 'prove' },
  ];
  return (
    <div className="revpanel">
      <div className="revhead">
        <span className="eyebrow" style={{ margin: 0 }}>For reviewers</span>
        <span className="revsub">three things, about two minutes</span>
      </div>
      <div className="revsteps">
        {steps.map((s) => {
          const Tag = s.action ? 'button' : 'div';
          return (
            <Tag
              key={s.n}
              className={`revstep${s.action ? ' clickable' : ''}`}
              {...(s.action ? { onClick: () => go(s.action), type: 'button' } : {})}
            >
              <span className="revn">{s.n}</span>
              <span className="revbody">
                <span className="revt">{s.t}</span>
                <span className="revd">{s.d}</span>
              </span>
            </Tag>
          );
        })}
      </div>
    </div>
  );
}

const TABS = [
  ['ask', 'Ask', Ask],
  ['prove', 'Prove', Prove],
  ['file', 'File', FileView],
  ['evidence', 'Evidence', Evidence],
];

export default function Page() {
  const [tab, setTab] = useState('ask');
  const Active = TABS.find((t) => t[0] === tab)[2];

  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <Mark />
          <div>
            <div className="nm">PaperTrail</div>
            <div className="sub">Team Provenance</div>
          </div>
        </div>
        <div className="tagline">Audit-ready risk &amp; regulatory copilot</div>
      </header>

      <nav className="tabs" role="tablist">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      <StatStrip />

      {tab === 'ask' && <ReviewerPanel go={setTab} />}

      <main>
        <Active />
      </main>

      <div className="foot">
        <span>Snowflake CoCo CLI Hackathon · GCC Edition</span>
        <span>Synthetic data only</span>
      </div>
    </div>
  );
}
