"""Splits article text into paragraph-respecting chunks for embedding."""

DEFAULT_CHUNK_SIZE = 1200


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[str]:
    """Greedily packs paragraphs into chunks up to chunk_size.

    Paragraph-respecting rather than a character-level sliding window, so
    chunks don't cut mid-word. Each chunk stays at or under chunk_size
    except for a single paragraph that's longer than chunk_size on its own,
    which gets hard-split.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append("\n\n".join(current))
                current, current_len = [], 0
            for start in range(0, len(paragraph), chunk_size):
                chunks.append(paragraph[start : start + chunk_size])
            continue

        added_len = len(paragraph) + (2 if current else 0)
        if current and current_len + added_len > chunk_size:
            chunks.append("\n\n".join(current))
            current, current_len = [paragraph], len(paragraph)
        else:
            current.append(paragraph)
            current_len += added_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks
