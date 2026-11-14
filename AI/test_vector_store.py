
import tempfile
from pathlib import Path

from ingestion.pdf_loader import load_pdf_document
from rag.chunker import chunk_documents
from rag.embedder import embed_chunks
from rag.vector_store import save_chunks, load_chunks


pdf_path = r"C:\Users\User\Downloads\PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf"

pages = load_pdf_document(pdf_path)
chunks = chunk_documents(pages)

# Use 3 chunks for this initial test.
embedded_chunks = embed_chunks(chunks[:3])

with tempfile.TemporaryDirectory() as temp_dir:
    store_path = Path(temp_dir) / "vector_store.json"

    save_chunks(embedded_chunks, str(store_path))
    loaded_chunks = load_chunks(str(store_path))

    print("Vector Store Test")
    print("=" * 40)

    print("Saved chunks:", len(embedded_chunks))
    print("Loaded chunks:", len(loaded_chunks))
    print("Embedding dimensions:", len(loaded_chunks[0]["embedding"]))

    assert len(loaded_chunks) == len(embedded_chunks)
    assert loaded_chunks[0]["text"] == embedded_chunks[0]["text"]
    assert loaded_chunks[0]["embedding"] == embedded_chunks[0]["embedding"]
    assert loaded_chunks[0]["page_number"] == embedded_chunks[0]["page_number"]

    print("\nAll tests passed!")
