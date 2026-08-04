
# regression.py
# Regression testing suite for LLM pipelines.
# Compare current pipeline performance against a saved baseline.

from dataclasses import dataclass, field
from typing import Optional

from agentaudit.core.storage import get_runs, DEFAULT_DB_PATH


@dataclass
class MetricDiff:
    metric: str
    baseline: Optional[float]
    current: Optional[float]
    change: Optional[float]
    status: str          # "IMPROVED" | "REGRESSED" | "STABLE" | "NO_DATA"


@dataclass
class RegressionReport:
    pipeline_name: str
    baseline_run_id: int
    current_run_id: int
    diffs: list[MetricDiff] = field(default_factory=list)
    passed: bool = True
    summary: str = ""
    
# --------------------------------------------------------------------------- #
# Core Comparison Logic
# --------------------------------------------------------------------------- #

def _compare_metric(
    metric: str,
    baseline_value: Optional[float],
    current_value: Optional[float],
    higher_is_better: bool = False,
    tolerance: float = 0.05,
) -> MetricDiff:
    """
    Compare one metric between baseline and current run.

    tolerance: how much change is acceptable before flagging.
               default 0.05 = 5% change is fine, beyond that is regression.
    higher_is_better: True for faithfulness (higher = better)
                      False for hallucination, cost, latency (lower = better)
    """

    if baseline_value is None or current_value is None:
        return MetricDiff(
            metric=metric,
            baseline=baseline_value,
            current=current_value,
            change=None,
            status="NO_DATA",
        )

    change = current_value - baseline_value

    if higher_is_better:
        # faithfulness — going down is bad
        if change < -tolerance:
            status = "REGRESSED"
        elif change > tolerance:
            status = "IMPROVED"
        else:
            status = "STABLE"
    else:
        # hallucination, cost, latency — going up is bad
        if change > tolerance:
            status = "REGRESSED"
        elif change < -tolerance:
            status = "IMPROVED"
        else:
            status = "STABLE"

    return MetricDiff(
        metric=metric,
        baseline=round(baseline_value, 4),
        current=round(current_value, 4),
        change=round(change, 4),
        status=status,
    )
    
# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def compare_runs(
    pipeline_name: str,
    baseline_run_id: int,
    current_run_id: int,
    tolerance: float = 0.05,
    db_path: str = DEFAULT_DB_PATH,
) -> RegressionReport:
    """
    Compare two runs of the same pipeline.
    Returns a RegressionReport showing what improved and what regressed.

    Usage:
        report = compare_runs(
            pipeline_name="my_pipeline",
            baseline_run_id=1,
            current_run_id=2,
        )
        print(report.passed)
        print(report.summary)
    """

    # Fetch both runs from database
    runs = get_runs(pipeline_name=pipeline_name, db_path=db_path)
    run_map = {r["id"]: r for r in runs}

    if baseline_run_id not in run_map:
        raise ValueError(f"Baseline run {baseline_run_id} not found")

    if current_run_id not in run_map:
        raise ValueError(f"Current run {current_run_id} not found")

    baseline = run_map[baseline_run_id]
    current  = run_map[current_run_id]

    # Compare each metric
    diffs = [
        _compare_metric(
            metric="hallucination_score",
            baseline_value=baseline.get("hallucination_score"),
            current_value=current.get("hallucination_score"),
            higher_is_better=False,
            tolerance=tolerance,
        ),
        _compare_metric(
            metric="faithfulness_score",
            baseline_value=baseline.get("faithfulness_score"),
            current_value=current.get("faithfulness_score"),
            higher_is_better=True,
            tolerance=tolerance,
        ),
        _compare_metric(
            metric="cost_usd",
            baseline_value=baseline.get("cost_usd"),
            current_value=current.get("cost_usd"),
            higher_is_better=False,
            tolerance=tolerance,
        ),
        _compare_metric(
            metric="latency_ms",
            baseline_value=baseline.get("latency_ms"),
            current_value=current.get("latency_ms"),
            higher_is_better=False,
            tolerance=tolerance,
        ),
    ]

    # Did anything regress?
    regressions = [d for d in diffs if d.status == "REGRESSED"]
    passed = len(regressions) == 0

    # Build summary
    if passed:
        summary = "✅ No regressions detected."
    else:
        regressed_metrics = ", ".join(d.metric for d in regressions)
        summary = f"❌ Regressions detected in: {regressed_metrics}"

    return RegressionReport(
        pipeline_name=pipeline_name,
        baseline_run_id=baseline_run_id,
        current_run_id=current_run_id,
        diffs=diffs,
        passed=passed,
        summary=summary,
    )


def get_latest_runs(
    pipeline_name: str,
    n: int = 2,
    db_path: str = DEFAULT_DB_PATH,
) -> list[int]:
    """
    Get the IDs of the last n runs for a pipeline.
    Useful for quickly comparing the last two runs.

    Usage:
        baseline_id, current_id = get_latest_runs("my_pipeline")
        report = compare_runs("my_pipeline", baseline_id, current_id)
    """
    runs = get_runs(pipeline_name=pipeline_name, limit=n, db_path=db_path)
    if len(runs) < 2:
        raise ValueError(
            f"Need at least 2 runs to compare. "
            f"Found {len(runs)} for pipeline '{pipeline_name}'"
        )
    # get_runs returns newest first — reverse to get oldest first
    return [r["id"] for r in reversed(runs)]