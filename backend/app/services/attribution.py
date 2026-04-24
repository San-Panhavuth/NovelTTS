from __future__ import annotations

from dataclasses import dataclass
import os
import re

from app.models.enums import SegmentType
from app.providers.llm.base import LLMProvider

_VALID_TYPES = {
    SegmentType.NARRATION.value,
    SegmentType.DIALOGUE.value,
    SegmentType.THOUGHT.value,
}
_THOUGHT_CUES = (
    "i thought",
    "i wondered",
    "inwardly",
    "to myself",
    "i had no idea",
)
_GENERIC_FALLBACK_CONFIDENCE = 0.25
_QUOTED_DIALOGUE_CONFIDENCE = 0.45
_SHORT_THOUGHT_CONFIDENCE = 0.65
_THOUGHT_CONFIDENCE = 0.4
_LONG_SINGLE_QUOTE_DIALOGUE_WORDS = 12
_SHORT_SINGLE_QUOTE_WORDS = 6
_SPEAKER_TAG_RE = re.compile(
    r"^(?P<name>[A-Z][A-Za-z0-9'\-]*(?:\s+[A-Z][A-Za-z0-9'\-]*){0,3})\s+"
    r"(?:said|shouted|asked|replied|called|cried|murmured|whispered|added|noted|muttered|answered)\b",
)


def _is_word_char(value: str) -> bool:
    return bool(value) and (value.isalnum() or value == "_")


def _find_quoted_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    index = 0

    while index < len(text):
        opener = text[index]
        if opener not in ('"', "“", "'", "‘"):
            index += 1
            continue

        if opener == "'":
            previous_char = text[index - 1] if index > 0 else ""
            next_char = text[index + 1] if index + 1 < len(text) else ""
            # Ignore apostrophes within words, e.g. It's / don't.
            if _is_word_char(previous_char) and _is_word_char(next_char):
                index += 1
                continue

        if opener == '"':
            acceptable_closers = ('"',)
        elif opener == "“":
            acceptable_closers = ("”",)
        elif opener == "'":
            acceptable_closers = ("'", "’")
        else:
            acceptable_closers = ("’",)

        cursor = index + 1
        while cursor < len(text):
            candidate = text[cursor]
            if candidate not in acceptable_closers:
                cursor += 1
                continue

            if opener in ("'", "‘"):
                previous_char = text[cursor - 1] if cursor > 0 else ""
                next_char = text[cursor + 1] if cursor + 1 < len(text) else ""
                # If quote-like mark is between two word chars, treat as apostrophe, not closing quote.
                if _is_word_char(previous_char) and _is_word_char(next_char):
                    cursor += 1
                    continue

            spans.append((index, cursor + 1))
            index = cursor + 1
            break
        else:
            index += 1

    return spans


@dataclass(frozen=True)
class AttributedSegment:
    text: str
    type: SegmentType
    character: str | None
    confidence: float


def _heuristic_type(text: str) -> SegmentType:
    lowered = text.lower()
    # For non-quoted spans, rely on lexical cues only.
    if any(cue in lowered for cue in _THOUGHT_CUES):
        return SegmentType.THOUGHT
    return SegmentType.NARRATION


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _strip_outer_quotes(text: str) -> str:
    stripped = text.strip()
    if (
        len(stripped) >= 2
        and stripped[0] in ('"', "“", "'", "‘")
        and stripped[-1]
        in (
            '"',
            "”",
            "'",
            "’",
        )
    ):
        return stripped[1:-1].strip()
    return stripped


def _is_short_exclamatory_single_quote(span: str) -> bool:
    stripped = span.strip()
    if not stripped or stripped[0] not in ("'", "‘"):
        return False

    inner = _strip_outer_quotes(stripped)
    if _word_count(inner) > _SHORT_SINGLE_QUOTE_WORDS:
        return False

    return any(token in inner for token in ("?", "!", "...", "…"))


def _append_merged(
    items: list[AttributedSegment],
    text: str,
    segment_type: SegmentType,
    confidence: float,
    merge_adjacent: bool = True,
) -> None:
    cleaned = text.strip()
    if not cleaned:
        return

    if merge_adjacent and items and items[-1].type == segment_type:
        previous = items[-1]
        items[-1] = AttributedSegment(
            text=f"{previous.text} {cleaned}".strip(),
            type=previous.type,
            character=None,
            confidence=min(previous.confidence, confidence),
        )
        return

    items.append(
        AttributedSegment(
            text=cleaned,
            type=segment_type,
            character=None,
            confidence=confidence,
        )
    )


