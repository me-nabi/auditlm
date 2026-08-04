# cost.py
# Tracks token usage and calculates cost in USD and INR.
# No LLM calls — pure math based on token counts and model pricing.

from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# Data Structure
# --------------------------------------------------------------------------- #

@dataclass
class CostResult:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    cost_inr: float
    model: str


# --------------------------------------------------------------------------- #
# Pricing Table
# --------------------------------------------------------------------------- #

# Price per 1000 tokens (input, output) in USD
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini":      (0.000150, 0.000600),
    "gpt-4o":           (0.005000, 0.015000),
    "gemini-1.5-flash": (0.000075, 0.000300),
    "gemini-1.5-pro":   (0.003500, 0.010500),
}

DEFAULT_USD_TO_INR = 84.0


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "gemini-1.5-flash",
    usd_to_inr: float = DEFAULT_USD_TO_INR,
) -> CostResult:
    """
    Calculate cost of an LLM call based on token usage.

    Args:
        input_tokens:  Number of tokens in the prompt.
        output_tokens: Number of tokens in the response.
        model:         Model used for the call.
        usd_to_inr:    Exchange rate. Override with today's rate if needed.

    Returns:
        CostResult with cost in both USD and INR.
    """

    if not isinstance(input_tokens, int) or input_tokens < 0:
        raise ValueError("input_tokens must be a non-negative integer")

    if not isinstance(output_tokens, int) or output_tokens < 0:
        raise ValueError("output_tokens must be a non-negative integer")

    if model not in MODEL_PRICING:
        raise ValueError(
            f"Unknown model: '{model}'. "
            f"Available models: {list(MODEL_PRICING.keys())}"
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