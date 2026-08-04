# latency.py
# Measures and evaluates latency of LLM pipeline steps.
# No LLM calls — pure time measurement.

import time
from dataclasses import dataclass
from typing import Optional


# --------------------------------------------------------------------------- #
# Data Structure
# --------------------------------------------------------------------------- #

@dataclass
class LatencyResult:
    step_name: str
    latency_ms: float
    threshold_ms: float
    is_slow: bool
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def measure_latency(
    step_name: str,
    threshold_ms: float = 3000.0,
) -> "LatencyTracker":
    """
    Context manager to measure latency of any code block.

    Usage:
        with measure_latency("retrieval_step") as tracker:
            results = retriever.get(query)
        
        print(tracker.result.latency_ms)
    """
    return LatencyTracker(step_name=step_name, threshold_ms=threshold_ms)


class LatencyTracker:
    """
    Context manager that times a block of code and returns a LatencyResult.
    """

    def __init__(self, step_name: str, threshold_ms: float):
        self.step_name = step_name
        self.threshold_ms = threshold_ms
        self.result: Optional[LatencyResult] = None

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency_ms = (time.perf_counter() - self._t0) * 1000

        self.result = LatencyResult(
            step_name=self.step_name,
            latency_ms=round(latency_ms, 2),
            threshold_ms=self.threshold_ms,
            is_slow=latency_ms > self.threshold_ms,
            error=str(exc_val) if exc_val else None,
        )

        # Return False so exceptions still propagate normally
        return False