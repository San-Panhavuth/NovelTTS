"""Phonetics inference service: extract non-English terms from novel text and infer IPA phonemes."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PhoneticsEntry(BaseModel):
    """A single term-phoneme pair inferred by the LLM."""

    term: str = Field(..., description="The term to be pronounced (e.g., '魔法', 'Ye Qing')")
    phoneme: str = Field(..., description="IPA phoneme string (e.g., 'mɔː.fɑː', 'jeː tɕʰɪŋ')")
    language_code: str | None = Field(
        default=None, description="Language code (e.g., 'zh', 'ko', 'ja', 'en')"
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0); only entries with confidence >= 0.5 are stored",
    )


class PhoneticsInferenceResponse(BaseModel):
    """Response from Gemini phonetics inference."""

    entries: list[PhoneticsEntry] = Field(default_factory=list)


# ────────────────────────────────────────────────────────────────────────────────
# Inference Prompt
# ────────────────────────────────────────────────────────────────────────────────

PHONETICS_INFERENCE_PROMPT_TEMPLATE = """You are an expert in linguistics and web novel translation.
Your task is to identify non-English terms in the provided novel segment that will be mispronounced by English TTS engines, and infer their correct pronunciations.

Focus on:
1. Character names (especially Chinese, Korean, Japanese names)
2. Cultivation/fantasy terms (e.g., 丹 "dan", 修仙 "xiu xian", 灵力 "ling li")
3. Place names and titles
4. Technical terms unique to the novel's world

For each identified term, provide the IPA phoneme that correctly represents its intended pronunciation.

NOVEL SEGMENT:
{segment_text}

CHARACTER NAMES IN THIS SEGMENT (if any): {character_names}
ORIGIN LANGUAGE (if known): {origin_language}

Return ONLY valid JSON (no markdown, no code blocks) with this exact structure:
{{
  "entries": [
    {{
      "term": "魔法",
      "phoneme": "mɔː.fɑː",
      "language_code": "zh",
      "confidence": 0.95
    }},
    {{
      "term": "Ye Qing",
      "phoneme": "jeː tɕʰɪŋ",
      "language_code": "zh",
      "confidence": 0.85
    }}
  ]
}}

Rules:
- Only include terms that will be mispronounced by English TTS (skip common English words).
- Use IPA (International Phonetic Alphabet) format for phonemes.
- Set confidence between 0.0-1.0; only include terms with confidence >= 0.5.
- Include at most 10-15 entries per segment (focus on high-impact terms).
- If no non-English terms are found, return {{"entries": []}}.
"""


async def infer_pronunciations(
    segment_text: str,
    characters: list[str] | None = None,
    origin_language: str | None = None,
    llm_provider: Any = None,
) -> list[dict]:
    """
    Infer phonetic pronunciations for non-English terms in a novel segment.

    Args:
        segment_text: The novel segment text to analyze.
        characters: List of character names that may appear in the segment.
        origin_language: Optional language code (e.g., 'zh', 'ko', 'ja') for hint.
        llm_provider: LLMProvider instance (must have `complete_json(prompt)` method).

    Returns:
        List of dicts with keys: term, phoneme, language_code, confidence.
        Returns empty list on LLM failure or parsing error.
    """
    if not llm_provider:
        logger.warning("infer_pronunciations: llm_provider is None; skipping inference")
        return []

    if not segment_text or not segment_text.strip():
        logger.debug("infer_pronunciations: segment_text is empty; returning []")
        return []

    logger.info(
        "inference_started",
        extra={
            "segment_length": len(segment_text),
            "num_characters": len(characters or []),
            "origin_language": origin_language,
        },
    )

    character_names_str = ", ".join(characters) if characters else "(none)"
    origin_language_str = origin_language or "(unknown)"

    prompt = PHONETICS_INFERENCE_PROMPT_TEMPLATE.format(
        segment_text=segment_text[:1000],  # Limit segment to 1000 chars to avoid token overflow
        character_names=character_names_str,
        origin_language=origin_language_str,
    )

    try:
        logger.debug("inference_prompt_sent")
        response_dict = await llm_provider.complete_json(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.exception("inference_llm_failed: %s", exc)
        return []

    try:
        parsed_response = PhoneticsInferenceResponse.model_validate(response_dict)
        logger.debug("inference_response_parsed", extra={"num_entries": len(parsed_response.entries)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("inference_response_validation_failed: %s", exc)
        return []

    # Filter by confidence >= 0.5
    filtered_entries = [
        entry
        for entry in parsed_response.entries
        if entry.confidence >= 0.5
    ]

    logger.info(
        "entries_filtered",
        extra={"num_before": len(parsed_response.entries), "num_after": len(filtered_entries)},
    )

    # Convert to dicts for storage
    result = [
        {
            "term": entry.term,
            "phoneme": entry.phoneme,
            "language_code": entry.language_code,
        }
        for entry in filtered_entries
    ]

    logger.info("inference_complete", extra={"final_entries": len(result)})
    return result
