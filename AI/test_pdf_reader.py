from pypdf import PdfReader

pdf_path = r"C:\Users\User\Downloads\PSI-159_Reports_FinalRpt_ACME.CFI-G.pdf"

reader = PdfReader(pdf_path)

print("PDF Inspection")
print("=" * 40)

print("Total pages:", len(reader.pages))
print("PDF metadata:", reader.metadata)

pages_with_text = 0
total_characters = 0

for page_number, page in enumerate(reader.pages, start=1):
    text = page.extract_text() or ""

    if text.strip():
        pages_with_text += 1

    total_characters += len(text)

    if page_number <= 3:
        print(f"\n--- Page {page_number} ---")
        print("Extracted characters:", len(text))
        print(text[:500])

print("\n" + "=" * 40)
print("Pages with text:", pages_with_text)
print("Pages without text:", len(reader.pages) - pages_with_text)
print("Total extracted characters:", total_characters)

# Inspect a page from the Results section
page_number = 23

page = reader.pages[page_number - 1]
text = page.extract_text() or ""

print(f"\n--- Page {page_number} ---")
print(text)

# Inspect page 24
page_number = 24

page = reader.pages[page_number - 1]
text = page.extract_text() or ""

print(f"\n--- Page {page_number} ---")
print(text)