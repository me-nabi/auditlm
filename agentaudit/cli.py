# cli.py
# Three commands: init, dashboard, compare
# Uses Python's built-in argparse — no extra dependencies needed

import argparse
import subprocess
import sys
import os

from agentaudit.core.storage import init_db, DEFAULT_DB_PATH
from agentaudit.core.regression import compare_runs, get_latest_runs

# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_init(args) -> None:
    """Create the SQLite database and tables."""
    db_path = args.db or DEFAULT_DB_PATH
    init_db(db_path=db_path)
    print(f"✅ AgentAudit initialized — database created at: {db_path}")


def cmd_dashboard(args) -> None:
    """Launch the Streamlit dashboard."""
    dashboard_path = os.path.join(
        os.path.dirname(__file__),
        "dashboard",
        "app.py",
    )

    if not os.path.exists(dashboard_path):
        print(f"❌ Dashboard not found at: {dashboard_path}")
        sys.exit(1)

    print("🚀 Launching AgentAudit dashboard at http://localhost:8501")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", dashboard_path
    ])


def cmd_compare(args) -> None:
    """Compare last two runs of a pipeline."""
    pipeline = args.pipeline
    db_path = args.db or DEFAULT_DB_PATH

    try:
        baseline_id, current_id = get_latest_runs(
            pipeline_name=pipeline,
            db_path=db_path,
        )
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    report = compare_runs(
        pipeline_name=pipeline,
        baseline_run_id=baseline_id,
        current_run_id=current_id,
        db_path=db_path,
    )

    print(f"\n📊 Regression Report — {pipeline}")
    print(f"Baseline Run: #{baseline_id}  |  Current Run: #{current_id}")
    print("-" * 60)

    for diff in report.diffs:
        status_icon = {
            "IMPROVED":  "✅",
            "REGRESSED": "❌",
            "STABLE":    "➡️",
            "NO_DATA":   "❓",
        }.get(diff.status, "❓")

        print(
            f"{status_icon} {diff.metric:<25}"
            f"baseline: {str(diff.baseline):<10}"
            f"current: {str(diff.current):<10}"
            f"{diff.status}"
        )

    print("-" * 60)
    print(report.summary)
    print()

    # Exit with error code if regression detected — useful for CI/CD
    if not report.passed:
        sys.exit(1)


# --------------------------------------------------------------------------- #
# Main — wire commands to argparse
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agentaudit",
        description="Open source evaluation toolkit for LLM pipelines and agents.",
    )

    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize AgentAudit database")
    init_parser.add_argument("--db", help="Custom database path", default=None)

    # dashboard
    subparsers.add_parser("dashboard", help="Launch Streamlit dashboard")

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare last two pipeline runs")
    compare_parser.add_argument("--pipeline", required=True, help="Pipeline name to compare")
    compare_parser.add_argument("--db", help="Custom database path", default=None)

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "dashboard":
        cmd_dashboard(args)
    elif args.command == "compare":
        cmd_compare(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()