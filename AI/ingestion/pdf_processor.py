
import re
from pathlib import Path
import pdfplumber
import pymupdf as fitz
import pytesseract
from PIL import Image

# Configure Tesseract for Windows.
pytesseract.pytesseract.tesseract_cmd = (
    "C:/Program Files/Tesseract-OCR/tesseract.exe"
)


def extract_page_ocr(page) -> str:
    """Extract text from a scanned PDF page using OCR."""

    pixmap = page.get_pixmap(dpi=300, alpha=False)

    image = Image.frombytes(
        "RGB",
        [pixmap.width, pixmap.height],
        pixmap.samples
    )

    return pytesseract.image_to_string(
        image,
        lang="eng"
    ).strip()


def extract_references(text: str) -> dict:
    """Extract DOI references from document text."""

    dois = re.findall(
        r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+",
        text,
        re.IGNORECASE
    )

    return {
        "dois": sorted(set(dois))
    }


def extract_pdf_images(
    page,
    page_number: int,
    output_dir: Path
) -> list:
    """Extract embedded images and preserve their page references."""

    images = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for image_index, image_info in enumerate(
        page.get_images(full=True),
        start=1
    ):
        xref = image_info[0]
        extracted = page.parent.extract_image(xref)

        extension = extracted["ext"]
        image_id = f"page{page_number}_image{image_index}"

        image_path = output_dir / f"{image_id}.{extension}"
        image_path.write_bytes(extracted["image"])

        images.append({
            "image_id": image_id,
            "path": str(image_path),
            "page": page_number,
            "xref": xref,
            "format": extension
        })

    return images


def extract_pdf_tables(file_path: Path, page_number: int) -> list:
    """Extract structured tables from a specific PDF page."""

    tables = []

    with pdfplumber.open(file_path) as pdf:
        page = pdf.pages[page_number - 1]
        extracted_tables = page.extract_tables()

        for table_index, table in enumerate(extracted_tables, start=1):
            rows = []

            for row in table:
                cleaned_row = [
                    cell.strip() if cell else ""
                    for cell in row
                ]

                # Ignore completely empty rows.
                if any(cleaned_row):
                    rows.append(cleaned_row)

            if rows:
                tables.append({
                    "table_id": f"page{page_number}_table{table_index}",
                    "page": page_number,
                    "rows": rows
                })

    return tables


def process_pdf(file_path: str) -> dict:
    """Extract PDF text, metadata, OCR, images and references."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    extracted_content = []
    warnings = []

    image_dir = path.parent / f"{path.stem}_extracted_images"

    try:
        with fitz.open(path) as pdf:

            if pdf.is_encrypted:
                raise ValueError("PDF is password-protected.")

            metadata = pdf.metadata or {}

            for page_number, page in enumerate(pdf, start=1):

                text = page.get_text("text").strip()
                extraction_method = "text"

                # Use OCR when the page has little or no text.
                if len(text) < 20:
                    try:
                        ocr_text = extract_page_ocr(page)

                        if ocr_text:
                            text = ocr_text
                            extraction_method = "ocr"
                        else:
                            warnings.append(
                                f"No text extracted from page {page_number}."
                            )

                    except Exception as ocr_error:
                        warnings.append(
                            f"OCR failed on page {page_number}: {ocr_error}"
                        )

                images = extract_pdf_images(
                    page,
                    page_number,
                    image_dir
                )
                tables = extract_pdf_tables(
                     path,
                     page_number
                )

                tables = extract_pdf_tables(path, page_number)

                extracted_content.append({
                    "page": page_number,
                    "text": text,
                    "extraction_method": extraction_method,
                    "images": images,
                    "tables": tables
                })

            full_text = "\n".join(
                item["text"] for item in extracted_content
            )

            match = re.search(
                r"PSI-\d+",
                path.name + "\n" + full_text,
                re.IGNORECASE
            )

            references = extract_references(full_text)

            document_metadata = {
                "file_type": ".pdf",
                "file_size": path.stat().st_size,
                "page_count": len(pdf),
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "producer": metadata.get("producer"),
                "creation_date": metadata.get("creationDate"),
                "image_count": sum(
                    len(item["images"])
                    for item in extracted_content
                )
            }

            return {
                "investigation_id": (
                    match.group(0).upper() if match else None
                ),
                "source": path.name,
                "file_type": "pdf",
                "extracted_content": extracted_content,
                "metadata": document_metadata,
                "references": references,
                "processing_status": (
                    "success" if full_text.strip() else "warning"
                ),
                "errors": [],
                "warnings": warnings
            }

    except (FileNotFoundError, ValueError):
        raise

    except Exception as error:
        raise RuntimeError(
            f"Failed to process PDF {path.name}: {error}"
        ) from error
