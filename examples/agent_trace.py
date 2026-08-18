# agent_trace.py
# Example: how to use AgentAudit to trace an agent's tool calls.
# Run with: python examples/agent_trace.py

from agentaudit import AgentTracer


# Fake tools — replace with your real tool functions
def search_tool(query: str) -> str:
    return f"Search results for: {query}"


def calculator_tool(expression: str) -> str:
    return str(eval(expression))


def run_agent(query: str) -> str:
    """
    A simple agent that uses two tools then gives an answer.
    AgentTracer records every tool call automatically.
    """

    with AgentTracer("my_agent") as tracer:

        # Tool call 1 — search
        search_result = search_tool(query)
        tracer.log_tool_call(
            tool_name="search",
            input=query,
            output=search_result,
        )

        # Tool call 2 — calculator
        calc_result = calculator_tool("2 + 2")
        tracer.log_tool_call(
            tool_name="calculator",
            input="2 + 2",
            output=calc_result,
        )

        # Final answer
        answer = f"Based on search: {search_result}. Also, 2+2={calc_result}."
        tracer.log_response(answer)

    return answer


if __name__ == "__main__":
    print("Running agent with AgentAudit tracing...\n")
    result = run_agent("What is AgentAudit?")
    print("Agent answer:")
    print(result)
    print("\n✅ Trace saved — check the dashboard:")
    print("   agentaudit dashboard")
