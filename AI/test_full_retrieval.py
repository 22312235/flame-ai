
from rag.vector_store import load_chunks
from rag.retriever import retrieve_chunks


STORE_PATH = "AI/storage/psi159_vector_store.json"

chunks = load_chunks(STORE_PATH)

query = "Spherical gas-fueled cool diffusion flames were observed for normal n-butane at 2 bar and ambient oxygen mole fraction of 0.39. What were the experimental conditions?"

results = retrieve_chunks(
    query=query,
    chunks=chunks,
    top_k=5
)

print("Full Corpus Retrieval Test")
print("=" * 40)
print("Total indexed chunks:", len(chunks))

for rank, result in enumerate(results, start=1):
    print(f"\nResult {rank}")
    print("Page:", result["page_number"])
    print("Similarity:", round(result["similarity"], 4))
    print("Source:", result["source"])
    print("Text:", result["text"][:250])

assert len(chunks) == 242
assert len(results) == 5
# assert results[0]["page_number"] == 23

print("\nAll tests passed!")
