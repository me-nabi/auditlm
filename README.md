<div align="center">

# AgentAudit

[![PyPI](https://img.shields.io/pypi/v/auditlm?color=blue&label=PyPI)](https://pypi.org/project/auditlm/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://pypi.org/project/auditlm/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/me-nabi/AiAudit/blob/main/LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/me-nabi/AiAudit?style=social)](https://github.com/me-nabi/AiAudit)

### Open source evaluation toolkit for LLM pipelines and AI agents.

Hallucination detection · Faithfulness scoring · Cost tracking · Latency logging
Regression testing · Agent trace viewer

**Self-hostable · No SaaS · No login · No data leaving your machine**

</div>

```bash
pip install auditlm
agentaudit init
agentaudit dashboard
```

---

## Why AgentAudit?

32% of AI teams cite quality as their #1 barrier to production.
Most teams ship prompts blindly or debug with print statements.

AgentAudit gives you a proper evaluation layer:

- **Hallucination detection** — did the model make up something not in the source?
- **Faithfulness scoring** — did the model contradict the retrieved context?
- **Cost tracking** — how much does each query cost in USD and INR?
- **Latency logging** — how slow is each step?
- **Regression testing** — did my last prompt change make things better or worse?
- **Agent trace viewer** — which tools did the agent call, in what order?

---

## Quick Start

### 1. Install

```bash
pip install auditlm
```

### 2. Setup (one time)

```bash
agentaudit init
```

Walks you through picking a provider (Gemini or OpenAI), pasting your API key,
and choosing a judge model. Your key is saved locally at `~/.agentaudit/.env`.

### 3. Add to your pipeline

**Before AgentAudit — your existing code:**

```python
def answer_question(query):
    docs = retriever.search(query)
    return llm.generate(query, docs)
```

**After AgentAudit — 3 lines added:**

```python
from agentaudit import audit, set_context          # line 1

@audit(name="my_pipeline")                          # line 2
def answer_question(query):
    docs = retriever.search(query)
    set_context(docs)                                # line 3
    return llm.generate(query, docs)
```

Your code works exactly the same. AgentAudit silently evaluates every run
and saves the results.

### 4. See results

```bash
agentaudit dashboard
```

Opens a local dashboard at `http://localhost:8501` with four pages:

- **Overview** — all pipelines at a glance, latest scores
- **Run Details** — drill into any run, see every claim the judge extracted
- **Trends** — scores over time as charts
- **Regression** — compare two runs side by side

---

## Don't want to edit code? Use the starter file.

```bash
agentaudit example
```

Creates `my_pipeline.py` with clear TODO markers. Open it, replace two lines
with your retrieval and AI code, run it. No guessing where things go.

---

## CLI Commands

| Command | What it does |
|---|---|
| `agentaudit init` | First-time setup — provider, API key, model |
| `agentaudit dashboard` | Open the Streamlit dashboard |
| `agentaudit compare --pipeline my_pipeline` | Compare last two runs in terminal |
| `agentaudit config --show` | Show current config (key is masked) |
| `agentaudit config --reset` | Update API key or model |
| `agentaudit example` | Generate a starter pipeline file |

---

## How It Works

AgentAudit uses **LLM-as-judge** — it sends your pipeline's output and context
to a judge model (Gemini Flash by default) and asks:

> "Extract every claim from this response.
> For each claim, is it supported by the context?"

The judge returns individual claims with verdicts (SUPPORTED / UNSUPPORTED /
CONTRADICTED), and AgentAudit calculates a score:

hallucination_score = unsupported claims / total claims


Scores, claims, and metadata are saved to a local SQLite database.
Nothing leaves your machine.

---

## Optional: Exact Cost Tracking

By default, AgentAudit estimates token counts from text length (~4 chars per token).
For exact cost, add one line inside your function:

```python
from agentaudit import audit, set_context, set_tokens

@audit(name="my_pipeline")
def my_pipeline(query):
    docs = retriever.search(query)
    set_context(docs)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": query}],
    )

    set_tokens(
        input=response.usage.prompt_tokens,
        output=response.usage.completion_tokens,
    )

    return response.choices[0].message.content
```

The dashboard labels costs as "estimated" or "exact" so you always know which you're seeing.

---

## Agent Tracing

For agent workflows with tool calls:

```python
from agentaudit import AgentTracer

with AgentTracer("my_agent") as tracer:
    result = search_tool(query)
    tracer.log_tool_call("search", input=query, output=result)

    answer = llm.generate(query, result)
    tracer.log_response(answer)
```

---

## Supported Judge Models

AgentAudit supports any model from these providers as the evaluation judge:

**Google Gemini** (free tier available)
- gemini-flash-latest (default)
- gemini-3.5-flash
- gemini-3-flash
- gemini-3.1-pro

**OpenAI**
- gpt-4o-mini
- gpt-4o

---

## Cost Tracking Covers These Models

Built-in pricing for common models. Add custom models at runtime:

```python
from agentaudit import calculate_cost
from agentaudit.metrics.cost import add_model_pricing

add_model_pricing("my-custom-model", input_price_per_1k=0.001, output_price_per_1k=0.003)
```

---

## Tech Stack

- **Python** — core metrics engine
- **SQLite** — local storage, zero setup
- **Streamlit** — dashboard
- **LLM-as-judge** — Gemini Flash or GPT-4o-mini for scoring
- **pyproject.toml** — proper Python packaging

---

## Project Structure

```text
agentaudit/
├── agentaudit/
│ ├── init.py
│ ├── cli.py # 5 CLI commands
│ ├── metrics/
│ │ ├── hallucination.py # LLM-as-judge hallucination detection
│ │ ├── faithfulness.py # faithfulness scoring
│ │ ├── cost.py # token cost tracking (USD + INR)
│ │ └── latency.py # latency measurement
│ ├── core/
│ │ ├── wrapper.py # @audit decorator + AgentTracer
│ │ ├── storage.py # SQLite storage layer
│ │ └── regression.py # regression testing suite
│ └── dashboard/
│ └── app.py # 4-page Streamlit dashboard
├── examples/
│ ├── rag_pipeline.py # RAG pipeline example
│ └── agent_trace.py # Agent tracing example
├── pyproject.toml
└── README.md

```

---

## Contributing

PRs welcome. If you find a bug or want a feature, open an issue.

## License

MIT
