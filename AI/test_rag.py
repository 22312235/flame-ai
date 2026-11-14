
from rag.vector_store import load_chunks
from rag.retriever import retrieve_chunks
from rag.generator import generate_answer


STORE_PATH = "AI/storage/psi159_vector_store.json"

chunks = load_chunks(STORE_PATH)

# Test question: information that may not be available
# in the retrieved document evidence.
query = (
    "What was the exact carbon monoxide concentration "
    "measured during each n-butane flame experiment?"
)

print("Retrieving evidence...")

results = retrieve_chunks(
    query=query,
    chunks=chunks,
    top_k=5
)

print("Generating answer with Qwen...\n")

answer = generate_answer(
    query=query,
    retrieved_chunks=results
)

print("=" * 50)
print("FLAME AI ANSWER")
print("=" * 50)
print(answer)

print("\n" + "=" * 50)
print("RETRIEVED SOURCES")
print("=" * 50)

for result in results:
    print(
        f"Page {result['page_number']} | "
        f"Similarity: {result['similarity']:.4f}"
    )
