import pytest

from app.models.enums import SegmentType
from app.services.attribution import _build_prompt, attribute_chunk


class _FakeProvider:
    def __init__(self, payload: dict | None = None, raises: bool = False) -> None:
        self._payload = payload or {}
        self._raises = raises

    async def complete_json(self, prompt: str) -> dict:
        if self._raises:
            raise RuntimeError("provider error")
        return self._payload


@pytest.mark.asyncio
async def test_attribute_chunk_uses_payload_items() -> None:
    provider = _FakeProvider(
        {
            "items": [
                {
                    "text": '"What are you doing?"',
                    "type": "dialogue",
                    "character": "Lin Mei",
                    "confidence": 0.91,
                }
            ]
        }
    )

    result = await attribute_chunk('"What are you doing?"', provider)

    assert len(result) == 1
    assert result[0].type == SegmentType.DIALOGUE
    assert result[0].character == "Lin Mei"
    assert result[0].confidence == pytest.approx(0.91)


@pytest.mark.asyncio
async def test_attribute_chunk_falls_back_on_provider_error() -> None:
    provider = _FakeProvider(raises=True)

    result = await attribute_chunk(
        "\"Hello.\" I looked around in confusion. 'Umm... what?'", provider
    )

    assert len(result) >= 1
    assert any(segment.type == SegmentType.DIALOGUE for segment in result)
    assert any(segment.type == SegmentType.NARRATION for segment in result)
    assert result[0].character is None
    assert all(segment.confidence > 0.0 for segment in result)


@pytest.mark.asyncio
async def test_short_single_quoted_exclamation_is_high_confidence_thought() -> None:
    provider = _FakeProvider(raises=True)

    result = await attribute_chunk("I froze. 'Umm, what?'", provider)

    thought_segments = [segment for segment in result if segment.type == SegmentType.THOUGHT]
    assert thought_segments
    assert any(segment.confidence >= 0.65 for segment in thought_segments)


@pytest.mark.asyncio
async def test_long_single_quoted_block_is_dialogue() -> None:
    provider = _FakeProvider(raises=True)
    text = (
        "She read from the transcript: "
        "'We are requesting immediate support for the eastern platform because visibility has dropped "
        "and several passengers are reporting severe nausea and auditory distortion.'"
    )

    result = await attribute_chunk(text, provider)

    assert any(segment.type == SegmentType.DIALOGUE for segment in result)


@pytest.mark.asyncio
async def test_contractions_do_not_split_into_broken_single_word_quote() -> None:
    provider = _FakeProvider(raises=True)
    text = (
        "It's the department that's no different to a suicide squad. "
        "Like the red-shirt crew members in a certain sci-fi drama. "
        "They rush in at the slightest excuse to 'explore paranormal phenomena' and get chewed up."
    )

    result = await attribute_chunk(text, provider)

    assert not any(segment.text in {"'It'", "‘It’"} for segment in result)
    assert any("'explore paranormal phenomena'" in segment.text for segment in result)


@pytest.mark.asyncio
async def test_fragmented_quoted_dialogue_is_merged() -> None:
    provider = _FakeProvider(
        {
            "items": [
                {"text": '"Wow!', "type": "narration", "character": None, "confidence": 0.25},
                {
                    "text": "An employee ID from the Field Exploration Team!",
                    "type": "narration",
                    "character": None,
                    "confidence": 0.25,
                },
                {
                    "text": "I'm really looking forward to seeing what kind of adventures Employee Kim Soleum will have in the <Dark Exploration Records> universe!\"",
                    "type": "narration",
                    "character": None,
                    "confidence": 0.25,
                },
            ]
        }
    )

    result = await attribute_chunk(
        '"Wow! An employee ID from the Field Exploration Team! I\'m really looking forward to seeing what kind of adventures Employee Kim Soleum will have in the <Dark Exploration Records> universe!"',
        provider,
    )

    assert len(result) == 1
    assert result[0].type == SegmentType.DIALOGUE
    assert result[0].text.startswith('"Wow!')
    assert result[0].text.endswith('!"')


@pytest.mark.asyncio
async def test_missing_middle_span_is_recovered_by_coverage_repair() -> None:
    provider = _FakeProvider(
        {
            "items": [
                {
                    "text": '"Hello there."',
                    "type": "dialogue",
                    "character": "Mina",
                    "confidence": 0.9,
                },
                {"text": "I turned.", "type": "narration", "character": None, "confidence": 0.8},
            ]
        }
    )

    text = '"Hello there." Mina said quietly. I turned.'
    result = await attribute_chunk(text, provider)

    assert any(segment.text == " Mina said quietly. " for segment in result)
    assert any(segment.text == '"Hello there."' for segment in result)
    assert any(segment.text == "I turned." for segment in result)


def test_prompt_requires_full_coverage_and_exact_substrings() -> None:
    prompt = _build_prompt("input")
    assert "Coverage is mandatory" in prompt
    assert "Copy exact substrings from input text only" in prompt


@pytest.mark.asyncio
async def test_apostrophe_split_is_stitched_back_to_source_span() -> None:
    provider = _FakeProvider(
        {
            "items": [
                {"text": "‘Let’", "type": "thought", "character": None, "confidence": 0.7},
                {"text": "s see how this plays out.’", "type": "thought", "character": None, "confidence": 0.7},
            ]
        }
    )
    text = "‘Let’s see how this plays out.’"
    result = await attribute_chunk(text, provider)

    assert len(result) == 1
    assert result[0].text == "‘Let’s see how this plays out.’"
    assert result[0].type == SegmentType.THOUGHT


@pytest.mark.asyncio
async def test_adjacent_wrapped_quote_runs_are_split_before_alignment() -> None:
    provider = _FakeProvider(
        {
            "items": [
                {
                    "text": "“Type-A must be referring to… blood type, right?” “Yes…”",
                    "type": "dialogue",
                    "character": None,
                    "confidence": 0.8,
                }
            ]
        }
    )
    text = "“Type-A must be referring to… blood type, right?” “Yes…”"
    result = await attribute_chunk(text, provider)

    assert len(result) == 2
    assert result[0].text == "“Type-A must be referring to… blood type, right?”"
    assert result[0].type == SegmentType.DIALOGUE
    assert result[1].text == "“Yes…”"
    assert result[1].type == SegmentType.DIALOGUE
