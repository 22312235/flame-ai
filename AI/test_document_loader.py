from ingestion.document_loader import load_text_document

document = load_text_document(
    r"C:\Users\User\Downloads\PSI-98_metadata_PSI-166_SAFFIRE-I\i_Investigation.txt"
)

print("Investigation ID:", document["investigation_id"])
print("Source:", document["source"])
print("Text length:", len(document["text"]))
print("\nFirst 500 characters:")
print(document["text"][:500])