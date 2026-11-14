
import math
import ollama


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if len(vector_a) != len(vector_b):
        raise ValueError("Vectors must have the same dimensions.")

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def retrieve_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 3,
    model: str = "nomic-embed-text"
) -> list[dict]:

    if not query.strip():
        raise ValueError("Query cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    if not chunks:
        return []

    response = ollama.embed(
        model=model,
        input=query
    )

    query_embedding = response["embeddings"][0]

    results = []

    for chunk in chunks:
        score = cosine_similarity(
            query_embedding,
            chunk["embedding"]
        )

        results.append({
            **chunk,
            "similarity": score
        })

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    return results[:top_k]