def _classify_quoted_span(span: str) -> SegmentType:
    stripped = span.strip()
    if not stripped:
        return SegmentType.NARRATION
    if stripped[0] in ('"', "“"):
        return SegmentType.DIALOGUE
    if stripped[0] in ("'", "‘"):
        if _is_short_exclamatory_single_quote(stripped):
            return SegmentType.THOUGHT
        if _word_count(_strip_outer_quotes(stripped)) >= _LONG_SINGLE_QUOTE_DIALOGUE_WORDS:
            return SegmentType.DIALOGUE
        return SegmentType.THOUGHT
    return SegmentType.NARRATION


def _quoted_confidence(span: str, segment_type: SegmentType) -> float:
    if segment_type == SegmentType.THOUGHT:
        if _is_short_exclamatory_single_quote(span):
            return _SHORT_THOUGHT_CONFIDENCE
        return _THOUGHT_CONFIDENCE
    if segment_type == SegmentType.DIALOGUE:
        return _QUOTED_DIALOGUE_CONFIDENCE
    return _GENERIC_FALLBACK_CONFIDENCE


def _heuristic_split(source_text: str) -> list[AttributedSegment]:
    sentences = [
        part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", source_text) if part.strip()
    ]
    if not sentences:
        return [
            AttributedSegment(
                text=source_text,
                type=SegmentType.NARRATION,
                character=None,
                confidence=0.0,
            )
        ]

    raw_segments: list[AttributedSegment] = []
    for sentence in sentences:
        last = 0
        found_quoted = False
        for span_start, span_end in _find_quoted_spans(sentence):
            found_quoted = True
            before = sentence[last:span_start].strip()
            if before:
                _append_merged(
                    raw_segments,
                    before,
                    _heuristic_type(before),
                    _GENERIC_FALLBACK_CONFIDENCE,
                    merge_adjacent=False,
                )

            quoted = sentence[span_start:span_end].strip()
            quoted_type = _classify_quoted_span(quoted)
            _append_merged(
                raw_segments,
                quoted,
                quoted_type,
                _quoted_confidence(quoted, quoted_type),
                merge_adjacent=False,
            )
            last = span_end

        after = sentence[last:].strip()
        if after:
            _append_merged(
                raw_segments,
                after,
                _heuristic_type(after),
                _GENERIC_FALLBACK_CONFIDENCE,
                merge_adjacent=False,
            )

        if not found_quoted and not after:
            _append_merged(
                raw_segments,
                sentence,
                _heuristic_type(sentence),
                _GENERIC_FALLBACK_CONFIDENCE,
                merge_adjacent=False,
            )

    return (
        raw_segments
        if raw_segments
        else [
            AttributedSegment(
                text=source_text,
                type=SegmentType.NARRATION,
                character=None,
                confidence=0.0,
            )
        ]
    )


def _build_prompt(text: str) -> str:
    return (
        "You are an assistant for novel line attribution. "
        "Return JSON only, no markdown. "
        'Schema: {"items": [{"text": string, "type": "narration"|"dialogue"|"thought", '
        '"character": string|null, "confidence": number}]}. '
        "Confidence must be between 0 and 1. "
        "Coverage is mandatory: every non-whitespace token from input must appear in exactly one output item. "
        "Copy exact substrings from input text only; never paraphrase, normalize, or rewrite text. "
        "Prefer maximal contiguous spans and avoid micro-fragmentation around commas or sentence punctuation. "
        "If uncertain, keep larger contiguous spans rather than splitting. "
        "Keep text spans as direct excerpts from input. "
        "Do not split a single quoted line into multiple items. "
        "If a line of dialogue contains multiple sentences or clauses inside the same opening and closing quotes, "
        "return it as one dialogue item. "
        "If quoted speech is followed by a speaker tag like 'Mina shouted.' or 'Mina said.', attach the speaker name "
        "to the dialogue item in the character field and keep the tag itself as narration only if it is separate. "
        "Prefer maximal contiguous spans with the same meaning; do not fragment quotes at sentence punctuation.\n\n"
        f"Input:\n{text}"
    )


