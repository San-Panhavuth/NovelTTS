from app.services.text_chunker import chunk_text


def _words(count: int) -> str:
    return " ".join(f"w{i}" for i in range(count))


def test_chunk_text_groups_paragraphs_around_target() -> None:
    paragraph_a = _words(220)
    paragraph_b = _words(210)
    paragraph_c = _words(180)
    text = f"{paragraph_a}\n\n{paragraph_b}\n\n{paragraph_c}"

    chunks = chunk_text(text, target_words=400, max_words=650)

    assert len(chunks) == 2
    assert paragraph_a in chunks[0]
    assert paragraph_b in chunks[1] or paragraph_b in chunks[0]


def test_chunk_text_splits_large_block_without_paragraphs() -> None:
    text = ". ".join([_words(120) for _ in range(8)]) + "."

    chunks = chunk_text(text, target_words=500, max_words=300)

    assert len(chunks) >= 2
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk.split()) <= 650 for chunk in chunks)
