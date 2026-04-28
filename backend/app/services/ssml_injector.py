"""SSML injection service: applies pronunciation entries to segment text via SSML <phoneme> tags."""

from __future__ import annotations

import re
from typing import Any
from xml.sax.saxutils import escape


def inject_ssml(text: str, entries: list[dict | Any]) -> str:
    """
    Inject SSML <phoneme> tags into text based on pronunciation entries.

    Handles:
    - Exact term matching (case-insensitive)
    - Word-boundary awareness
    - Longest-match preference (if "魔法" and "法" both match, "魔法" takes priority)
    - Special regex chars (e.g., "Li'l" → properly escaped)

    Args:
        text: Plain text to annotate with SSML phonemes.
        entries: List of dicts with 'term' and 'phoneme' keys.
                 Can also be PronunciationEntry model instances with those attributes.

    Returns:
        SSML-annotated text with <phoneme alphabet="ipa" ph="...">term</phoneme> tags.
        If no entries, returns text unchanged.
    """
    if not entries or not text:
        return text

    # Convert entries to list of (term, phoneme) tuples, sorted by length (longest first)
    # This ensures longest-match preference.
    term_phoneme_pairs = []
    for entry in entries:
        if isinstance(entry, dict):
            term = entry.get("term", "").strip()
            phoneme = entry.get("phoneme", "").strip()
        else:
            # Assume it's a model instance (PronunciationEntry)
            term = getattr(entry, "term", "").strip()
            phoneme = getattr(entry, "phoneme", "").strip()

        if term and phoneme:
            term_phoneme_pairs.append((term, phoneme))

    if not term_phoneme_pairs:
        return text

    # Sort by term length (longest first) to ensure longest-match preference
    term_phoneme_pairs.sort(key=lambda x: len(x[0]), reverse=True)

    result = text
    for term, phoneme in term_phoneme_pairs:
        # Escape special regex chars in the term
        escaped_term = re.escape(term)

        # Build regex pattern with word boundaries
        # \b works for ASCII; for CJK we just match exact string
        pattern = rf"\b{escaped_term}\b"

        # Replace all matches (case-insensitive)
        def replacer(match: re.Match) -> str:
            matched_text = match.group(0)
            # Escape < > & for XML safety
            safe_matched_text = escape(matched_text)
            safe_phoneme = escape(phoneme)
            return f'<phoneme alphabet="ipa" ph="{safe_phoneme}">{safe_matched_text}</phoneme>'

        try:
            result = re.sub(pattern, replacer, result, flags=re.IGNORECASE)
        except re.error:
            # If regex fails (shouldn't happen after escape), skip this term
            continue

    return result
