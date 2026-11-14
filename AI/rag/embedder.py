
import ollama


def embed_chunks(
    chunks: list[dict],
    model: str = "nomic-embed-text"
) -> list[dict]:

    if not chunks:
        return []

    texts = [chunk["text"] for chunk in chunks]

    response = ollama.embed(
        model=model,
        input=texts
    )

    embeddings = response["embeddings"]

    if len(embeddings) != len(chunks):
        raise ValueError("Embedding count does not match chunk count.")

    embedded_chunks = []

    for chunk, embedding in zip(chunks, embeddings):
        embedded_chunks.append({
            **chunk,
            "embedding": embedding
        })

    return embedded_chunks
