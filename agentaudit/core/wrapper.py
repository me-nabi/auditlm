# wrapper.py
# Decorator and context manager for wrapping LLM pipelines and agents.
# Plug into existing code with minimal change.

import os
import time
import functools
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

from agentaudit.metrics.hallucination import detect_hallucination
from agentaudit.metrics.faithfulness import detect_faithfulness
from agentaudit.metrics.cost import calculate_cost
from agentaudit.metrics.latency import LatencyResult
from agentaudit.core.storage import save_run, init_db, DEFAULT_DB_PATH


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


_current_input_tokens: Optional[int] = None
_current_output_tokens: Optional[int] = None


def set_tokens(input: int, output: int) -> None:
    """
    Optional: call inside your pipeline to report exact token usage.
    If not called, AgentAudit estimates tokens from text length.

    Example:
        @audit(name="my_pipeline")
        def my_pipeline(query):
            response = client.chat.completions.create(...)
            set_tokens(
                input=response.usage.prompt_tokens,
                output=response.usage.completion_tokens,
            )
            return response.choices[0].message.content
    """
    global _current_input_tokens, _current_output_tokens
    _current_input_tokens = input
    _current_output_tokens = output


def _estimate_tokens(text: str) -> int:
    """
    Rough token estimate: ~4 characters per token for English text.
    Not exact — but better than hardcoded 500 or showing nothing.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


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

    def __init__(self, agent_name: str, db_path: str = DEFAULT_DB_PATH):
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
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    threshold_ms: float = 3000.0,
    db_path: str = DEFAULT_DB_PATH,
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
            global _current_context, _current_input_tokens, _current_output_tokens

            # Fix mutable default
            active_metrics = metrics or [
                "hallucination", "faithfulness", "cost", "latency"
            ]

            active_provider = provider or os.environ.get("AGENTAUDIT_PROVIDER", "gemini")
            active_model = model or os.environ.get("AGENTAUDIT_MODEL", "gemini-flash-latest")

            # Reset context before every run
            _current_context = None
            _current_input_tokens = None
            _current_output_tokens = None

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

            if "hallucination" in active_metrics and not context:
                print("⚠️  AgentAudit: no context set — add set_context(your_docs) "
                      "inside your function to enable hallucination checking.")
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
                    provider=active_provider,
                    model=active_model,
                    api_key=api_key,
                )
                if hallucination_result.error:
                    print(f"⚠️  AgentAudit: hallucination check failed — {hallucination_result.error}")

            if "faithfulness" in active_metrics and context:
                faithfulness_result = detect_faithfulness(
                    response=response,
                    context=context,
                    provider=active_provider,
                    model=active_model,
                    api_key=api_key,
                )
                if faithfulness_result.error:
                    print(f"⚠️  AgentAudit: faithfulness check failed — {faithfulness_result.error}")

            if "cost" in active_metrics:
                if _current_input_tokens is not None:
                    cost_result = calculate_cost(
                        input_tokens=_current_input_tokens,
                        output_tokens=_current_output_tokens or 0,
                        model=active_model,
                        is_estimated=False,
                    )
                else:
                    est_input = _estimate_tokens(str(query) + context)
                    est_output = _estimate_tokens(response)
                    cost_result = calculate_cost(
                        input_tokens=est_input,
                        output_tokens=est_output,
                        model=active_model,
                        is_estimated=True,
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
            _current_input_tokens = None
            _current_output_tokens = None

            return result

        return wrapper
    return decorator