
from ingestion.pdf_loader import load_pdf_document
from rag.chunker import chunk_documents

pdf_path = r"C:\Users\User\Downloads\PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf"

pages = load_pdf_document(pdf_path)

chunks = chunk_documents(
    pages,
    chunk_size=1200,
    overlap=200
)

print("Chunking Test")
print("=" * 40)

print("Original pages:", len(pages))
print("Generated chunks:", len(chunks))

print("\nFirst chunk:")
print("ID:", chunks[0]["chunk_id"])
print("Source:", chunks[0]["source"])
print("Page:", chunks[0]["page_number"])
print("Characters:", len(chunks[0]["text"]))
print(chunks[0]["text"][:500])

print("\nValidation:")

assert len(chunks) > len(pages)
assert all(chunk["text"].strip() for chunk in chunks)
assert all("page_number" in chunk for chunk in chunks)
assert all("source" in chunk for chunk in chunks)

print("All tests passed!")
