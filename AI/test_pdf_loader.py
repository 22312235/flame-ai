from ingestion.pdf_loader import load_pdf_document

pdf_path = r"C:\Users\User\Downloads\PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf"

pages = load_pdf_document(pdf_path)

print("PDF Loader Test")
print("=" * 40)

print("Total loaded pages:", len(pages))
print("First page:", pages[0]["page_number"])
print("Last page:", pages[-1]["page_number"])

print("\nPage 23:")
page_23 = next(
    page for page in pages
    if page["page_number"] == 23
)

print(page_23["text"][:500])

print("\nValidation:")
assert len(pages) == 93
assert pages[0]["page_number"] == 1
assert pages[-1]["page_number"] == 93
assert pages[22]["source"] == "PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf"

print("All tests passed!")