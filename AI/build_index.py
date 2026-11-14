
from ingestion.pdf_loader import load_pdf_document
from rag.chunker import chunk_documents
from rag.embedder import embed_chunks
from rag.vector_store import save_chunks


PDF_PATH = r"C:\Users\User\Downloads\PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf"
STORE_PATH = "AI/storage/psi159_vector_store.json"
BATCH_SIZE = 16


print("Loading PDF...")
pages = load_pdf_document(PDF_PATH)

print("Creating chunks...")
chunks = chunk_documents(pages)

print(f"Total pages: {len(pages)}")
print(f"Total chunks: {len(chunks)}")

print("\nGenerating embeddings...")

embedded_chunks = []

for start in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[start:start + BATCH_SIZE]

    embedded_batch = embed_chunks(batch)
    embedded_chunks.extend(embedded_batch)

    print(
        f"Embedded {len(embedded_chunks)}/{len(chunks)} chunks"
    )

print("\nSaving vector store...")
save_chunks(embedded_chunks, STORE_PATH)

print("Index successfully created!")
print("Total embedded chunks:", len(embedded_chunks))
print("Vector store:", STORE_PATH)
