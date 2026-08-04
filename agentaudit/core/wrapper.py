# wrapper.py
# Decorator and context manager for wrapping LLM pipelines and agents.
# Plug into existing code with minimal change.

import time
import functools
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

from agentaudit.metrics.hallucination import detect_hallucination
from agentaudit.metrics.faithfulness import detect_faithfulness
from agentaudit.metrics.cost import calculate_cost
from agentaudit.metrics.latency import LatencyResult
from agentaudit.core.storage import save_run, init_db


# --------------------------------------------------------------------------- #
# Module-level context store
# --------------------------------------------------------------------------- #

_current_context: Optional[str] = None


def set_context(context: str) -> None:
    """
    Call this inside your pipeline function to pass context to the decorator.

    Example:
        @audit(name="my_pipeline")
        def my_pipeline(query: str) -> str:
            context = retriever.get(query)
            set_context(context)
            return llm.call(query, context)
    """
    global _current_context
    _current_context = context


# --------------------------------------------------------------------------- #
# Agent Tracer — context manager for agent workflows
# --------------------------------------------------------------------------- #

@dataclass
class ToolCall:
    tool_name: str
    input: Any
    output: Any
    success: bool
    latency_ms: float


@dataclass
class AgentTrace:
    agent_name: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    final_response: str = ""
    total_latency_ms: float = 0.0


class AgentTracer:
    """
    Context manager for tracing agent tool calls.

    Usage:
        with AgentTracer("my_agent") as tracer:
            tracer.log_tool_call("search", input=query, output=results)
            tracer.log_response(final_answer)
    """

    def __init__(self, agent_name: str, db_path: str = "agentaudit.db"):
        self.agent_name = agent_name
        self.db_path = db_path
        self.trace = AgentTrace(agent_name=agent_name)
        self._t0: float = 0.0

    def __enter__(self) -> "AgentTracer":
        self._t0 = time.perf_counter()
        return self

    def log_tool_call(
        self,
        tool_name: str,
        input: Any,
        output: Any,
        success: bool = True,
    ) -> None:
        t0 = time.perf_counter()
        self.trace.tool_calls.append(
            ToolCall(
                tool_name=tool_name,
                input=input,
                output=output,
                success=success,
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
        )

    def log_response(self, response: str) -> None:
        self.trace.final_response = response

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.trace.total_latency_ms = round(
            (time.perf_counter() - self._t0) * 1000, 2
        )

        # Save agent trace as a run
        init_db(self.db_path)
        save_run(
            pipeline_name=self.agent_name,
            query="agent_trace",
            response=self.trace.final_response,
            context="",
            db_path=self.db_path,
        )

        return False  # let exceptions propagate normally


# --------------------------------------------------------------------------- #
# Audit Decorator — for pipeline functions
# --------------------------------------------------------------------------- #

def audit(
    name: str,
    metrics: Optional[list[str]] = None,
    provider: str = "gemini",
    model: str = "gemini-1.5-flash",
    api_key: Optional[str] = None,
    threshold_ms: float = 3000.0,
    db_path: str = "agentaudit.db",
):
    """
    Decorator that wraps a pipeline function and automatically:
    - Measures latency
    - Runs hallucination detection
    - Runs faithfulness scoring
    - Calculates cost
    - Saves everything to SQLite

    Usage:
        @audit(name="my_pipeline", metrics=["hallucination", "cost"])
        def my_pipeline(query: str) -> str:
            context = retriever.get(query)
            set_context(context)
            return llm.call(query, context)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            global _current_context

            # Fix mutable default
            active_metrics = metrics or [
                "hallucination", "faithfulness", "cost", "latency"
            ]

            # Reset context before every run
            _current_context = None

            # --- Run the original function, measure latency ---
            t0 = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                _current_context = None
                raise e
            latency_ms = (time.perf_counter() - t0) * 1000

            # --- Grab what we need ---
            response = str(result)
            context = _current_context or ""
            query = args[0] if args else kwargs.get("query", "")

            # --- Run metrics ---
            hallucination_result = None
            faithfulness_result = None
            cost_result = None
            latency_result = None

            if "latency" in active_metrics:
                latency_result = LatencyResult(
                    step_name=name,
                    latency_ms=round(latency_ms, 2),
                    threshold_ms=threshold_ms,
                    is_slow=latency_ms > threshold_ms,
                )

            if "hallucination" in active_metrics and context:
                hallucination_result = detect_hallucination(
                    response=response,
                    context=context,
                    model=model,
                    api_key=api_key,
                )

            if "faithfulness" in active_metrics and context:
                faithfulness_result = detect_faithfulness(
                    response=response,
                    context=context,
                    provider=provider,
                    model=model,
                    api_key=api_key,
                )

            if "cost" in active_metrics:
                cost_result = calculate_cost(
                    input_tokens=500,   # placeholder — real counts added later
                    output_tokens=100,
                    model=model,
                )

            # --- Save to SQLite ---
            init_db(db_path)
            save_run(
                pipeline_name=name,
                query=str(query),
                response=response,
                context=context,
                hallucination_result=hallucination_result,
                faithfulness_result=faithfulness_result,
                cost_result=cost_result,
                latency_result=latency_result,
                db_path=db_path,
            )

            # --- Reset context ---
            _current_context = None

            return result

        return wrapper
    return decorator