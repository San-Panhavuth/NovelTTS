"""Unit tests for phonetics inference service."""

import logging

import pytest

from app.services.phonetics_inference import (
    PhoneticsEntry,
    PhoneticsInferenceResponse,
    infer_pronunciations,
)


class MockLLMProvider:
    """Mock LLMProvider that returns controllable JSON responses."""

    def __init__(self, response_dict: dict | None = None, raises_exception: bool = False):
        self.response_dict = response_dict or {}
        self.raises_exception = raises_exception
        self.call_count = 0
        self.last_prompt = None

    async def complete_json(self, prompt: str) -> dict:
        """Mock implementation of complete_json."""
        self.call_count += 1
        self.last_prompt = prompt
        if self.raises_exception:
            raise RuntimeError("LLM provider error")
        return self.response_dict


@pytest.mark.asyncio
async def test_phonetics_inference_valid_gemini_response() -> None:
    """Test: Valid Gemini JSON response → entries parsed correctly."""
    provider = MockLLMProvider(
        {
            "entries": [
                {
                    "term": "魔法",
                    "phoneme": "mɔː.fɑː",
                    "language_code": "zh",
                    "confidence": 0.95,
                },
                {
                    "term": "Ye Qing",
                    "phoneme": "jeː tɕʰɪŋ",
                    "language_code": "zh",
                    "confidence": 0.85,
                },
            ]
        }
    )

    result = await infer_pronunciations(
        segment_text="The great cultivator Ye Qing mastered 魔法 (magic).",
        characters=["Ye Qing"],
        origin_language="zh",
        llm_provider=provider,
    )

    assert len(result) == 2
    assert result[0]["term"] == "魔法"
    assert result[0]["phoneme"] == "mɔː.fɑː"
    assert result[0]["language_code"] == "zh"
    assert result[1]["term"] == "Ye Qing"
    assert result[1]["phoneme"] == "jeː tɕʰɪŋ"


@pytest.mark.asyncio
async def test_phonetics_inference_malformed_json_returns_empty() -> None:
    """Test: Malformed JSON → empty list returned (graceful fallback)."""
    provider = MockLLMProvider(
        {
            "entries": "not_a_list",  # Invalid: should be a list
        }
    )

    result = await infer_pronunciations(
        segment_text="Some text",
        llm_provider=provider,
    )

    # Should gracefully handle the malformed response and return empty
    assert result == []


@pytest.mark.asyncio
async def test_phonetics_inference_filters_by_confidence() -> None:
    """Test: Filtering by confidence ≥ 0.5 works."""
    provider = MockLLMProvider(
        {
            "entries": [
                {
                    "term": "high_confidence",
                    "phoneme": "haɪ",
                    "language_code": "en",
                    "confidence": 0.95,
                },
                {
                    "term": "medium_confidence",
                    "phoneme": "med",
                    "language_code": "en",
                    "confidence": 0.5,
                },
                {
                    "term": "low_confidence",
                    "phoneme": "loʊ",
                    "language_code": "en",
                    "confidence": 0.3,
                },
            ]
        }
    )

    result = await infer_pronunciations(
        segment_text="Various confidence levels.",
        llm_provider=provider,
    )

    # Should include entries with confidence >= 0.5, exclude < 0.5
    assert len(result) == 2
    assert result[0]["term"] == "high_confidence"
    assert result[1]["term"] == "medium_confidence"
    assert not any(e["term"] == "low_confidence" for e in result)


@pytest.mark.asyncio
async def test_phonetics_inference_logging_captures_steps(caplog) -> None:
    """Test: Logging captures all inference steps."""
    provider = MockLLMProvider(
        {
            "entries": [
                {
                    "term": "test_term",
                    "phoneme": "tɛst",
                    "language_code": "en",
                    "confidence": 0.8,
                }
            ]
        }
    )

    with caplog.at_level(logging.INFO):
        result = await infer_pronunciations(
            segment_text="Test segment.",
            characters=["TestChar"],
            origin_language="en",
            llm_provider=provider,
        )

    # Verify logging
    assert len(result) == 1
    log_messages = [record.message for record in caplog.records]
    assert any("inference_started" in msg for msg in log_messages)
    assert any("inference_complete" in msg for msg in log_messages)


@pytest.mark.asyncio
async def test_phonetics_inference_empty_segment_returns_empty() -> None:
    """Test: Text with no detectable terms → empty response."""
    provider = MockLLMProvider({"entries": []})

    result = await infer_pronunciations(
        segment_text="",
        llm_provider=provider,
    )

    assert result == []


@pytest.mark.asyncio
async def test_phonetics_inference_none_provider_returns_empty() -> None:
    """Test: None LLM provider → empty list returned."""
    result = await infer_pronunciations(
        segment_text="Some text with no provider",
        llm_provider=None,
    )

    assert result == []