def _build_label_prompt(source_text: str, segments: list[AttributedSegment], mode: str) -> str:
    payload_items = [{"idx": idx, "text": segment.text} for idx, segment in enumerate(segments)]
    guidance = (
        "Use provided idx values. Confidence must be between 0 and 1. "
        "Character should be null when unknown."
    )
    if mode == "preseg_label_v2":
        guidance = (
            "Use provided idx values. Confidence must be between 0 and 1. "
            "Character should be null when unknown. "
            "If a span starts and ends with quote marks, prefer dialogue unless it is clearly internal monologue. "
            "Treat first-person internal reasoning without spoken quotes as thought."
        )
    return (
        "You are labeling pre-segmented novel spans. "
        "Do not rewrite span text. Only return JSON with labels. "
        'Schema: {"items":[{"idx": number, "type":"narration"|"dialogue"|"thought", '
        '"character": string|null, "confidence": number}]}. '
        f"{guidance}\n\n"
        f"Source:\n{source_text}\n\nSegments:\n{payload_items}"
    )


def _normalize_type(raw_type: str | None) -> SegmentType:
    value = (raw_type or "").strip().lower()
    if value not in _VALID_TYPES:
        return SegmentType.NARRATION
    return SegmentType(value)


def _normalize_confidence(raw_confidence: object) -> float:
    try:
        value = float(raw_confidence)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


def _merge_adjacent_same_label(segments: list[AttributedSegment]) -> list[AttributedSegment]:
    if not segments:
        return []
    merged: list[AttributedSegment] = [segments[0]]
    for segment in segments[1:]:
        previous = merged[-1]
        if previous.type == segment.type and previous.character == segment.character:
            merged[-1] = AttributedSegment(
                text=f"{previous.text}{segment.text}",
                type=previous.type,
                character=previous.character,
                confidence=min(previous.confidence, segment.confidence),
            )
            continue
        merged.append(segment)
    return merged


_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?…])\s+")


def _split_text_preserving_quotes(text: str) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []

    if _has_wrapped_quote(normalized):
        return [normalized]

    segments: list[str] = []
    for sentence in _SENTENCE_BOUNDARY_RE.split(normalized):
        sentence = sentence.strip()
        if not sentence:
            continue

        last = 0
        found_quote = False
        for span_start, span_end in _find_quoted_spans(sentence):
            found_quote = True
            before = sentence[last:span_start].strip()
            if before:
                segments.append(before)
            segments.append(sentence[span_start:span_end].strip())
            last = span_end

        after = sentence[last:].strip()
        if after:
            segments.append(after)
        elif not found_quote:
            segments.append(sentence)

    return [segment for segment in segments if segment]


