
from ingestion.pdf_loader import load_pdf_document
from rag.chunker import chunk_documents
from rag.embedder import embed_chunks

pdf_path = r"C:\Users\User\Downloads\PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf"

pages = load_pdf_document(pdf_path)
chunks = chunk_documents(pages)

# Test with only 3 chunks first.
sample_chunks = chunks[:3]

embedded_chunks = embed_chunks(sample_chunks)

print("Embedding Test")
print("=" * 40)

print("Input chunks:", len(sample_chunks))
print("Embedded chunks:", len(embedded_chunks))

for chunk in embedded_chunks:
    print(
        f"Chunk {chunk['chunk_id']} | "
        f"Page {chunk['page_number']} | "
        f"Dimensions: {len(chunk['embedding'])}"
    )

assert len(embedded_chunks) == 3
assert all(len(chunk["embedding"]) == 768 for chunk in embedded_chunks)

print("\nAll tests passed!")