@pytest.mark.asyncio
async def test_phonetics_inference_llm_provider_error_handling() -> None:
    """Test: LLM provider raises exception → graceful fallback."""
    provider = MockLLMProvider(raises_exception=True)

    result = await infer_pronunciations(
        segment_text="Text when provider fails",
        llm_provider=provider,
    )

    assert result == []


@pytest.mark.asyncio
async def test_phonetics_inference_pydantic_response_parsing() -> None:
    """Test: Proper Pydantic model validation."""
    provider = MockLLMProvider(
        {
            "entries": [
                {
                    "term": "cultivate",
                    "phoneme": "kʌl.tɪ.veɪt",
                    "language_code": "en",
                    "confidence": 0.9,
                },
                {
                    "term": "修仙",
                    "phoneme": "ʂjoʊ̯.ɕjæn",
                    "language_code": "zh",
                    # confidence defaults to 0.8 if not provided
                },
            ]
        }
    )

    result = await infer_pronunciations(
        segment_text="Cultivating 修仙 techniques.",
        llm_provider=provider,
    )

    assert len(result) == 2
    assert result[1]["term"] == "修仙"


@pytest.mark.asyncio
async def test_phonetics_inference_mixed_confidence_filtering() -> None:
    """Test: Complex filtering scenario with boundary cases."""
    provider = MockLLMProvider(
        {
            "entries": [
                {"term": "a", "phoneme": "eɪ", "language_code": None, "confidence": 0.5},
                {"term": "b", "phoneme": "biː", "language_code": None, "confidence": 0.49},
                {"term": "c", "phoneme": "siː", "language_code": None, "confidence": 0.51},
            ]
        }
    )

    result = await infer_pronunciations(
        segment_text="a b c",
        llm_provider=provider,
    )

    # Should include 0.5 and 0.51, exclude 0.49
    assert len(result) == 2
    terms = {e["term"] for e in result}
    assert terms == {"a", "c"}


@pytest.mark.asyncio
async def test_phonetics_inference_respects_character_names() -> None:
    """Test: Character names are passed to prompt correctly."""
    provider = MockLLMProvider({"entries": []})

    characters = ["Ye Qing", "Lin Mei", "Master Chen"]
    await infer_pronunciations(
        segment_text="Sample text",
        characters=characters,
        llm_provider=provider,
    )

    # Verify the prompt included character names
    assert provider.last_prompt is not None
    prompt = provider.last_prompt
    for char in characters:
        assert char in prompt


@pytest.mark.asyncio
async def test_phonetics_inference_segment_text_truncation() -> None:
    """Test: Long segment text is truncated to avoid token overflow."""
    long_text = "x" * 2000  # Create very long text (exceeds 1000 char limit)
    provider = MockLLMProvider({"entries": []})

    await infer_pronunciations(
        segment_text=long_text,
        llm_provider=provider,
    )

    # Verify text was truncated in prompt
    assert provider.last_prompt is not None
    # The prompt should contain only first 1000 chars of segment
    assert len(long_text[:1000]) == 1000
    assert long_text[:1000] in provider.last_prompt


@pytest.mark.asyncio
async def test_phonetics_inference_all_fields_preserved() -> None:
    """Test: All response fields are preserved in output."""
    provider = MockLLMProvider(
        {
            "entries": [
                {
                    "term": "complex_term",
                    "phoneme": "kɑm.plɛks",
                    "language_code": "en",
                    "confidence": 0.92,
                }
            ]
        }
    )

    result = await infer_pronunciations(
        segment_text="Complex term here",
        llm_provider=provider,
    )

    assert len(result) == 1
    entry = result[0]
    assert entry["term"] == "complex_term"
    assert entry["phoneme"] == "kɑm.plɛks"
    assert entry["language_code"] == "en"
    # Confidence is used for filtering but shouldn't appear in output dict
    assert "confidence" not in entry


@pytest.mark.asyncio
async def test_phonetics_inference_entry_count_logging() -> None:
    """Test: Entry count before/after filtering is logged."""
    provider = MockLLMProvider(
        {
            "entries": [
                {"term": "a", "phoneme": "eɪ", "confidence": 0.95},
                {"term": "b", "phoneme": "biː", "confidence": 0.3},
                {"term": "c", "phoneme": "siː", "confidence": 0.8},
            ]
        }
    )

    # The service logs filtering info
    result = await infer_pronunciations(
        segment_text="Test",
        llm_provider=provider,
    )
    # Only 2 entries should pass the confidence >= 0.5 filter
    assert len(result) == 2
    assert result[0]["term"] == "a"
    assert result[1]["term"] == "c"
    # 3 total, 2 filtered (b removed due to low confidence)
    assert len(result) == 2
