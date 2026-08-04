# app.py
# Streamlit dashboard for AgentAudit.
# Four pages: Overview, Run Details, Trends, Regression.
# Run with: streamlit run agentaudit/dashboard/app.py

import streamlit as st
import pandas as pd

from agentaudit.core.storage import (
    get_runs,
    get_run_by_id,
    get_claims,
    DEFAULT_DB_PATH,
)

st.set_page_config(
    page_title="AgentAudit",
    page_icon="🔍",
    layout="wide",
)

# --------------------------------------------------------------------------- #
# Page 1 — Overview
# --------------------------------------------------------------------------- #

def show_overview(db_path: str) -> None:
    st.title("🔍 AgentAudit — Overview")
    st.caption("All recent pipeline runs at a glance.")

    runs = get_runs(db_path=db_path)

    if not runs:
        st.warning("No runs found. Wrap your pipeline with @audit and run it first.")
        return

    df = pd.DataFrame(runs)

    # Show summary metrics at the top
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        label="Total Runs",
        value=len(df),
    )
    col2.metric(
        label="Avg Hallucination Score",
        value=f"{df['hallucination_score'].mean():.2f}" 
              if "hallucination_score" in df else "N/A",
    )
    col3.metric(
        label="Avg Faithfulness Score",
        value=f"{df['faithfulness_score'].mean():.2f}"
              if "faithfulness_score" in df else "N/A",
    )
    col4.metric(
        label="Avg Cost (USD)",
        value=f"${df['cost_usd'].mean():.4f}"
              if "cost_usd" in df else "N/A",
    )

    st.divider()

    # Pipeline filter
    pipelines = ["All"] + sorted(df["pipeline_name"].unique().tolist())
    selected = st.selectbox("Filter by pipeline", pipelines)

    if selected != "All":
        df = df[df["pipeline_name"] == selected]

    # Show table
    st.dataframe(
        df[[
            "id", "pipeline_name", "timestamp",
            "hallucination_score", "faithfulness_score",
            "cost_usd", "cost_inr", "latency_ms",
        ]].rename(columns={
            "id": "Run ID",
            "pipeline_name": "Pipeline",
            "timestamp": "Time",
            "hallucination_score": "Hallucination ↓",
            "faithfulness_score": "Faithfulness ↑",
            "cost_usd": "Cost (USD)",
            "cost_inr": "Cost (INR)",
            "latency_ms": "Latency (ms)",
        }),
        use_container_width=True,
        hide_index=True,
    )
    

# --------------------------------------------------------------------------- #
# Page 2 — Run Details
# --------------------------------------------------------------------------- #

def show_run_details(db_path: str) -> None:
    st.title("🔎 Run Details")
    st.caption("Drill into a specific run and see every claim.")

    runs = get_runs(db_path=db_path)
    if not runs:
        st.warning("No runs found.")
        return

    run_ids = [r["id"] for r in runs]
    selected_id = st.selectbox("Select Run ID", run_ids)

    run = get_run_by_id(selected_id, db_path=db_path)
    if not run:
        st.error("Run not found.")
        return

    # --- Run summary ---
    st.subheader(f"Pipeline: {run['pipeline_name']}")
    st.caption(f"Timestamp: {run['timestamp']}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Hallucination ↓", 
                f"{run['hallucination_score']:.2f}" 
                if run['hallucination_score'] is not None else "N/A")
    col2.metric("Faithfulness ↑", 
                f"{run['faithfulness_score']:.2f}" 
                if run['faithfulness_score'] is not None else "N/A")
    col3.metric("Cost (USD)", 
                f"${run['cost_usd']:.4f}" 
                if run['cost_usd'] is not None else "N/A")
    col4.metric("Latency (ms)", 
                f"{run['latency_ms']:.0f}" 
                if run['latency_ms'] is not None else "N/A")

    st.divider()

    # --- Query, Response, Context ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Query**")
        st.info(run["query"] or "N/A")

        st.markdown("**Response**")
        st.success(run["response"] or "N/A")

    with col_right:
        st.markdown("**Context**")
        st.text_area(
            label="context",
            value=run["context"] or "N/A",
            height=200,
            label_visibility="collapsed",
        )

    st.divider()

    # --- Claims ---
    st.subheader("Claims")

    claims = get_claims(selected_id, db_path=db_path)
    if not claims:
        st.info("No claims found for this run.")
        return

    for claim in claims:
        status = claim["status"]

        if status in ("SUPPORTED", "FAITHFUL"):
            icon = "✅"
            color = "success"
        elif status == "UNSUPPORTED":
            icon = "❌"
            color = "error"
        elif status == "CONTRADICTED":
            icon = "⚠️"
            color = "warning"
        else:
            icon = "❓"
            color = "info"

        with st.expander(f"{icon} [{claim['metric_type'].upper()}] {claim['claim']}"):
            st.markdown(f"**Status:** {status}")
            st.markdown(f"**Evidence:** {claim['evidence'] or 'None'}")
            
            
