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
    breakdown = estimate_cost_breakdown_usd(model, prompt_tokens, completion_tokens)
    if breakdown is None:
        return None

    return breakdown["total_cost"]


def estimate_cost_breakdown_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Optional[Dict[str, float]]:
    """Estimate input and output costs separately using the selected model's rates."""
    rates = MODEL_PRICING.get(model)
    if not rates:
        return None

    input_rate = rates.get("input_per_million")
    output_rate = rates.get("output_per_million")
    if input_rate is None or output_rate is None:
        return None

    input_cost = round((prompt_tokens / 1_000_000) * input_rate, 10)
    output_cost = round((completion_tokens / 1_000_000) * output_rate, 10)
    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": round(input_cost + output_cost, 10),
    }


def build_usage_metadata(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_tokens: Optional[int] = None,
    request_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a JSON-serializable usage payload for API responses / persistence."""
    input_tokens = int(prompt_tokens)
    output_tokens = int(completion_tokens)
    costs = estimate_cost_breakdown_usd(model, input_tokens, output_tokens)
    usage: Dict[str, Any] = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        # Keep the original provider field names for compatibility with existing clients.
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "input_cost": costs["input_cost"] if costs else None,
        "output_cost": costs["output_cost"] if costs else None,
        "total_cost": costs["total_cost"] if costs else None,
        "estimated_cost_usd": costs["total_cost"] if costs else None,
    }
    if cached_tokens is not None:
        usage["cached_tokens"] = cached_tokens
    if request_id:
        usage["request_id"] = request_id
    if latency_ms is not None:
        usage["latency_ms"] = round(latency_ms, 1)
    return usage