def _has_wrapped_quote(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 2:
        return False
    opening = stripped[0]
    closing = stripped[-1]
    return (
        (opening == '"' and closing == '"')
        or (opening == "“" and closing == "”")
        or (opening in ("'", "‘") and closing in ("'", "’"))
    )


def _coalesce_fragmented_quotes(segments: list[AttributedSegment]) -> list[AttributedSegment]:
    if not segments:
        return []

    merged: list[AttributedSegment] = []
    index = 0
    while index < len(segments):
        segment = segments[index]
        if _has_wrapped_quote(segment.text):
            merged.append(segment)
            index += 1
            continue

        if segment.text.strip().startswith(('"', "“", "'", "‘")):
            quote_parts = [segment]
            quote_text = segment.text.strip()
            opening = quote_text[0]
            closing_chars = {
                '"': ('"',),
                "“": ("”",),
                "'": ("'", "’"),
                "‘": ("’",),
            }[opening]

            cursor = index + 1
            while cursor < len(segments):
                quote_parts.append(segments[cursor])
                quote_text = " ".join(part.text.strip() for part in quote_parts).strip()
                if quote_text.endswith(closing_chars):
                    merged.append(
                        AttributedSegment(
                            text=quote_text,
                            type=_classify_quoted_span(quote_text),
                            character=quote_parts[0].character,
                            confidence=min(part.confidence for part in quote_parts),
                        )
                    )
                    index = cursor + 1
                    break
                cursor += 1
            else:
                merged.append(segment)
                index += 1
            continue

        merged.append(segment)
        index += 1

    return merged


def _merge_open_quote_runs(segments: list[AttributedSegment]) -> list[AttributedSegment]:
    if not segments:
        return []

    merged: list[AttributedSegment] = []
    index = 0
    while index < len(segments):
        current = segments[index]
        stripped = current.text.strip()

        if stripped and stripped[0] in ('"', "“", "'", "‘") and not _has_wrapped_quote(stripped):
            opening = stripped[0]
            closing_chars = {
                '"': ('"',),
                "“": ("”",),
                "'": ("'", "’"),
                "‘": ("’",),
            }[opening]

            parts = [current]
            cursor = index + 1
            while cursor < len(segments):
                parts.append(segments[cursor])
                combined_text = " ".join(part.text.strip() for part in parts).strip()
                if combined_text.endswith(closing_chars):
                    merged.append(
                        AttributedSegment(
                            text=combined_text,
                            type=_classify_quoted_span(combined_text),
                            character=parts[0].character,
                            confidence=min(part.confidence for part in parts),
                        )
                    )
                    index = cursor + 1
                    break
                cursor += 1
            else:
                merged.append(current)
                index += 1
            continue

        merged.append(current)
        index += 1

    return merged


def _infer_character_from_tag(text: str) -> str | None:
    stripped = text.strip().strip('"').strip("“").strip("”").strip("'").strip("‘").strip("’")
    match = _SPEAKER_TAG_RE.match(stripped)
    if not match:
        return None
    return match.group("name").strip()


def _finalize_segments(segments: list[AttributedSegment]) -> list[AttributedSegment]:
    finalized = _merge_open_quote_runs(segments)

    for index, segment in enumerate(finalized):
        if segment.type != SegmentType.DIALOGUE or segment.character:
            continue

        next_segment = finalized[index + 1] if index + 1 < len(finalized) else None
        previous_segment = finalized[index - 1] if index > 0 else None

        for candidate in (candidate for candidate in (next_segment, previous_segment) if candidate):
            inferred = _infer_character_from_tag(candidate.text)
            if inferred:
                finalized[index] = AttributedSegment(
                    text=segment.text,
                    type=segment.type,
                    character=inferred,
                    confidence=segment.confidence,
                )
                break

    return finalized


def _split_predicted_segment(segment: AttributedSegment) -> list[AttributedSegment]:
    text_parts = _split_text_preserving_quotes(segment.text)
    if len(text_parts) <= 1:
        return [segment]

    split_segments: list[AttributedSegment] = []
    for part in text_parts:
        if part.startswith(('"', "“")) or (
            part.startswith(("'", "‘")) and segment.type != SegmentType.NARRATION
        ):
            part_type = _classify_quoted_span(part)
        else:
            part_type = (
                segment.type if segment.type != SegmentType.NARRATION else _heuristic_type(part)
            )

        confidence = segment.confidence
        if part_type == SegmentType.THOUGHT:
            confidence = max(confidence, _SHORT_THOUGHT_CONFIDENCE)
        elif part_type == SegmentType.DIALOGUE:
            confidence = max(confidence, _QUOTED_DIALOGUE_CONFIDENCE)

        split_segments.append(
            AttributedSegment(
                text=part,
                type=part_type,
                character=segment.character if part_type == segment.type else None,
                confidence=confidence,
            )
        )

    return _coalesce_fragmented_quotes(split_segments)


def _split_adjacent_wrapped_quotes(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    parts: list[str] = []
    remaining = stripped
    while remaining:
        if not remaining.startswith(('"', "“", "'", "‘")):
            break
        quote_spans = _find_quoted_spans(remaining)
        if not quote_spans:
            break
        first_start, first_end = quote_spans[0]
        if first_start != 0:
            break

        parts.append(remaining[first_start:first_end].strip())
        tail = remaining[first_end:].lstrip()
        if not tail.startswith(('"', "“", "'", "‘")):
            if tail:
                parts[-1] = f"{parts[-1]} {tail}".strip()
            remaining = ""
            break
        remaining = tail

    if remaining:
        return [stripped]
    return [part for part in parts if part]


def _normalize_payload_segments(segments: list[AttributedSegment]) -> list[AttributedSegment]:
    if not segments:
        return []

    normalized: list[AttributedSegment] = []
    for segment in segments:
        text_parts = _split_adjacent_wrapped_quotes(segment.text)
        if len(text_parts) <= 1:
            normalized.append(segment)
            continue

        for part in text_parts:
            normalized.append(
                AttributedSegment(
                    text=part,
                    type=_classify_quoted_span(part),
                    character=segment.character,
                    confidence=segment.confidence,
                )
            )

    return normalized


def _canonicalize_for_search(text: str) -> tuple[str, list[int]]:
    canonical_chars: list[str] = []
    index_map: list[int] = []
    previous_space = False

    for index, char in enumerate(text):
        if char.isalnum():
            canonical_chars.append(char.lower())
            index_map.append(index)
            previous_space = False
            continue

        if char.isspace():
            if not previous_space:
                canonical_chars.append(" ")
                index_map.append(index)
                previous_space = True
            continue

    canonical = "".join(canonical_chars).strip()
    if not canonical:
        return "", [0]
    return canonical, index_map


def _canonical_cursor_from_raw(raw_map: list[int], raw_cursor: int) -> int:
    for index, raw_index in enumerate(raw_map):
        if raw_index >= raw_cursor:
            return index
    return len(raw_map)


def _find_span(raw_text: str, segment_text: str, start_at: int = 0) -> tuple[int, int] | None:
    cleaned = segment_text.strip()
    if not cleaned:
        return None

    parts = [re.escape(part) for part in re.split(r"\s+", cleaned) if part]
    if not parts:
        return None

    pattern = r"\s+".join(parts)
    match = re.search(pattern, raw_text[start_at:], flags=re.DOTALL)
    if match is None:
        raw_canon, raw_map = _canonicalize_for_search(raw_text)
        seg_canon, _ = _canonicalize_for_search(cleaned)
        canon_start = _canonical_cursor_from_raw(raw_map, start_at)
        canon_match = re.search(re.escape(seg_canon), raw_canon[canon_start:])
        if canon_match is None:
            return None

        canon_begin = canon_start + canon_match.start()
        canon_end = canon_start + canon_match.end()
        raw_begin = raw_map[canon_begin]
        raw_end = raw_map[min(canon_end - 1, len(raw_map) - 1)] + 1
        return raw_begin, raw_end

    return start_at + match.start(), start_at + match.end()


def _classify_gap_text(text: str) -> SegmentType:
    stripped = text.strip()
    if not stripped:
        return SegmentType.NARRATION
    if stripped[0] in ('"', "“", "'", "‘"):
        return _classify_quoted_span(stripped)
    return _heuristic_type(stripped)


def _is_apostrophe_connector(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return all(char in {"'", "’", "`", '"', "“", "”", "‘"} for char in stripped)


def _is_tight_apostrophe_boundary(previous_text: str, current_text: str) -> bool:
    previous = previous_text.rstrip()
    current = current_text.lstrip()
    if not previous or not current:
        return False

    apostrophes = {"'", "’", "`"}
    prev_last = previous[-1]
    curr_first = current[0]
    return (
        (prev_last in apostrophes and curr_first.isalpha())
        or (prev_last.isalpha() and curr_first in apostrophes)
    )


def _repair_source_coverage(
    source_text: str,
    segments: list[AttributedSegment],
) -> list[AttributedSegment]:
    repaired: list[AttributedSegment] = []
    cursor = 0

    for segment in segments:
        span = _find_span(source_text, segment.text, start_at=cursor)
        if span is None:
            continue

        start, end = span
        current_text = source_text[start:end]
        if (
            repaired
            and start == cursor
            and repaired[-1].type == segment.type
            and repaired[-1].character == segment.character
            and _is_tight_apostrophe_boundary(repaired[-1].text, current_text)
        ):
            previous = repaired[-1]
            repaired[-1] = AttributedSegment(
                text=f"{previous.text}{current_text}",
                type=previous.type,
                character=previous.character,
                confidence=min(previous.confidence, segment.confidence),
            )
            cursor = end
            continue

        if start > cursor:
            gap_text = source_text[cursor:start]
            if gap_text.strip():
                if (
                    repaired
                    and _is_apostrophe_connector(gap_text)
                    and repaired[-1].type == segment.type
                    and repaired[-1].character == segment.character
                ):
                    previous = repaired[-1]
                    repaired[-1] = AttributedSegment(
                        text=f"{previous.text}{gap_text}{current_text}",
                        type=previous.type,
                        character=previous.character,
                        confidence=min(previous.confidence, segment.confidence),
                    )
                    cursor = end
                    continue

                if _is_apostrophe_connector(gap_text):
                    current_text = f"{gap_text}{current_text}"
                else:
                    repaired.append(
                        AttributedSegment(
                            text=gap_text,
                            type=_classify_gap_text(gap_text),
                            character=None,
                            confidence=_GENERIC_FALLBACK_CONFIDENCE,
                        )
                    )

        repaired.append(
            AttributedSegment(
                text=current_text,
                type=segment.type,
                character=segment.character,
                confidence=segment.confidence,
            )
        )
        cursor = end

    if cursor < len(source_text):
        gap_text = source_text[cursor:]
        if gap_text.strip():
            repaired.append(
                AttributedSegment(
                    text=gap_text,
                    type=_classify_gap_text(gap_text),
                    character=None,
                    confidence=_GENERIC_FALLBACK_CONFIDENCE,
                )
            )

    return repaired or _heuristic_split(source_text)


def _from_payload(payload: dict, source_text: str) -> list[AttributedSegment]:
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        return _heuristic_split(source_text)

    output: list[AttributedSegment] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue

        text = str(item.get("text", "")).strip()
        if not text:
            continue

        raw_character = item.get("character")
        character = str(raw_character).strip() if isinstance(raw_character, str) else None
        if character == "":
            character = None

        output.append(
            AttributedSegment(
                text=text,
                type=_normalize_type(item.get("type")),
                character=character,
                confidence=_normalize_confidence(item.get("confidence")),
            )
        )

    if output:
        output = _normalize_payload_segments(output)
        expanded: list[AttributedSegment] = []
        for segment in output:
            expanded.extend(_split_predicted_segment(segment))

        expanded = _finalize_segments(_repair_source_coverage(source_text, expanded))

        if (
            len(expanded) == 1
            and expanded[0].type == SegmentType.NARRATION
            and expanded[0].confidence <= 0.05
            and len(expanded[0].text) >= int(len(source_text) * 0.9)
        ):
            return _heuristic_split(source_text)
        return expanded

    return _heuristic_split(source_text)


def _extract_item_labels(payload: dict) -> tuple[dict[int, AttributedSegment], bool]:
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        return {}, False
    indexed: dict[int, AttributedSegment] = {}
    has_explicit_idx = False
    for auto_idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        raw_idx = item.get("idx")
        if raw_idx is None:
            idx = auto_idx
        else:
            has_explicit_idx = True
            try:
                idx = int(raw_idx)
            except (TypeError, ValueError):
                continue
        raw_character = item.get("character")
        character = str(raw_character).strip() if isinstance(raw_character, str) else None
        if character == "":
            character = None
        indexed[idx] = AttributedSegment(
            text="",
            type=_normalize_type(item.get("type")),
            character=character,
            confidence=_normalize_confidence(item.get("confidence")),
        )
    return indexed, has_explicit_idx


async def _attribute_with_presegmented_labels(
    text: str,
    provider: LLMProvider,
    mode: str,
) -> list[AttributedSegment]:
    base_segments = _heuristic_split(text)
    if not base_segments:
        return []

    prompt = _build_label_prompt(text, base_segments, mode=mode)
    try:
        payload = await provider.complete_json(prompt)
    except Exception:  # noqa: BLE001
        payload = {}

    labels, has_explicit_idx = _extract_item_labels(payload)
    if not has_explicit_idx:
        return []
    labeled: list[AttributedSegment] = []
    for idx, segment in enumerate(base_segments):
        label = labels.get(idx)
        if label is None:
            labeled.append(segment)
            continue
        labeled.append(
            AttributedSegment(
                text=segment.text,
                type=label.type,
                character=label.character,
                confidence=label.confidence,
            )
        )

    return _merge_adjacent_same_label(labeled)


def _get_attribution_experiment_mode() -> str:
    return os.getenv("ATTRIBUTION_EXPERIMENT", "hybrid_v1").strip().lower()


async def attribute_chunk(text: str, provider: LLMProvider) -> list[AttributedSegment]:
    mode = _get_attribution_experiment_mode()

    if mode in {"preseg_label_v1", "preseg_label_v2", "hybrid_v1"}:
        preseg_mode = "preseg_label_v2" if mode == "preseg_label_v2" else "preseg_label_v1"
        primary = await _attribute_with_presegmented_labels(text, provider, mode=preseg_mode)
        if primary:
            return _finalize_segments(primary)
        if mode in {"preseg_label_v1", "preseg_label_v2"}:
            return _finalize_segments(_heuristic_split(text))

    # Legacy fallback path kept as safety net.
    prompt = _build_prompt(text)
    try:
        payload = await provider.complete_json(prompt)
    except Exception:  # noqa: BLE001
        payload = {}
    return _finalize_segments(_from_payload(payload, source_text=text))