# --------------------------------------------------------------------------- #
# Page 3 — Trends
# --------------------------------------------------------------------------- #

def show_trends(db_path: str) -> None:
    st.title("📈 Trends")
    st.caption("See how your pipeline scores change over time.")

    runs = get_runs(db_path=db_path)
    if not runs:
        st.warning("No runs found.")
        return

    df = pd.DataFrame(runs)

    # Pipeline filter
    pipelines = sorted(df["pipeline_name"].unique().tolist())
    selected = st.selectbox("Select pipeline", pipelines)
    df = df[df["pipeline_name"] == selected].sort_values("timestamp")

    if len(df) < 2:
        st.info("Need at least 2 runs to show trends.")
        return

    st.divider()

    # --- Charts ---
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Hallucination Score over time** ↓ lower is better")
        if df["hallucination_score"].notna().any():
            st.line_chart(
                df.set_index("timestamp")["hallucination_score"],
                use_container_width=True,
            )
        else:
            st.info("No hallucination data yet.")

    with col2:
        st.markdown("**Faithfulness Score over time** ↑ higher is better")
        if df["faithfulness_score"].notna().any():
            st.line_chart(
                df.set_index("timestamp")["faithfulness_score"],
                use_container_width=True,
            )
        else:
            st.info("No faithfulness data yet.")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**Cost (USD) over time** ↓ lower is better")
        if df["cost_usd"].notna().any():
            st.line_chart(
                df.set_index("timestamp")["cost_usd"],
                use_container_width=True,
            )
        else:
            st.info("No cost data yet.")

    with col4:
        st.markdown("**Latency (ms) over time** ↓ lower is better")
        if df["latency_ms"].notna().any():
            st.line_chart(
                df.set_index("timestamp")["latency_ms"],
                use_container_width=True,
            )
        else:
            st.info("No latency data yet.")
            
# --------------------------------------------------------------------------- #
# Page 4 — Regression
# --------------------------------------------------------------------------- #

def show_regression(db_path: str) -> None:
    st.title("🔁 Regression Testing")
    st.caption("Compare two runs to see what improved and what regressed.")

    runs = get_runs(db_path=db_path)
    if not runs:
        st.warning("No runs found.")
        return

    pipelines = sorted(set(r["pipeline_name"] for r in runs))
    selected_pipeline = st.selectbox("Select pipeline", pipelines)

    pipeline_runs = [r for r in runs if r["pipeline_name"] == selected_pipeline]

    if len(pipeline_runs) < 2:
        st.info("Need at least 2 runs to compare.")
        return

    run_ids = [r["id"] for r in pipeline_runs]

    col1, col2 = st.columns(2)
    with col1:
        baseline_id = st.selectbox("Baseline Run ID", run_ids, index=len(run_ids)-2)
    with col2:
        current_id = st.selectbox("Current Run ID", run_ids, index=len(run_ids)-1)

    if baseline_id == current_id:
        st.warning("Select two different runs to compare.")
        return

    if st.button("Compare Runs"):
        try:
            report = compare_runs(
                pipeline_name=selected_pipeline,
                baseline_run_id=baseline_id,
                current_run_id=current_id,
                db_path=db_path,
            )
        except Exception as e:
            st.error(f"Error comparing runs: {e}")
            return

        # Summary
        if report.passed:
            st.success(report.summary)
        else:
            st.error(report.summary)

        st.divider()

        # Diff table
        st.subheader("Metric Comparison")

        for diff in report.diffs:
            col1, col2, col3, col4 = st.columns(4)

            col1.markdown(f"**{diff.metric}**")
            col2.markdown(f"Baseline: `{diff.baseline}`")
            col3.markdown(f"Current: `{diff.current}`")

            if diff.status == "IMPROVED":
                col4.success("✅ IMPROVED")
            elif diff.status == "REGRESSED":
                col4.error("❌ REGRESSED")
            elif diff.status == "STABLE":
                col4.info("➡️ STABLE")
            else:
                col4.warning("❓ NO DATA")
                
# --------------------------------------------------------------------------- #
# Main — sidebar navigation
# --------------------------------------------------------------------------- #

def main() -> None:
    st.sidebar.title("🔍 AgentAudit")
    st.sidebar.caption("v0.1.0 — open source LLM eval toolkit")

    db_path = st.sidebar.text_input(
        "Database path",
        value=DEFAULT_DB_PATH,
    )

    st.sidebar.divider()

    page = st.sidebar.radio(
        "Navigate",
        ["Overview", "Run Details", "Trends", "Regression"],
    )

    if page == "Overview":
        show_overview(db_path=db_path)
    elif page == "Run Details":
        show_run_details(db_path=db_path)
    elif page == "Trends":
        show_trends(db_path=db_path)
    elif page == "Regression":
        show_regression(db_path=db_path)

    st.sidebar.divider()
    st.sidebar.markdown(
        "Built with ❤️ — "
        "[GitHub](https://github.com/yourusername/agentaudit)"
    )


if __name__ == "__main__":
    main()