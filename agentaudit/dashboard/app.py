# app.py
# Streamlit dashboard for AgentAudit.
# Four pages: Overview, Run Details, Trends, Regression.
# Run with: streamlit run agentaudit/dashboard/app.py

import glob
import os
import sqlite3

import pandas as pd
import streamlit as st

from agentaudit.core.storage import (
    get_runs,
    get_run_by_id,
    get_claims,
    DEFAULT_DB_PATH,
)
from agentaudit.core.regression import compare_runs
from agentaudit.dashboard import theme as th
from agentaudit.dashboard.charts import trend_chart

st.set_page_config(
    page_title="AgentAudit",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Page name -> Material Symbol shown in the sidebar nav.
PAGES = {
    "Overview": "space_dashboard",
    "Run Details": "description",
    "Trends": "trending_up",
    "Regression": "compare_arrows",
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def fmt_time(value: str) -> str:
    """ISO timestamp -> 'Jul 27, 14:32'. Falls back to the raw string."""
    try:
        return pd.to_datetime(value).strftime("%b %d, %H:%M")
    except (ValueError, TypeError):
        return str(value)


def hallucination_tone(score) -> str:
    if score is None or pd.isna(score):
        return "neutral"
    return "good" if score < 0.2 else "warning" if score < 0.5 else "critical"


def faithfulness_tone(score) -> str:
    if score is None or pd.isna(score):
        return "neutral"
    return "good" if score >= 0.8 else "warning" if score >= 0.5 else "critical"


# tone, icon name, label, and the glyph shown on the collapsed expander row
# (expander labels take markdown, not HTML, so status needs a text symbol).
CLAIM_STATUS = {
    "SUPPORTED":    ("good", "check", "Supported", "✓"),
    "FAITHFUL":     ("good", "check", "Faithful", "✓"),
    "UNSUPPORTED":  ("critical", "x", "Unsupported", "✕"),
    "CONTRADICTED": ("warning", "alert", "Contradicted", "⚠"),
}


def series_delta(series: pd.Series):
    """Change between the two most recent values, or None."""
    vals = series.dropna().tolist()
    return (vals[-1] - vals[-2]) if len(vals) >= 2 else None


# --------------------------------------------------------------------------- #
# Database discovery — no manual path entry for the common case
# --------------------------------------------------------------------------- #

def _is_agentaudit_db(path: str) -> bool:
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='runs'")
        found = cur.fetchone() is not None
        conn.close()
        return found
    except sqlite3.Error:
        return False


def discover_db_paths() -> list[str]:
    candidates = set(glob.glob("*.db"))
    if os.path.exists(DEFAULT_DB_PATH):
        candidates.add(DEFAULT_DB_PATH)
    return sorted(p for p in candidates if _is_agentaudit_db(p))


def pick_db_path(t: dict) -> str:
    discovered = discover_db_paths()

    if len(discovered) > 1:
        db_path = st.sidebar.selectbox("Database", discovered)
    elif discovered:
        db_path = discovered[0]
    else:
        db_path = DEFAULT_DB_PATH

    # Summarise what's actually in the database so the rail carries real status,
    # not just a filename.
    try:
        runs = get_runs(db_path=db_path)
    except sqlite3.Error:
        runs = []

    if runs:
        pipelines = len({r["pipeline_name"] for r in runs})
        meta = f"{len(runs)} run{'s' * (len(runs) != 1)} · {pipelines} pipeline{'s' * (pipelines != 1)}"
        th.db_chip(t, os.path.basename(db_path), meta, connected=True)
    else:
        th.db_chip(t, os.path.basename(db_path), "no runs recorded", connected=False)

    with st.sidebar.expander("Change database"):
        db_path = st.text_input("Path", value=db_path, label_visibility="collapsed")

    return db_path


def sidebar_latest_run(t: dict, db_path: str) -> None:
    """Latest-run summary — gives the lower rail purpose instead of empty space."""
    try:
        runs = get_runs(db_path=db_path, limit=1)
    except sqlite3.Error:
        return
    if not runs:
        return

    run = runs[0]
    rows = []

    h = run.get("hallucination_score")
    if h is not None:
        accent, _ = th.tone_colors(t, hallucination_tone(h))
        rows.append(("Hallucination", f"{h:.2f}", accent))

    f = run.get("faithfulness_score")
    if f is not None:
        accent, _ = th.tone_colors(t, faithfulness_tone(f))
        rows.append(("Faithfulness", f"{f:.2f}", accent))

    lat = run.get("latency_ms")
    if lat is not None:
        rows.append(("Latency", f"{lat:,.0f} ms", t["ink"]))

    th.last_run_panel(t, run["pipeline_name"], fmt_time(run["timestamp"]), rows)


# --------------------------------------------------------------------------- #
# Page 1 — Overview
# --------------------------------------------------------------------------- #

def show_overview(db_path: str, t: dict) -> None:
    th.page_head(t, "overview", "Overview", "All recent pipeline runs at a glance.")

    runs = get_runs(db_path=db_path)
    if not runs:
        th.empty_state(
            t, "No runs recorded yet",
            "Wrap a pipeline with <code>@audit(name=\"my_pipeline\")</code> and run it — "
            "results land here automatically.",
        )
        return

    df = pd.DataFrame(runs).sort_values("timestamp")

    hall = df["hallucination_score"]
    faith = df["faithfulness_score"]
    cost = df["cost_usd"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        th.stat_card(
            t, "Total runs", f"{len(df):,}", tone="info",
            hint=f"{df['pipeline_name'].nunique()} pipeline(s)",
        )
    with c2:
        th.stat_card(
            t, "Avg hallucination", f"{hall.mean():.2f}" if hall.notna().any() else "—",
            tone=hallucination_tone(hall.mean()), delta=series_delta(hall),
            lower_is_better=True, spark=hall.dropna().tolist(),
        )
    with c3:
        th.stat_card(
            t, "Avg faithfulness", f"{faith.mean():.2f}" if faith.notna().any() else "—",
            tone=faithfulness_tone(faith.mean()), delta=series_delta(faith),
            lower_is_better=False, spark=faith.dropna().tolist(),
        )
    with c4:
        th.stat_card(
            t, "Avg cost", f"${cost.mean():.4f}" if cost.notna().any() else "—",
            tone="info", delta=None, spark=cost.dropna().tolist(),
            hint=f"${cost.sum():.3f} total" if cost.notna().any() else "",
        )

    th.section("Recent runs")

    pipelines = ["All pipelines"] + sorted(df["pipeline_name"].unique().tolist())
    selected = st.selectbox("Filter", pipelines, label_visibility="collapsed")
    if selected != "All pipelines":
        df = df[df["pipeline_name"] == selected]

    table = df.sort_values("timestamp", ascending=False).copy()
    table["timestamp"] = table["timestamp"].map(fmt_time)

    st.dataframe(
        table[[
            "id", "pipeline_name", "timestamp", "hallucination_score",
            "faithfulness_score", "cost_usd", "latency_ms",
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("Run", width="small"),
            "pipeline_name": st.column_config.TextColumn("Pipeline"),
            "timestamp": st.column_config.TextColumn("Time"),
            "hallucination_score": st.column_config.ProgressColumn(
                "Hallucination ↓", min_value=0, max_value=1, format="%.2f",
            ),
            "faithfulness_score": st.column_config.ProgressColumn(
                "Faithfulness ↑", min_value=0, max_value=1, format="%.2f",
            ),
            "cost_usd": st.column_config.NumberColumn("Cost (USD)", format="$%.4f"),
            "latency_ms": st.column_config.NumberColumn("Latency", format="%.0f ms"),
        },
    )


# --------------------------------------------------------------------------- #
# Page 2 — Run Details
# --------------------------------------------------------------------------- #

def show_run_details(db_path: str, t: dict) -> None:
    th.page_head(t, "details", "Run Details", "Drill into a single run and inspect every claim.")

    runs = get_runs(db_path=db_path)
    if not runs:
        th.empty_state(t, "No runs recorded yet", "Run an audited pipeline first.")
        return

    labels = {
        r["id"]: f"#{r['id']}  ·  {r['pipeline_name']}  ·  {fmt_time(r['timestamp'])}"
        for r in runs
    }
    selected_id = st.selectbox(
        "Run", list(labels), format_func=lambda i: labels[i], label_visibility="collapsed",
    )

    run = get_run_by_id(selected_id, db_path=db_path)
    if not run:
        st.error("Run not found.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        h = run["hallucination_score"]
        th.stat_card(t, "Hallucination ↓", f"{h:.2f}" if h is not None else "—",
                     tone=hallucination_tone(h))
    with c2:
        f = run["faithfulness_score"]
        th.stat_card(t, "Faithfulness ↑", f"{f:.2f}" if f is not None else "—",
                     tone=faithfulness_tone(f))
    with c3:
        c = run["cost_usd"]
        cost_label = "~estimated" if run.get("is_cost_estimated") else "exact"
        th.stat_card(t, "Cost", f"${c:.4f}" if c is not None else "—", tone="info",
                     hint=f"₹{run['cost_inr']:.2f} ({cost_label})" if run.get("cost_inr") else cost_label if c is not None else "")
    with c4:
        l = run["latency_ms"]
        th.stat_card(t, "Latency", f"{l:,.0f} ms" if l is not None else "—", tone="info",
                     hint=run.get("model_used") or "")

    th.section("Query, response & context")

    left, right = st.columns(2)
    with left:
        st.markdown(
            f"""
            <div class="aa-field">
                <div class="aa-field-label">Query</div>
                <div class="aa-text" style="--accent:{t['series'][0]};">{run['query'] or '—'}</div>
            </div>
            <div class="aa-field">
                <div class="aa-field-label">Response</div>
                <div class="aa-text" style="--accent:{t['good']};">{run['response'] or '—'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""
            <div class="aa-field">
                <div class="aa-field-label">Retrieved context</div>
                <div class="aa-text" style="--accent:{t['baseline']};max-height:250px;overflow-y:auto;">
                    {run['context'] or '—'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    claims = get_claims(selected_id, db_path=db_path)
    th.section(f"Claims ({len(claims)})")

    if not claims:
        th.empty_state(t, "No claims extracted",
                       "This run has no per-claim breakdown recorded.")
        return

    for claim in claims:
        tone, ico, text, glyph = CLAIM_STATUS.get(
            claim["status"], ("neutral", "help", claim["status"], "?")
        )
        accent, _ = th.tone_colors(t, tone)
        with st.expander(f"{glyph}  {claim['claim']}"):
            st.markdown(
                f"""
                <div style="display:flex;gap:8px;align-items:center;margin-bottom:9px;">
                    {th.badge(t, tone, ico, text)}
                    {th.badge(t, 'neutral', None, claim['metric_type'].title())}
                </div>
                <div class="aa-field-label">Evidence</div>
                <div class="aa-text" style="--accent:{accent};">{claim['evidence'] or 'None recorded'}</div>
                """,
                unsafe_allow_html=True,
            )


# --------------------------------------------------------------------------- #
# Page 3 — Trends
# --------------------------------------------------------------------------- #

def show_trends(db_path: str, t: dict) -> None:
    th.page_head(t, "trends", "Trends", "How your pipeline's scores move over time.")

    runs = get_runs(db_path=db_path)
    if not runs:
        th.empty_state(t, "No runs recorded yet", "Run an audited pipeline first.")
        return

    df = pd.DataFrame(runs)
    pipelines = sorted(df["pipeline_name"].unique().tolist())
    selected = st.selectbox("Pipeline", pipelines, label_visibility="collapsed")
    df = df[df["pipeline_name"] == selected].sort_values("timestamp")

    if len(df) < 2:
        th.empty_state(t, "Not enough history",
                       "At least two runs of this pipeline are needed to plot a trend.")
        return

    specs = [
        ("hallucination_score", "Hallucination score", "lower is better", 0, ".2f", ".2f"),
        ("faithfulness_score",  "Faithfulness score",  "higher is better", 2, ".2f", ".2f"),
        ("cost_usd",            "Cost per run",        "lower is better", 1, "$.4f", "$.3f"),
        ("latency_ms",          "Latency",             "lower is better", 3, ",.0f", ",.0f"),
    ]

    for row_start in (0, 2):
        cols = st.columns(2)
        for col, (field, title, sub, slot, tip_fmt, ax_fmt) in zip(
            cols, specs[row_start:row_start + 2]
        ):
            with col, st.container(border=True):
                st.markdown(
                    f'<div class="aa-panel-title">{title}</div>'
                    f'<div class="aa-panel-sub">{sub}</div>',
                    unsafe_allow_html=True,
                )
                if df[field].notna().any():
                    st.altair_chart(
                        trend_chart(
                            df, field, t["series"][slot], t,
                            value_fmt=tip_fmt, axis_fmt=ax_fmt, value_title=title,
                        ),
                        use_container_width=True,
                    )
                else:
                    st.caption("No data recorded for this metric.")


# --------------------------------------------------------------------------- #
# Page 4 — Regression
# --------------------------------------------------------------------------- #

METRIC_LABELS = {
    "hallucination_score": "Hallucination score",
    "faithfulness_score": "Faithfulness score",
    "cost_usd": "Cost (USD)",
    "latency_ms": "Latency (ms)",
}

DIFF_STATUS = {
    "IMPROVED":  ("good", "up", "Improved"),
    "REGRESSED": ("critical", "down", "Regressed"),
    "STABLE":    ("neutral", "dot", "Stable"),
    "NO_DATA":   ("neutral", "help", "No data"),
}


def show_regression(db_path: str, t: dict) -> None:
    th.page_head(t, "compare", "Regression Testing",
                 "Compare two runs to see what improved and what regressed.")

    runs = get_runs(db_path=db_path)
    if not runs:
        th.empty_state(t, "No runs recorded yet", "Run an audited pipeline first.")
        return

    pipelines = sorted({r["pipeline_name"] for r in runs})
    selected_pipeline = st.selectbox("Pipeline", pipelines, label_visibility="collapsed")

    pipeline_runs = [r for r in runs if r["pipeline_name"] == selected_pipeline]
    if len(pipeline_runs) < 2:
        th.empty_state(t, "Not enough history",
                       "At least two runs of this pipeline are needed to compare.")
        return

    labels = {r["id"]: f"#{r['id']}  ·  {fmt_time(r['timestamp'])}" for r in pipeline_runs}
    ids = list(labels)

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        baseline_id = st.selectbox("Baseline", ids, index=min(1, len(ids) - 1),
                                   format_func=lambda i: labels[i])
    with c2:
        current_id = st.selectbox("Current", ids, index=0, format_func=lambda i: labels[i])
    with c3:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        run_compare = st.button("Compare", type="primary", use_container_width=True)

    if baseline_id == current_id:
        st.info("Pick two different runs to compare.")
        return

    if not run_compare:
        return

    try:
        report = compare_runs(
            pipeline_name=selected_pipeline,
            baseline_run_id=baseline_id,
            current_run_id=current_id,
            db_path=db_path,
        )
    except Exception as e:
        st.error(f"Could not compare runs: {e}")
        return

    tone = "good" if report.passed else "critical"
    accent, fg = th.tone_colors(t, tone)

    # Rebuild the headline with readable metric names — report.summary carries its
    # own emoji and raw field ids, which duplicate the icon we render here.
    if report.passed:
        headline = "No regressions detected"
    else:
        regressed = [
            METRIC_LABELS.get(d.metric, d.metric)
            for d in report.diffs if d.status == "REGRESSED"
        ]
        headline = "Regressions detected in " + ", ".join(regressed)

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;padding:13px 16px;margin-top:6px;
                    border:1px solid {accent}44;background:{accent}14;border-radius:12px;">
            <span style="color:{fg};display:flex;">{th.icon('check' if report.passed else 'alert', 17)}</span>
            <span style="color:{fg};font-weight:600;font-size:14px;">{headline}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    th.section("Metric comparison")

    for diff in report.diffs:
        d_tone, d_icon, d_text = DIFF_STATUS.get(diff.status, ("neutral", "help", diff.status))
        st.markdown(
            f"""
            <div class="aa-diff">
                <span class="aa-diff-name">{METRIC_LABELS.get(diff.metric, diff.metric)}</span>
                <span class="aa-diff-val">baseline <b>{diff.baseline if diff.baseline is not None else '—'}</b></span>
                <span class="aa-diff-arrow">{th.icon('arrow', 14)}</span>
                <span class="aa-diff-val">current <b>{diff.current if diff.current is not None else '—'}</b></span>
                {th.badge(t, d_tone, d_icon, d_text)}
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    t = th.tokens()
    th.inject_css(t)
    th.brand(t)

    db_path = pick_db_path(t)

    st.sidebar.markdown('<div class="aa-nav-label">Navigate</div>', unsafe_allow_html=True)
    page = st.sidebar.radio(
        "Navigate",
        list(PAGES),
        format_func=lambda name: f":material/{PAGES[name]}: {name}",
        label_visibility="collapsed",
    )

    sidebar_latest_run(t, db_path)

    if page == "Overview":
        show_overview(db_path, t)
    elif page == "Run Details":
        show_run_details(db_path, t)
    elif page == "Trends":
        show_trends(db_path, t)
    elif page == "Regression":
        show_regression(db_path, t)

    st.sidebar.markdown(
        f"""
        <div style="margin-top:26px;padding:14px 4px 0 4px;border-top:1px solid {t['border_soft']};
                    font-size:11.5px;color:{t['muted']};">
            Open source · <a href="https://github.com/me-nabi/AiAudit"
            style="color:{t['series'][0]};text-decoration:none;">GitHub ↗</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
