"""Tests for Groq rate-limit parsing, user messages, and model fallback."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from groq import RateLimitError

from app.rag.generation import _format_llm_error
from app.rag.llm import GroqService, filter_history_for_llm
from app.rag.rate_limit import format_capacity_error, parse_retry_after_minutes


SAMPLE_429 = (
    "Error code: 429 - {'error': {'message': 'Rate limit reached for model "
    "`openai/gpt-oss-120b` in organization `org_x` service tier `on_demand` on "
    "tokens per day (TPD): Limit 200000, Used 199627, Requested 2258. "
    "Please try again in 13m34.319999999s. Need more tokens? Upgrade to Dev Tier "
    "today at https://console.groq.com/settings/billing', "
    "'type': 'tokens', 'code': 'rate_limit_exceeded'}}"
)


def test_parse_retry_after_minutes_from_groq_message():
    assert parse_retry_after_minutes(SAMPLE_429) == 14


def test_format_capacity_error_hides_raw_api_dump():
    message = format_capacity_error(SAMPLE_429)
    assert "Error code: 429" not in message
    assert "org_" not in message
    assert "I'm temporarily out of AI capacity" in message
    assert "about 14 minutes" in message


def test_format_llm_error_uses_friendly_capacity_copy():
    message = _format_llm_error(Exception(SAMPLE_429))
    assert message.startswith("I'm temporarily out of AI capacity.")
    assert "Error generating LLM response" not in message


def test_filter_history_drops_capacity_only_turns():
    history = [
        {"role": "user", "content": "hello"},
        {
            "role": "assistant",
            "content": "I'm temporarily out of AI capacity. Please try again in about 14 minutes.",
        },
        {"role": "user", "content": "what is malaria?"},
        {"role": "assistant", "content": "Malaria is ..."},
    ]
    cleaned = filter_history_for_llm(history)
    assert cleaned == [
        {"role": "user", "content": "what is malaria?"},
        {"role": "assistant", "content": "Malaria is ..."},
    ]


def _fake_completion(text: str, model: str):
    return SimpleNamespace(
        id="chatcmpl-test",
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            prompt_tokens_details=None,
        ),
        x_groq=None,
    )


def test_generate_answer_falls_back_silently():
    service = GroqService()
    client = MagicMock()

    def create_side_effect(**kwargs):
        model = kwargs["model"]
        if model == "openai/gpt-oss-120b":
            raise RateLimitError(
                message=SAMPLE_429,
                response=MagicMock(status_code=429, headers={}),
                body={
                    "error": {
                        "message": SAMPLE_429,
                        "type": "tokens",
                        "code": "rate_limit_exceeded",
                    }
                },
            )
        return _fake_completion("Hello from backup.", model)

    client.chat.completions.create.side_effect = create_side_effect

    with patch.object(service, "_get_client", return_value=client), patch(
        "app.rag.llm.settings"
    ) as mock_settings:
        mock_settings.groq_model = "openai/gpt-oss-120b"
        mock_settings.groq_fallback_model = "openai/gpt-oss-20b"
        answer, usage = service.generate_answer("hello")

    assert answer == "Hello from backup."
    assert "Falling back" not in answer
    assert "temporarily out of capacity" not in answer
    assert usage is not None
    assert usage["model"] == "openai/gpt-oss-20b"
    assert "rate_limit_fallback" not in usage


def test_generate_answer_raises_friendly_path_when_all_models_limited():
    service = GroqService()
    client = MagicMock()
    client.chat.completions.create.side_effect = RateLimitError(
        message=SAMPLE_429,
        response=MagicMock(status_code=429, headers={}),
        body={"error": {"message": SAMPLE_429, "code": "rate_limit_exceeded"}},
    )

    with patch.object(service, "_get_client", return_value=client), patch(
        "app.rag.llm.settings"
    ) as mock_settings:
        mock_settings.groq_model = "openai/gpt-oss-120b"
        mock_settings.groq_fallback_model = "openai/gpt-oss-20b"
        with pytest.raises(RateLimitError):
            service.generate_answer("hello")

    # Pipeline layer still converts this into the friendly copy.
    assert "I'm temporarily out of AI capacity" in _format_llm_error(
        RateLimitError(
            message=SAMPLE_429,
            response=MagicMock(status_code=429, headers={}),
            body={"error": {"message": SAMPLE_429}},
        )
    )
