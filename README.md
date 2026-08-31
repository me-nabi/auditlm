<div align="center">

# AuditLM

[![PyPI](https://img.shields.io/pypi/v/auditlm?color=blue&label=PyPI)](https://pypi.org/project/auditlm/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://pypi.org/project/auditlm/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/me-nabi/AiAudit/blob/main/LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/me-nabi/AiAudit?style=social)](https://github.com/me-nabi/AiAudit)

**Open source evaluation toolkit for LLM pipelines and AI agents.**

Hallucination detection · Faithfulness scoring · Cost tracking
Latency logging · Regression testing · Agent trace viewer

*Self-hostable · No SaaS · No login · No data leaving your machine*

</div>

```bash
pip install auditlm
auditlm init
auditlm dashboard
```

---

## Why AuditLM?

32% of AI teams cite quality as their #1 barrier to production.
Most teams ship prompts blindly or debug with print statements.

AuditLM gives you a proper evaluation layer:

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
auditlm init
```

Walks you through picking a provider (Gemini or OpenAI), pasting your API key,
and choosing a judge model. Config saved locally at `~/.agentaudit/.env`.

### 3. Add to your pipeline

**Before:**

```python
def answer_question(query):
    docs = retriever.search(query)
    return llm.generate(query, docs)
```

**After — 3 lines added:**

```python
from agentaudit import audit, set_context          # line 1

@audit(name="my_pipeline")                          # line 2
def answer_question(query):
    docs = retriever.search(query)
    set_context(docs)                                # line 3
    return llm.generate(query, docs)
```

Your code works exactly the same. AuditLM silently evaluates every run.

### 4. See results

```bash
auditlm dashboard
```

Opens a local dashboard at `localhost:8501` with four pages:
**Overview** · **Run Details** · **Trends** · **Regression**

---

## Zero-code starter

```bash
auditlm example
```

Creates `my_pipeline.py` with clear TODO markers. Replace two lines, run it, done.

---

## CLI

| Command | What it does |
|---|---|
| `auditlm init` | First-time setup |
| `auditlm dashboard` | Open Streamlit dashboard |
| `auditlm compare --pipeline NAME` | Compare last two runs |
| `auditlm config --show` | Show current config |
| `auditlm config --reset` | Update API key or model |
| `auditlm example` | Generate starter file |

---

## How it works

AuditLM uses **LLM-as-judge** — sends your pipeline's output and context
to a judge model (Gemini Flash by default) and asks:

> "Extract every claim. For each, is it supported by the context?"

The judge returns claims with verdicts (SUPPORTED / UNSUPPORTED / CONTRADICTED)
and AuditLM calculates:

hallucination_score = unsupported claims / total claims


Everything saved to local SQLite. Nothing leaves your machine.

---

## Exact cost tracking (optional)

By default, AuditLM estimates tokens from text length.
For exact cost, add one line:

```python
from agentaudit import set_tokens

set_tokens(
    input=response.usage.prompt_tokens,
    output=response.usage.completion_tokens,
)
```

Dashboard labels costs as **estimated** or **exact**.

---

## Agent tracing

```python
from agentaudit import AgentTracer

with AgentTracer("my_agent") as tracer:
    result = search_tool(query)
    tracer.log_tool_call("search", input=query, output=result)
    tracer.log_response(answer)
```

---

## Supported judge models

**Google Gemini** (free tier available):
gemini-flash-latest · gemini-3.5-flash · gemini-3-flash · gemini-3.1-pro

**OpenAI**:
gpt-4o-mini · gpt-4o

Custom models: `add_model_pricing("model", input_per_1k, output_per_1k)`

---

## Tech stack

Python · SQLite · Streamlit · LLM-as-judge · pyproject.toml

---

## Contributing

PRs welcome. Open an issue for bugs or feature requests.

## License

MIT
