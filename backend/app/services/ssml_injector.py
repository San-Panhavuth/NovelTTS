"""SSML injection service: applies pronunciation entries to segment text via SSML <phoneme> tags."""

from __future__ import annotations

import re
from typing import Any
from xml.sax.saxutils import escape


def _collect_term_replacements(entries: list[dict | Any]) -> list[tuple[str, str]]:
    """Normalize entries into (term, replacement) tuples sorted by longest term first."""
    term_replacements = []
    for entry in entries:
        if isinstance(entry, dict):
            term = entry.get("term", "").strip()
            replacement = entry.get("phoneme", "").strip()
        else:
            term = getattr(entry, "term", "").strip()
            replacement = getattr(entry, "phoneme", "").strip()

        if term and replacement:
            term_replacements.append((term, replacement))

    term_replacements.sort(key=lambda x: len(x[0]), reverse=True)
    return term_replacements


def _term_pattern(term: str) -> str:
    escaped_term = re.escape(term)
    return rf"\b{escaped_term}\b"


def apply_pronunciation_overrides(text: str, entries: list[dict | Any]) -> str:
    """
    Replace matched terms with their pronunciation override as plain text.

    Edge TTS does not support arbitrary custom SSML phoneme tags, so this helper is used
    to make pronunciation overrides still affect spoken output by substituting the text
    directly before synthesis.
    """
    if not entries or not text:
        return text

    result = text
    for term, replacement in _collect_term_replacements(entries):
        pattern = _term_pattern(term)
        try:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        except re.error:
            continue

    return result


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

    term_phoneme_pairs = _collect_term_replacements(entries)
    if not term_phoneme_pairs:
        return text

    result = text
    for term, phoneme in term_phoneme_pairs:
        pattern = _term_pattern(term)

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
