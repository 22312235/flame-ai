
def chunk_documents(
    pages: list[dict],
    chunk_size: int = 1200,
    overlap: int = 200
) -> list[dict]:

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    chunks = []

    for page in pages:
        text = page["text"]
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Avoid splitting words when possible.
            if end < len(text):
                boundary = text.rfind(" ", start + chunk_size // 2, end)

                if boundary > start:
                    end = boundary

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": len(chunks),
                    "source": page["source"],
                    "page_number": page["page_number"],
                    "text": chunk_text
                })

            if end >= len(text):
                break

            start = end - overlap

    return chunks
