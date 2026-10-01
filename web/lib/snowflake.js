import fs from 'node:fs';
import sdk from 'snowflake-sdk';

sdk.configure({ logLevel: 'ERROR' });

function readToken() {
  if (process.env.SNOWFLAKE_PAT) return process.env.SNOWFLAKE_PAT.trim();
  // local development fallback
  const p = `${process.env.HOME}/.snowflake/manoj_pat.txt`;
  if (fs.existsSync(p)) return fs.readFileSync(p, 'utf8').trim();
  throw new Error('No Snowflake credential: set SNOWFLAKE_PAT');
}

export function connect() {
  return new Promise((resolve, reject) => {
    const conn = sdk.createConnection({
      account: process.env.SNOWFLAKE_ACCOUNT || 'xd71507.ap-southeast-7.aws',
      username: process.env.SNOWFLAKE_USER || 'TJMANOJ',
      authenticator: 'PROGRAMMATIC_ACCESS_TOKEN',
      token: readToken(),
      role: 'ACCOUNTADMIN',
      warehouse: 'PAPERTRAIL_WH',
      database: 'PAPERTRAIL',
      clientSessionKeepAlive: false,
    });
    conn.connect((err) => (err ? reject(err) : resolve(conn)));
  });
}

export function run(conn, sqlText, binds) {
  return new Promise((resolve, reject) => {
    conn.execute({
      sqlText,
      binds,
      complete: (err, _stmt, rows) => (err ? reject(err) : resolve(rows)),
    });
  });
}

/** Opens a connection, runs fn, always tears the connection down. */
export async function withSnowflake(fn) {
  const conn = await connect();
  try {
    return await fn((sql, binds) => run(conn, sql, binds));
  } finally {
    try { conn.destroy(() => {}); } catch { /* already gone */ }
  }
}
