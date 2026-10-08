"""Centralized Groq model pricing for estimated API cost calculation."""

from __future__ import annotations

from typing import Any, Dict, Optional

# Rates are USD per 1,000,000 tokens.
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "openai/gpt-oss-120b": {
        "input_per_million": 0.15,
        "output_per_million": 0.60,
    },
    "openai/gpt-oss-20b": {
        "input_per_million": 0.075,
        "output_per_million": 0.30,
    },
}


def estimate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Optional[float]:
    """
    Estimate USD cost from token counts and configured model pricing.

    Cached tokens are a subset of prompt_tokens and must not be added again.
    Returns None when the model has no configured pricing.
    """
    rates = MODEL_PRICING.get(model)
    if not rates:
        return None

    input_rate = rates.get("input_per_million")
    output_rate = rates.get("output_per_million")
    if input_rate is None or output_rate is None:
        return None

    input_cost = (prompt_tokens / 1_000_000) * input_rate
    output_cost = (completion_tokens / 1_000_000) * output_rate
    return round(input_cost + output_cost, 10)


def build_usage_metadata(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cached_tokens: Optional[int] = None,
    request_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a JSON-serializable usage payload for API responses / persistence."""
    usage: Dict[str, Any] = {
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimate_cost_usd(model, prompt_tokens, completion_tokens),
    }
    if cached_tokens is not None:
        usage["cached_tokens"] = cached_tokens
    if request_id:
        usage["request_id"] = request_id
    if latency_ms is not None:
        usage["latency_ms"] = round(latency_ms, 1)
    return usage
