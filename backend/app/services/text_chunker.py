from __future__ import annotations

import re


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _split_large_paragraph(paragraph: str, max_words: int) -> list[str]:
    # First try sentence-level splitting to keep chunks readable.
    sentences = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    if not sentences:
        return []

    pieces: list[str] = []
    current: list[str] = []
    current_words = 0

    for sentence in sentences:
        sentence_words = _word_count(sentence)
        if sentence_words > max_words:
            words = sentence.split()
            for start in range(0, len(words), max_words):
                piece = " ".join(words[start : start + max_words]).strip()
                if piece:
                    pieces.append(piece)
            continue

        if current and current_words + sentence_words > max_words:
            pieces.append(" ".join(current).strip())
            current = [sentence]
            current_words = sentence_words
            continue

        current.append(sentence)
        current_words += sentence_words

    if current:
        pieces.append(" ".join(current).strip())

    return [piece for piece in pieces if piece]


def chunk_text(text: str, target_words: int = 500, max_words: int = 650) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    raw_paragraphs = re.split(r"\n\s*\n+", normalized)
    paragraphs = [paragraph.strip() for paragraph in raw_paragraphs if paragraph.strip()]

    if len(paragraphs) <= 1:
        # Fallback for normalized chapter text with no paragraph breaks.
        paragraphs = _split_large_paragraph(normalized, max_words)

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for paragraph in paragraphs:
        paragraph_words = _word_count(paragraph)

        if paragraph_words > max_words:
            for piece in _split_large_paragraph(paragraph, max_words):
                piece_words = _word_count(piece)
                if current and current_words + piece_words > target_words:
                    chunks.append("\n\n".join(current).strip())
                    current = []
                    current_words = 0

                current.append(piece)
                current_words += piece_words

                if current_words >= target_words:
                    chunks.append("\n\n".join(current).strip())
                    current = []
                    current_words = 0
            continue

        if current and current_words + paragraph_words > target_words:
            chunks.append("\n\n".join(current).strip())
            current = [paragraph]
            current_words = paragraph_words
            continue

        current.append(paragraph)
        current_words += paragraph_words

    if current:
        chunks.append("\n\n".join(current).strip())

    return [chunk for chunk in chunks if chunk]
