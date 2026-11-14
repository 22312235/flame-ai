
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

from ingestion.pptx_processor import process_pptx


class PowerPointProcessorTests(unittest.TestCase):

    def test_extracts_slide_text_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "PSI-98_test.pptx"

            presentation = Presentation()
            slide = presentation.slides.add_slide(
                presentation.slide_layouts[5]
            )

            slide.shapes.title.text = "SAFFIRE PSI-98 Results"

            textbox = slide.shapes.add_textbox(
                Inches(1), Inches(2), Inches(5), Inches(1)
            )
            textbox.text_frame.text = (
                "Microgravity investigation results"
            )

            presentation.core_properties.title = "SAFFIRE Test"
            presentation.core_properties.author = "NASA"

            presentation.save(file_path)

            result = process_pptx(str(file_path))

            self.assertEqual(result["investigation_id"], "PSI-98")
            self.assertEqual(result["file_type"], "pptx")
            self.assertEqual(result["metadata"]["slide_count"], 1)
            self.assertEqual(
                result["metadata"]["title"], "SAFFIRE Test"
            )
            self.assertIn(
                "SAFFIRE PSI-98 Results",
                result["extracted_content"][0]["text"]
            )
            self.assertEqual(result["processing_status"], "success")

    def test_rejects_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            process_pptx("missing_file.pptx")

    def test_rejects_non_pptx_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "document.pdf"
            file_path.write_text("test")

            with self.assertRaises(ValueError):
                process_pptx(str(file_path))


if __name__ == "__main__":
    unittest.main()
