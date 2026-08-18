# cost.py
# Tracks token usage and calculates cost in USD and INR.
# No LLM calls — pure math based on token counts and model pricing.

from dataclasses import dataclass
from typing import Optional


# --------------------------------------------------------------------------- #
# Data Structure
# --------------------------------------------------------------------------- #

@dataclass
class CostResult:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: Optional[float]
    cost_inr: Optional[float]
    model: str
    is_estimated: bool = False


# --------------------------------------------------------------------------- #
# Pricing Table
# --------------------------------------------------------------------------- #

# Price per 1000 tokens (input, output) in USD.
# Verified against provider pricing pages, August 2026.
# Model names and prices change often — use add_model_pricing() for
# anything not listed here.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Google Gemini (developer API)
    "gemini-3.1-pro":        (0.002000, 0.012000),
    "gemini-3.7-flash":      (0.000750, 0.003750),
    "gemini-3.5-flash":      (0.001500, 0.009000),
    "gemini-3-flash":        (0.000500, 0.003000),
    "gemini-3.1-flash-lite": (0.000250, 0.001500),
    "gemini-flash-latest":   (0.001500, 0.009000),  # alias → 3.5 Flash rate

    # OpenAI
    "gpt-4o":                (0.002500, 0.010000),
    "gpt-4o-mini":           (0.000150, 0.000600),

    # Anthropic Claude
    "claude-opus-5":         (0.005000, 0.025000),
    "claude-sonnet-5":       (0.002000, 0.010000),
    "claude-haiku-4-5":      (0.001000, 0.005000),
}

DEFAULT_USD_TO_INR = 84.0


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "gemini-flash-latest",
    usd_to_inr: float = DEFAULT_USD_TO_INR,
    is_estimated: bool = False,
) -> CostResult:
    """
    Calculate cost of an LLM call based on token usage.

    If the model is not in MODEL_PRICING, returns a CostResult with
    cost_usd and cost_inr set to None (unknown) rather than raising —
    an unknown model should never crash the user's pipeline. Register
    custom models with add_model_pricing().
    """
    if not isinstance(input_tokens, int) or input_tokens < 0:
        raise ValueError("input_tokens must be a non-negative integer")

    if not isinstance(output_tokens, int) or output_tokens < 0:
        raise ValueError("output_tokens must be a non-negative integer")

    if model not in MODEL_PRICING:
        return CostResult(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=None,
            cost_inr=None,
            model=model,
            is_estimated=is_estimated,
        )

    input_price, output_price = MODEL_PRICING[model]

    cost_usd = (input_tokens * input_price) + (output_tokens * output_price)
    cost_inr = cost_usd * usd_to_inr

    return CostResult(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=round(cost_usd, 6),
        cost_inr=round(cost_inr, 4),
        model=model,
        is_estimated=is_estimated,
    )


def add_model_pricing(
    model: str,
    input_price_per_1k: float,
    output_price_per_1k: float,
) -> None:
    """
    Register a new model's pricing at runtime.
    Useful for custom or newly released models.

    Example:
        add_model_pricing("gpt-5", 0.01, 0.03)
    """
    MODEL_PRICING[model] = (input_price_per_1k, output_price_per_1k)