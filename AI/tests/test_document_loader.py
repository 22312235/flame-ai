import tempfile
import unittest
from pathlib import Path

from ingestion.document_loader import load_text_document, parse_psi_investigation


class ParsePSIInvestigationTests(unittest.TestCase):
    def test_preserves_sections_fields_values_and_multiline_content(self):
        text = (
            "ONTOLOGY SOURCE REFERENCE\n"
            "Term Source Name\tEFO\t\tPSI\t\n"
            "INVESTIGATION\n"
            "Investigation Identifier\t\n"
            "INVESTIGATION PUBLICATIONS\n"
            "Investigation PubMed ID\n"
            "Comment[Objective]\t\"First line\nsecond line\"\n"
            "STUDY DESIGN DESCRIPTORS\n"
            "Study Design Type\tCygnus\tFire\n"
            "Study Design Type\tSAFFIRE\n"
        )

        sections = parse_psi_investigation(text)

        self.assertEqual(
            [section["name"] for section in sections],
            [
                "ONTOLOGY SOURCE REFERENCE",
                "INVESTIGATION",
                "INVESTIGATION PUBLICATIONS",
                "STUDY DESIGN DESCRIPTORS",
            ],
        )
        self.assertEqual(
            sections[0]["fields"],
            [
                {
                    "name": "Term Source Name",
                    "values": ["EFO", "", "PSI", ""],
                }
            ],
        )
        self.assertEqual(
            sections[1]["fields"],
            [{"name": "Investigation Identifier", "values": [""]}],
        )
        self.assertEqual(
            sections[2]["fields"],
            [
                {"name": "Investigation PubMed ID", "values": []},
                {
                    "name": "Comment[Objective]",
                    "values": ["First line\nsecond line"],
                },
            ],
        )
        self.assertEqual(
            sections[3]["fields"],
            [
                {"name": "Study Design Type", "values": ["Cygnus", "Fire"]},
                {"name": "Study Design Type", "values": ["SAFFIRE"]},
            ],
        )

    def test_rejects_field_before_first_section(self):
        with self.assertRaisesRegex(ValueError, "before the first section"):
            parse_psi_investigation("Investigation Identifier\tPSI-1\n")

    def test_rejects_malformed_quoted_value(self):
        with self.assertRaisesRegex(ValueError, "Invalid tab-delimited PSI metadata"):
            parse_psi_investigation('INVESTIGATION\nComment[Note]\t"unterminated\n')


class LoadTextDocumentTests(unittest.TestCase):
    def test_loads_nasa_psi_fixture_without_losing_metadata(self):
        path = Path(__file__).parent / "fixtures" / "i_Investigation.txt"
        original_text = path.read_text(encoding="utf-8-sig")

        document = load_text_document(str(path))

        self.assertEqual(document["investigation_id"], "PSI-98")
        self.assertEqual(document["source"], path.name)
        self.assertEqual(document["text"], original_text)
        self.assertEqual(document["metadata"]["file_size"], path.stat().st_size)
        self.assertEqual(
            [section["name"] for section in document["sections"]],
            [
                "ONTOLOGY SOURCE REFERENCE",
                "INVESTIGATION",
                "INVESTIGATION PUBLICATIONS",
                "INVESTIGATION CONTACTS",
                "STUDY",
                "STUDY DESIGN DESCRIPTORS",
                "STUDY PUBLICATIONS",
                "STUDY FACTORS",
                "STUDY ASSAYS",
                "STUDY PROTOCOLS",
                "STUDY CONTACTS",
            ],
        )

        fields = [
            field
            for section in document["sections"]
            for field in section["fields"]
        ]
        doi_values = [
            field["values"]
            for field in fields
            if field["name"] == "Study Publication DOI"
        ]
        self.assertEqual(
            doi_values,
            [[
                "",
                "",
                "10.1016/j.combustflame.2018.10.012",
                "10.1016/j.proci.2018.05.168",
                "10.1016/j.actaastro.2014.11.025",
                "",
            ]],
        )
        self.assertTrue(
            any(
                field["name"] == "Comment[Objective]"
                and "\n" in field["values"][0]
                for field in fields
            )
        )

    def test_adds_parsed_sections_for_investigation_file(self):
        text = "INVESTIGATION\nInvestigation Identifier\tPSI-98\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "i_Investigation.txt"
            path.write_text(text, encoding="utf-8")

            document = load_text_document(str(path))

        self.assertEqual(document["investigation_id"], "PSI-98")
        self.assertEqual(document["text"], text)
        self.assertEqual(
            document["sections"],
            [
                {
                    "name": "INVESTIGATION",
                    "fields": [
                        {"name": "Investigation Identifier", "values": ["PSI-98"]}
                    ],
                }
            ],
        )

    def test_leaves_other_text_documents_unparsed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_text("ordinary text", encoding="utf-8")

            document = load_text_document(str(path))

        self.assertEqual(document["text"], "ordinary text")
        self.assertNotIn("sections", document)


if __name__ == "__main__":
    unittest.main()
