# hallucination.py
# Detects hallucinations in LLM responses using LLM-as-judge approach.
# Score: 0.0 = fully grounded, 1.0 = fully hallucinated

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from openai import OpenAI


# --------------------------------------------------------------------------- #
# Data Structures
# --------------------------------------------------------------------------- #

@dataclass
class Claim:
    claim: str
    status: str
    evidence: Optional[str] = None


@dataclass
class HallucinationResult:
    hallucination_score: float
    has_hallucination: bool
    claims: list[Claim] = field(default_factory=list)
    reasoning: str = ""
    latency_ms: float = 0.0
    model_used: str = ""
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #

JUDGE_PROMPT = """You are an expert fact-checker. Your job is to check
if an AI response is grounded in the provided context.

CONTEXT:
{context}

AI RESPONSE:
{response}

TASK:
1. Extract every factual claim from the AI response.
2. For each claim check if it is:
   - SUPPORTED: claim is backed by the context
   - UNSUPPORTED: claim is not in the context at all
   - CONTRADICTED: claim conflicts with the context

IMPORTANT: Do not use your world knowledge. Only use the provided context.

Return ONLY this JSON, nothing else:
{{
  "claims": [
    {{"claim": "...", "status": "SUPPORTED|UNSUPPORTED|CONTRADICTED", "evidence": "quote from context or null"}}
  ],
  "hallucination_score": <float 0.0 to 1.0>,
  "has_hallucination": <true|false>,
  "reasoning": "one line explanation"
}}

hallucination_score = unsupported + contradicted claims / total claims.
"""


# --------------------------------------------------------------------------- #
# Internal Judge Call
# --------------------------------------------------------------------------- #

def _call_judge(
    context: str,
    response: str,
    model: str,
    client: OpenAI,
) -> tuple[dict, float]:
    
    prompt = JUDGE_PROMPT.format(context=context, response=response)

    t0 = time.perf_counter()
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
        max_tokens=1000,
    )
    latency_ms = (time.perf_counter() - t0) * 1000

    raw = completion.choices[0].message.content
    
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Judge returned invalid JSON: {raw[:200]}") from e

    return parsed, latency_ms


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def detect_hallucination(
    response: str,
    context: str,
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    threshold: float = 0.0,
) -> HallucinationResult:

    if not response or not response.strip():
        raise ValueError("response cannot be empty")
    
    if not context or not context.strip():
        raise ValueError("context cannot be empty")

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError(
            "No OpenAI API key found. Set OPENAI_API_KEY or pass api_key=..."
        )
    
    client = OpenAI(api_key=key)

    try:
        raw, latency_ms = _call_judge(context, response, model, client)
    except Exception as e:
        return HallucinationResult(
            hallucination_score=0.0,
            has_hallucination=False,
            error=str(e),
            model_used=model,
        )

    claims = [
        Claim(
            claim=c.get("claim", ""),
            status=c.get("status", "UNSUPPORTED").upper(),
            evidence=c.get("evidence"),
        )
        for c in raw.get("claims", [])
    ]

    score = float(raw.get("hallucination_score", 0.0))
    score = max(0.0, min(1.0, score))

    return HallucinationResult(
        hallucination_score=score,
        has_hallucination=score > threshold,
        claims=claims,
        reasoning=raw.get("reasoning", ""),
        latency_ms=latency_ms,
        model_used=model,
    )