def chunk_text(text: str, max_chars: int = 4000):
    chunks = []
    current = []

    for line in text.split("\n"):
        if sum(len(x) for x in current) + len(line) >= max_chars:
            chunks.append("\n".join(current))
            current = []
        current.append(line)

    if current:
        chunks.append("\n".join(current))

    return chunks
