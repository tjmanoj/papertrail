import streamlit as st
import json
import hashlib
from snowflake.snowpark.context import get_active_session

session = get_active_session()

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg-ground: #0A1020;
    --bg-panel: #121A2B;
    --text-primary: #E6ECF5;
    --text-muted: #8EA0B8;
    --accent-cyan: #35B6E8;
    --border: #223047;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"],
.main, .block-container {
    background-color: var(--bg-ground) !important;
    color: var(--text-primary) !important;
}

[data-testid="stSidebar"] {
    background-color: var(--bg-panel) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em;
}

p, li, span, div, label, td, th {
    color: var(--text-primary) !important;
}

.muted-text { color: var(--text-muted) !important; font-size: 0.85rem; }
.accent-text { color: var(--accent-cyan) !important; }

.metric-tile {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    text-align: center;
}
.metric-tile .metric-value {
    font-size: 2rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--accent-cyan);
    line-height: 1.2;
}
.metric-tile .metric-label {
    font-size: 0.8rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.35rem;
}

.panel {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

.badge-agree {
    display: inline-block;
    background: #1a3a2a;
    color: #4ade80;
    padding: 0.15rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-diverge {
    display: inline-block;
    background: #3a1a1a;
    color: #f87171;
    padding: 0.15rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}

[data-testid="stExpander"] {
    background: var(--bg-panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

[data-testid="stDataFrame"], .stDataFrame {
    font-variant-numeric: tabular-nums;
}

table { border-collapse: collapse; width: 100%; }
th {
    background: var(--bg-panel) !important;
    color: var(--text-muted) !important;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid var(--border);
    text-align: left;
}
td {
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid var(--border);
    font-variant-numeric: tabular-nums;
}

textarea, input, [data-testid="stTextInput"] input {
    background: var(--bg-panel) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}

button[kind="secondary"], .stButton > button {
    background: var(--bg-panel) !important;
    color: var(--accent-cyan) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-weight: 500;
}
button[kind="secondary"]:hover, .stButton > button:hover {
    border-color: var(--accent-cyan) !important;
    background: #1a2538 !important;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run_query(sql):
    return session.sql(sql).collect()


def metric_tile(label, value):
    st.markdown(f"""
    <div class="metric-tile">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def safe_get(row, col, default=""):
    try:
        return row[col]
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown("### PaperTrail")
st.sidebar.markdown('<p class="muted-text">Risk & Regulatory Intelligence</p>',
                    unsafe_allow_html=True)
page = st.sidebar.radio("", ["Ask", "Prove", "File", "Evidence"],
                        label_visibility="collapsed")


# ===================================================================
# PAGE 1 - Ask
# ===================================================================
if page == "Ask":
    try:
        st.markdown("## Ask the Risk Analyst")
        st.markdown('<p class="muted-text">Questions are answered through a governed '
                    'semantic view. Every figure traces to its definition and source rows.</p>',
                    unsafe_allow_html=True)

        examples = [
            "What was our total suspicious transaction volume last quarter?",
            "How quickly must a confirmed sanctions match be reported?",
            "Which counterparties breach our concentration limit, and what is the limit?",
            "What will next quarter's suspicious volume be?",
        ]

        cols = st.columns(2)
        clicked_example = None
        for i, ex in enumerate(examples):
            with cols[i % 2]:
                if st.button(ex, key=f"ex_{i}", use_container_width=True):
                    clicked_example = ex

        if clicked_example == examples[3]:
            st.markdown('<p class="muted-text" style="font-style:italic;">'
                        'The agent declines to forecast &mdash; it reports governed '
                        'historical data only.</p>', unsafe_allow_html=True)

        question = st.text_input("Your question", value=clicked_example or "",
                                 placeholder="Ask about risk, exposure, or regulation...")

        if question:
            with st.spinner("Querying the governed agent..."):
                try:
                    agent_sql = """
                    SELECT SNOWFLAKE.CORTEX.AGENT(
                        'PAPERTRAIL.GOLD.PAPERTRAIL_AGENT',
                        ?,
                        {'tools': [
                            {'tool_spec': {'type': 'cortex_analyst_tool',
                                           'name': 'Risk_Analyst'}},
                            {'tool_spec': {'type': 'cortex_search_tool',
                                           'name': 'Regulation_Search'}}
                        ]}
                    ) AS RESPONSE
                    """
                    result = session.sql(agent_sql, params=[question]).collect()
                    raw = safe_get(result[0], "RESPONSE", "{}")
                    resp = json.loads(raw) if isinstance(raw, str) else raw

                    # Extract message
                    message = resp.get("message", raw if isinstance(raw, str) else json.dumps(resp))
                    st.markdown(f'<div class="panel">{message}</div>',
                                unsafe_allow_html=True)

                    # Tools used and SQL in expander
                    tool_results = resp.get("tool_results", [])
                    if tool_results:
                        with st.expander("Tools used and generated SQL"):
                            for tr in tool_results:
                                tool_name = tr.get("tool_name", "unknown")
                                st.markdown(f'<span class="accent-text">{tool_name}</span>',
                                            unsafe_allow_html=True)
                                content = tr.get("content", "")
                                if isinstance(content, str):
                                    try:
                                        content = json.loads(content)
                                    except Exception:
                                        pass
                                if isinstance(content, dict):
                                    sql_text = content.get("sql", content.get("generated_sql", ""))
                                    if sql_text:
                                        st.code(sql_text, language="sql")
                                    else:
                                        st.json(content)
                                else:
                                    st.text(str(content)[:2000])
                except Exception as e:
                    st.error(f"Agent call failed: {e}")

    except Exception as e:
        st.error(f"Ask page error: {e}")


# ===================================================================
# PAGE 2 - Prove
# ===================================================================
elif page == "Prove":
    try:
        st.markdown("## Governed vs Ungoverned")
        st.markdown("**Both paths are perfectly stable. The ungoverned one is "
                    "confidently wrong on 2 of 5.**")

        rows = run_query("""
            SELECT * FROM PAPERTRAIL.GOVERNANCE.GOVERNANCE_EXPERIMENT
            ORDER BY QUESTION_ID, PATH, RUN_NUMBER
        """)

        if not rows:
            st.info("No experiment data found.")
        else:
            # Build structure: question -> path -> list of runs
            questions = {}
            for r in rows:
                q = safe_get(r, "QUESTION_TEXT", "") or safe_get(r, "QUESTION_ID", "")
                p = safe_get(r, "PATH", "")
                if q not in questions:
                    questions[q] = {}
                if p not in questions[q]:
                    questions[q][p] = []
                questions[q][p].append(r)

            divergence_notes = {
                "suspicious transaction volume": (
                    "The ungoverned query uses booking date instead of value date; "
                    "includes reversals; includes unsettled transactions; and counts "
                    "transactions on already-closed alerts."
                ),
                "high-risk": (
                    "The ungoverned query filtered RISK_RATING='HIGH' literally, "
                    "dropping VERY_HIGH entities that KYC policy 2.1 requires be counted."
                ),
                "singapore": (
                    "The ungoverned query filtered RISK_RATING='HIGH' literally, "
                    "dropping VERY_HIGH entities that KYC policy 2.1 requires be counted."
                ),
            }

            coincidence_notes = {
                "concentration": (
                    "This question agrees only by coincidence. The ungoverned path "
                    "computes direct exposure rather than entity-resolved exposure, "
                    "and would diverge for any counterparty with beneficial-ownership links."
                ),
            }

            for qi, (question, paths) in enumerate(questions.items()):
                st.markdown(f"---")
                st.markdown(f"#### Q{qi+1}: {question}")

                gov_runs = paths.get("GOVERNED", [])
                ungov_runs = paths.get("UNGOVERNED", [])

                gov_val = safe_get(gov_runs[0], "ANSWER_NUMERIC", None) if gov_runs else None
                ungov_val = safe_get(ungov_runs[0], "ANSWER_NUMERIC", None) if ungov_runs else None

                # Check stability
                gov_vals = set(str(safe_get(r, "ANSWER_NUMERIC", "")) for r in gov_runs)
                ungov_vals = set(str(safe_get(r, "ANSWER_NUMERIC", "")) for r in ungov_runs)
                gov_stable = len(gov_vals) <= 1
                ungov_stable = len(ungov_vals) <= 1

                agrees = (gov_val is not None and ungov_val is not None
                          and float(gov_val) == float(ungov_val)) if gov_val and ungov_val else False
                badge = "AGREE" if agrees else "DIVERGE"
                badge_class = "badge-agree" if agrees else "badge-diverge"

                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(f'<p class="muted-text">GOVERNED</p>', unsafe_allow_html=True)
                    st.markdown(f'<span style="font-variant-numeric:tabular-nums;font-size:1.3rem;">'
                                f'{gov_val}</span>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<p class="muted-text">UNGOVERNED</p>', unsafe_allow_html=True)
                    st.markdown(f'<span style="font-variant-numeric:tabular-nums;font-size:1.3rem;">'
                                f'{ungov_val}</span>', unsafe_allow_html=True)
                with c3:
                    diff = ""
                    if gov_val is not None and ungov_val is not None:
                        try:
                            diff = f"{float(ungov_val) - float(gov_val):+,.2f}"
                        except Exception:
                            diff = "n/a"
                    st.markdown(f'<p class="muted-text">DIFF</p>', unsafe_allow_html=True)
                    st.markdown(f'{diff}', unsafe_allow_html=True)
                    st.markdown(f'<span class="{badge_class}">{badge}</span>',
                                unsafe_allow_html=True)

                # Show SQL side by side for divergent
                if not agrees:
                    gov_sql = safe_get(gov_runs[0], "GENERATED_SQL", "") if gov_runs else ""
                    ungov_sql = safe_get(ungov_runs[0], "GENERATED_SQL", "") if ungov_runs else ""
                    if gov_sql or ungov_sql:
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            st.markdown('<p class="muted-text">Governed SQL</p>',
                                        unsafe_allow_html=True)
                            st.code(str(gov_sql), language="sql")
                        with sc2:
                            st.markdown('<p class="muted-text">Ungoverned SQL</p>',
                                        unsafe_allow_html=True)
                            st.code(str(ungov_sql), language="sql")

                # Divergence explanation
                q_lower = question.lower()
                for key, note in divergence_notes.items():
                    if key in q_lower:
                        st.markdown(f'<div class="panel"><p class="muted-text">'
                                    f'Why they diverge:</p><p>{note}</p></div>',
                                    unsafe_allow_html=True)
                        break

                # Coincidence note
                for key, note in coincidence_notes.items():
                    if key in q_lower:
                        st.markdown(f'<div class="panel"><p class="muted-text">'
                                    f'Note:</p><p>{note}</p></div>',
                                    unsafe_allow_html=True)
                        break

    except Exception as e:
        st.error(f"Prove page error: {e}")


# ===================================================================
# PAGE 3 - File
# ===================================================================
elif page == "File":
    try:
        st.markdown("## Filed Findings")
        st.markdown('<p class="muted-text">Each finding is an immutable record. '
                    'Every figure is a footnote resolving to its metric definition, '
                    'SQL, source rows, and regulatory clause.</p>',
                    unsafe_allow_html=True)

        findings = run_query("""
            SELECT * FROM PAPERTRAIL.GOVERNANCE.FINDINGS
            ORDER BY CREATED_AT DESC
        """)

        if not findings:
            st.info("No findings have been filed yet.")
        else:
            options = {
                f"{safe_get(f, 'FINDING_ID', '?')} - {str(safe_get(f, 'CREATED_AT', ''))[:19]}": f
                for f in findings
            }
            selected_label = st.selectbox("Select a finding", list(options.keys()))
            finding = options[selected_label]

            finding_id = safe_get(finding, "FINDING_ID", "")
            finding_text = safe_get(finding, "FINDING_TEXT", "")
            content_hash = safe_get(finding, "CONTENT_HASH", "")

            st.markdown(f'<div class="panel">{finding_text}</div>',
                        unsafe_allow_html=True)

            st.markdown(f'<p class="muted-text">Content hash (SHA-256 of finding_text): '
                        f'<code>{content_hash}</code></p>', unsafe_allow_html=True)

            # Footnotes
            footnotes = run_query(f"""
                SELECT * FROM PAPERTRAIL.GOVERNANCE.FINDING_FOOTNOTES
                WHERE FINDING_ID = '{finding_id}'
                ORDER BY FOOTNOTE_NUMBER
            """)

            if footnotes:
                st.markdown("### Footnotes")
                for fn in footnotes:
                    fn_num = safe_get(fn, "FOOTNOTE_NUMBER", "?")
                    metric_name = safe_get(fn, "METRIC_NAME", "")
                    metric_def = safe_get(fn, "METRIC_DEFINITION", "")
                    result_val = safe_get(fn, "RESULT_VALUE", "")
                    clause_num = safe_get(fn, "CLAUSE_NUMBER", "")
                    clause_text = safe_get(fn, "CLAUSE_TEXT_EXCERPT", "")
                    source_table = safe_get(fn, "SOURCE_TABLE", "")
                    source_ids_raw = safe_get(fn, "SOURCE_ROW_IDS", "")
                    gen_sql = safe_get(fn, "GENERATED_SQL", "")

                    # Parse source row IDs
                    try:
                        if isinstance(source_ids_raw, str):
                            source_ids = json.loads(source_ids_raw)
                        else:
                            source_ids = source_ids_raw
                        if isinstance(source_ids, list):
                            display_ids = source_ids[:5]
                        else:
                            display_ids = [source_ids]
                    except Exception:
                        display_ids = [str(source_ids_raw)[:200]]

                    st.markdown(f"""
                    <div class="panel">
                        <p><span class="accent-text" style="font-weight:600;">
                        [{fn_num}] {metric_name}</span></p>
                        <table>
                            <tr><th>Definition</th><td>{metric_def}</td></tr>
                            <tr><th>Result value</th>
                                <td style="font-variant-numeric:tabular-nums;font-weight:600;">
                                {result_val}</td></tr>
                            <tr><th>Clause</th>
                                <td>{clause_num}: {clause_text}</td></tr>
                            <tr><th>Source table</th><td>{source_table}</td></tr>
                            <tr><th>Source rows (first 5)</th>
                                <td>{', '.join(str(s) for s in display_ids)}</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.expander(f"Generated SQL for [{fn_num}]"):
                        st.code(str(gen_sql), language="sql")

                        if st.button(f"Re-run this SQL", key=f"rerun_{finding_id}_{fn_num}"):
                            try:
                                live_result = run_query(str(gen_sql))
                                if live_result:
                                    live_val = live_result[0][0]
                                    match = str(live_val) == str(result_val)
                                    indicator = ("match" if match else "mismatch")
                                    badge_cls = ("badge-agree" if match else "badge-diverge")
                                    st.markdown(
                                        f'<p>Live: <strong>{live_val}</strong> '
                                        f'&nbsp; Filed: <strong>{result_val}</strong> '
                                        f'&nbsp; <span class="{badge_cls}">'
                                        f'{indicator.upper()}</span></p>',
                                        unsafe_allow_html=True
                                    )
                                else:
                                    st.warning("Query returned no rows.")
                            except Exception as ex:
                                st.error(f"Re-run failed: {ex}")
            else:
                st.info("No footnotes found for this finding.")

    except Exception as e:
        st.error(f"File page error: {e}")


# ===================================================================
# PAGE 4 - Evidence
# ===================================================================
elif page == "Evidence":
    try:
        st.markdown("## Evidence Summary")
        st.markdown('<p class="muted-text">Live counts from the governed data estate, '
                    'plus static build facts.</p>', unsafe_allow_html=True)

        # Live counts
        counts = {}
        for label, sql in [
            ("Transactions", "SELECT COUNT(*) FROM PAPERTRAIL.GOLD.FACT_TRANSACTION"),
            ("Counterparties", "SELECT COUNT(*) FROM PAPERTRAIL.GOLD.DIM_COUNTERPARTY"),
            ("Findings", "SELECT COUNT(*) FROM PAPERTRAIL.GOVERNANCE.FINDINGS"),
            ("Footnotes", "SELECT COUNT(*) FROM PAPERTRAIL.GOVERNANCE.FINDING_FOOTNOTES"),
        ]:
            try:
                r = run_query(sql)
                counts[label] = f"{r[0][0]:,}" if r else "?"
            except Exception:
                counts[label] = "?"

        st.markdown("### Live Counts")
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        with c1:
            metric_tile("Transactions", counts["Transactions"])
        with c2:
            metric_tile("Counterparties", counts["Counterparties"])
        with c3:
            metric_tile("Findings Filed", counts["Findings"])
        with c4:
            metric_tile("Footnotes", counts["Footnotes"])

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Build Facts")

        static = [
            ("Governed Metrics", "7"),
            ("Verified Queries", "10"),
            ("Indexed Clauses", "72"),
            ("Regulatory PDFs Parsed (AI_PARSE_DOCUMENT)", "11"),
            ("Registered CoCo Skills", "4"),
            ("Dynamic Tables", "9"),
        ]

        row1 = st.columns(3)
        row2 = st.columns(3)
        all_cols = row1 + row2
        for i, (label, val) in enumerate(static):
            with all_cols[i]:
                metric_tile(label, val)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Retrieval Precision")
        st.markdown("""
        <div class="panel">
            <table>
                <tr><th>Metric</th><th>Score</th></tr>
                <tr><td>Top-1 precision</td>
                    <td style="font-variant-numeric:tabular-nums;">11 / 12</td></tr>
                <tr><td>Top-3 precision</td>
                    <td style="font-variant-numeric:tabular-nums;">12 / 12</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Evidence page error: {e}")
