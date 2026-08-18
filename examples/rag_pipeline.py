# rag_pipeline.py
# Example: how to use AgentAudit with a RAG pipeline.
# Run with: python examples/rag_pipeline.py

import os
from agentaudit import audit, set_context


# Fake retriever — simulates what your real retriever would return
def retrieve(query: str) -> str:
    return """
    AgentAudit is an open source evaluation toolkit for LLM pipelines.
    It supports hallucination detection, faithfulness scoring, cost tracking,
    latency logging, and regression testing. It runs fully locally with
    no SaaS, no login, and no data leaving your machine.
    It can be installed with: pip install agentaudit.
    """


# Fake LLM — one hallucination included: "founded in 2023" is not in context
def fake_llm(query: str, context: str) -> str:
    return (
        "AgentAudit is an open source toolkit founded in 2023. "
        "It helps teams evaluate LLM pipelines locally with no SaaS required. "
        "You can install it using pip install agentaudit."
    )


@audit(
    name="rag_pipeline",
    metrics=["hallucination", "faithfulness", "cost", "latency"],
    provider="gemini",
    model="gemini-flash-latest",
    api_key=os.environ.get("GEMINI_API_KEY"),
)
def rag_pipeline(query: str) -> str:
    context = retrieve(query)
    set_context(context)
    response = fake_llm(query, context)
    return response


if __name__ == "__main__":
    print("Running RAG pipeline with AgentAudit...\n")
    result = rag_pipeline("What is AgentAudit and how do I install it?")
    print("Response:")
    print(result)
    print("\n✅ Run complete — check the dashboard:")
    print("   agentaudit dashboard")
