from unittest.mock import patch
import tempfile
import unittest
from pathlib import Path

import pymupdf as fitz

from ingestion.pdf_processor import process_pdf


class PDFProcessorTests(unittest.TestCase):

    def create_pdf(self, folder, filename, pages):
        path = Path(folder) / filename

        pdf = fitz.open()

        for text in pages:
            page = pdf.new_page()
            if text:
                page.insert_text((72, 72), text)

        pdf.save(path)
        pdf.close()

        return path

    def create_image_pdf(self, folder, filename):
        from PIL import Image

        path = Path(folder) / filename
        image_path = Path(folder) / "sample.png"

        # Create a small test image.
        image = Image.new("RGB", (100, 100), color="red")
        image.save(image_path)

        # Insert it into a PDF.
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_image(
            fitz.Rect(72, 72, 172, 172),
            filename=str(image_path)
        )

        pdf.save(path)
        pdf.close()

        return path

    def test_extracts_images_with_page_information(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.create_image_pdf(
                folder,
                "image_report.pdf"
            )

            result = process_pdf(str(path))

            page = result["extracted_content"][0]
            images = page["images"]

            self.assertEqual(len(images), 1)
            self.assertEqual(images[0]["page"], 1)
            self.assertTrue(Path(images[0]["path"]).exists())
            self.assertEqual(result["metadata"]["image_count"], 1)

    def create_table_pdf(self, folder, filename):
        path = Path(folder) / filename

        pdf = fitz.open()
        page = pdf.new_page()

        # Draw a 3-row, 2-column table.
        x_positions = [72, 230, 400]
        y_positions = [100, 140, 180, 220]

        for x in x_positions:
            page.draw_line(
                (x, 100),
                (x, 220),
                color=(0, 0, 0),
                width=1
            )

        for y in y_positions:
            page.draw_line(
                (72, y),
                (400, y),
                color=(0, 0, 0),
                width=1
            )

        # Insert text into the cells.
        cells = [
            (80, 125, "Parameter"),
            (238, 125, "Value"),
            (80, 165, "Temperature"),
            (238, 165, "25 C"),
            (80, 205, "Pressure"),
            (238, 205, "101 kPa")
        ]

        for x, y, text in cells:
            page.insert_text((x, y), text)

        pdf.save(path)
        pdf.close()

        return path

    def test_extracts_tables_with_page_information(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.create_table_pdf(
                folder,
                "table_report.pdf"
            )

            result = process_pdf(str(path))

            page = result["extracted_content"][0]
            tables = page["tables"]

            self.assertEqual(len(tables), 1)
            self.assertEqual(tables[0]["page"], 1)

            rows = tables[0]["rows"]

            self.assertEqual(rows[0], ["Parameter", "Value"])
            self.assertEqual(
                rows[1],
                ["Temperature", "25 C"]
            )
            self.assertEqual(
                rows[2],
                ["Pressure", "101 kPa"]
            )

    @patch("ingestion.pdf_processor.extract_page_ocr")
    def test_uses_ocr_when_page_has_no_text(self, mock_ocr):
        mock_ocr.return_value = "SAFFIRE investigation results"

        with tempfile.TemporaryDirectory() as folder:
            path = self.create_pdf(
                folder,
                "scanned_report.pdf",
                [""]
            )

            result = process_pdf(str(path))

            page = result["extracted_content"][0]

            self.assertEqual(
                page["text"],
                "SAFFIRE investigation results"
            )
            self.assertEqual(
                page["extraction_method"],
                "ocr"
            )
            mock_ocr.assert_called_once()

    def test_extracts_text_page_by_page(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.create_pdf(
                folder,
                "PSI-98_report.pdf",
                ["First page content", "Second page content"]
            )

            result = process_pdf(str(path))

            self.assertEqual(result["investigation_id"], "PSI-98")
            self.assertEqual(result["metadata"]["page_count"], 2)
            self.assertEqual(
                result["extracted_content"][0]["text"],
                "First page content"
            )
            self.assertEqual(
                result["extracted_content"][1]["text"],
                "Second page content"
            )
            self.assertEqual(result["processing_status"], "success")

    def test_warns_when_page_has_no_extractable_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.create_pdf(folder, "empty_page.pdf", [""])

            result = process_pdf(str(path))

            self.assertEqual(result["processing_status"], "warning")
            self.assertTrue(result["warnings"])

    def test_rejects_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            process_pdf("missing.pdf")

    def test_rejects_non_pdf_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "document.txt"
            path.write_text("Some text")

            with self.assertRaises(ValueError):
                process_pdf(str(path))


if __name__ == "__main__":
    unittest.main()