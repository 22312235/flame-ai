
from ingestion.pdf_loader import load_pdf_document
from rag.chunker import chunk_documents
from rag.embedder import embed_chunks
from rag.retriever import retrieve_chunks


pdf_path = r"C:\Users\User\Downloads\PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf"

pages = load_pdf_document(pdf_path)
chunks = chunk_documents(pages)

# Focus on pages containing the cool diffusion flame results.
relevant_chunks = [
    chunk for chunk in chunks
    if chunk["page_number"] in [23, 24]
]

embedded_chunks = embed_chunks(relevant_chunks)

query = "Under what conditions were spherical gas-fueled cool diffusion flames observed?"

results = retrieve_chunks(
    query=query,
    chunks=embedded_chunks,
    top_k=3
)

print("Semantic Retrieval Test")
print("=" * 40)

for index, result in enumerate(results, start=1):
    print(f"\nResult {index}")
    print("Page:", result["page_number"])
    print("Similarity:", round(result["similarity"], 4))
    print("Text:", result["text"][:300])

assert len(results) == min(3, len(embedded_chunks))
assert all(
    results[i]["similarity"] >= results[i + 1]["similarity"]
    for i in range(len(results) - 1)
)

print("\nAll tests passed!")
