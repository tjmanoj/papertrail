/* Pulls presentation data from Snowflake into data/snapshot.json at build time.
   Keeps the public page instant: no cold-warehouse wait on first paint. */
const fs = require('fs');
const path = require('path');
const sdk = require('snowflake-sdk');
sdk.configure({ logLevel: 'ERROR' });

const token = (process.env.SNOWFLAKE_PAT ||
  fs.readFileSync(process.env.HOME + '/.snowflake/manoj_pat.txt', 'utf8')).trim();

const conn = sdk.createConnection({
  account: process.env.SNOWFLAKE_ACCOUNT || 'xd71507.ap-southeast-7.aws',
  username: process.env.SNOWFLAKE_USER || 'TJMANOJ',
  authenticator: 'PROGRAMMATIC_ACCESS_TOKEN',
  token,
  role: 'ACCOUNTADMIN',
  warehouse: 'PAPERTRAIL_WH',
  database: 'PAPERTRAIL',
});

const q = (sqlText) => new Promise((res, rej) =>
  conn.execute({ sqlText, complete: (e, s, rows) => (e ? rej(e) : res(rows)) }));
const q2 = (sqlText, binds) => new Promise((res, rej) =>
  conn.execute({ sqlText, binds, complete: (e, s, rows) => (e ? rej(e) : res(rows)) }));

(async () => {
  await new Promise((res, rej) => conn.connect((e) => (e ? rej(e) : res())));
  const out = { generatedAt: new Date().toISOString() };

  const safe = async (key, sql, fallback) => {
    try { out[key] = await q(sql); }
    catch (e) { console.error(`  ! ${key}: ${e.message}`); out[key] = fallback; }
  };

  await safe('experiment', `
    SELECT QUESTION_ID, ANY_VALUE(QUESTION_TEXT) AS QUESTION_TEXT, PATH,
           ANY_VALUE(ANSWER_NUMERIC) AS ANSWER,
           COUNT(*) AS RUNS, COUNT(DISTINCT ANSWER_NUMERIC) AS DISTINCT_ANSWERS,
           COUNT(ERROR) AS ERRORS, ANY_VALUE(GENERATED_SQL) AS SQL_TEXT
    FROM PAPERTRAIL.GOVERNANCE.GOVERNANCE_EXPERIMENT
    GROUP BY QUESTION_ID, PATH ORDER BY QUESTION_ID, PATH`, []);

  await safe('findings', `
    SELECT * FROM PAPERTRAIL.GOVERNANCE.FINDINGS ORDER BY CREATED_AT DESC LIMIT 5`, []);

  await safe('footnotes', `
    SELECT * FROM PAPERTRAIL.GOVERNANCE.FINDING_FOOTNOTES ORDER BY FOOTNOTE_NUMBER`, []);

  await safe('counts', `
    SELECT
      (SELECT COUNT(*) FROM PAPERTRAIL.GOLD.FACT_TRANSACTION)   AS TRANSACTIONS,
      (SELECT COUNT(*) FROM PAPERTRAIL.GOLD.DIM_COUNTERPARTY)   AS COUNTERPARTIES,
      (SELECT COUNT(*) FROM PAPERTRAIL.GOLD.DIM_ACCOUNT)        AS ACCOUNTS,
      (SELECT COUNT(*) FROM PAPERTRAIL.GOLD.FACT_ALERT)         AS ALERTS,
      (SELECT COUNT(*) FROM PAPERTRAIL.GOLD.FACT_CASE)          AS CASES,
      (SELECT COUNT(*) FROM PAPERTRAIL.RAW.REGULATORY_DOCUMENT_CLAUSE) AS CLAUSES,
      (SELECT COUNT(*) FROM PAPERTRAIL.RAW.REGULATORY_DOCUMENT) AS DOCUMENTS,
      (SELECT COUNT(*) FROM PAPERTRAIL.GOVERNANCE.FINDINGS)     AS FINDINGS`, [{}]);

  try {
    const dt = await q(`SHOW DYNAMIC TABLES IN DATABASE PAPERTRAIL`);
    out.dynamicTables = dt.map((r) => ({
      SCHEMA: r.schema_name, NAME: r.name, ROWS: r.rows,
      TARGET_LAG: r.target_lag, REFRESH_MODE: r.refresh_mode,
    }));
  } catch (e) { console.error('  ! dynamicTables:', e.message); out.dynamicTables = []; }

  // One real agent exchange, captured at build time so the page opens in a
  // working state rather than an empty shell. Labelled as a saved example in
  // the UI; asking live uses the same agent.
  try {
    const q = 'Which counterparties breach our concentration limit, and what is the limit?';
    const body = JSON.stringify({ messages: [{ role: 'user', content: [{ type: 'text', text: q }] }] });
    const rows = await q2(`SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN('PAPERTRAIL.GOLD.PAPERTRAIL_AGENT', ?) AS R`, [body]);
    out.sampleExchange = { question: q, raw: String(rows[0].R) };
    console.log('  sample exchange captured');
  } catch (e) {
    console.error('  ! sampleExchange:', e.message);
    out.sampleExchange = null;
  }

  fs.writeFileSync(path.join(__dirname, '..', 'data', 'snapshot.json'),
                   JSON.stringify(out, null, 2));
  const n = (k) => Array.isArray(out[k]) ? out[k].length : 0;
  console.log(`snapshot written — experiment:${n('experiment')} findings:${n('findings')} footnotes:${n('footnotes')} dynTables:${n('dynamicTables')}`);
  console.log('counts:', JSON.stringify(out.counts && out.counts[0]));
  conn.destroy(() => process.exit(0));
})().catch((e) => { console.error('FAILED:', e.message); process.exit(1); });
