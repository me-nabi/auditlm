# faithfulness.py
# Detects faithfulness failures in LLM responses using LLM-as-judge approach.
# Score: 1.0 = fully faithful, 0.0 = fully contradicts context

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- #
# Data Structures
# --------------------------------------------------------------------------- #

@dataclass
class Claim:
    claim: str
    status: str
    evidence: Optional[str] = None


@dataclass
class FaithfulnessResult:
    faithfulness_score: Optional[float]
    is_faithful: bool
    claims: list[Claim] = field(default_factory=list)
    reasoning: str = ""
    latency_ms: float = 0.0
    model_used: str = ""
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #

JUDGE_PROMPT = """You are an expert fact-checker. Your job is to check
if an AI response faithfully represents the provided context.

CONTEXT:
{context}

AI RESPONSE:
{response}

TASK:
1. Extract every factual claim from the AI response.
2. For each claim check if it is:
   - FAITHFUL: claim is consistent with the context
   - CONTRADICTED: claim directly conflicts with the context

IMPORTANT: Do not use your world knowledge. Only use the provided context.
Ignore claims that are not mentioned in context at all — only flag direct contradictions.

Return ONLY this JSON, nothing else:
{{
  "claims": [
    {{"claim": "...", "status": "FAITHFUL|CONTRADICTED", "evidence": "quote from context or null"}}
  ],
  "faithfulness_score": <float 0.0 to 1.0>,
  "is_faithful": <true|false>,
  "reasoning": "one line explanation"
}}

faithfulness_score = faithful claims / total claims.
If no claims found return faithfulness_score 1.0.
"""


# --------------------------------------------------------------------------- #
# Internal Judge Call
# --------------------------------------------------------------------------- #

def _call_judge(
    context: str,
    response: str,
    model: str,
    provider: str,
    api_key: str,
) -> tuple[dict, float]:

    prompt = JUDGE_PROMPT.format(context=context, response=response)
    t0 = time.perf_counter()

    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        judge = genai.GenerativeModel(model)
        result = judge.generate_content(prompt)
        raw = result.text

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=1000,
        )
        raw = completion.choices[0].message.content

    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'openai'")

    latency_ms = (time.perf_counter() - t0) * 1000

    # Gemini sometimes wraps JSON in markdown — strip it
    raw = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Judge returned invalid JSON: {raw[:200]}") from e

    return parsed, latency_ms


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def detect_faithfulness(
    response: str,
    context: str,
    provider: str = "gemini",
    model: str = "gemini-flash-latest",
    api_key: Optional[str] = None,
    threshold: float = 0.5,
) -> FaithfulnessResult:

    if not response or not response.strip():
        raise ValueError("response cannot be empty")

    if not context or not context.strip():
        raise ValueError("context cannot be empty")

    # Pick API key from argument or environment
    if provider == "gemini":
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise EnvironmentError(
                "No Gemini API key found. Set GEMINI_API_KEY or pass api_key=..."
            )
    elif provider == "openai":
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise EnvironmentError(
                "No OpenAI API key found. Set OPENAI_API_KEY or pass api_key=..."
            )
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'openai'")

    try:
        raw, latency_ms = _call_judge(context, response, model, provider, key)
    except Exception as e:
        return FaithfulnessResult(
            faithfulness_score=None,
            is_faithful=False,
            error=str(e),
            model_used=model,
        )

    claims = [
        Claim(
            claim=c.get("claim", ""),
            status=c.get("status", "FAITHFUL").upper(),
            evidence=c.get("evidence"),
        )
        for c in raw.get("claims", [])
    ]

    score = float(raw.get("faithfulness_score", 1.0))
    score = max(0.0, min(1.0, score))

    return FaithfulnessResult(
        faithfulness_score=score,
        is_faithful=score >= threshold,
        claims=claims,
        reasoning=raw.get("reasoning", ""),
        latency_ms=latency_ms,
        model_used=model,
    )