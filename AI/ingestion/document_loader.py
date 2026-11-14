
import csv
from io import StringIO
from pathlib import Path
import re
from typing import List, TypedDict


class PSIField(TypedDict):
    name: str
    values: List[str]


class PSISection(TypedDict):
    name: str
    fields: List[PSIField]


def parse_psi_investigation(text: str) -> List[PSISection]:
    sections: List[PSISection] = []
    current_section = None
    rows = csv.reader(StringIO(text, newline=""), delimiter="\t", strict=True)

    try:
        for row in rows:
            if not row:
                continue

            if len(row) == 1 and row[0] and row[0].isupper():
                current_section = {"name": row[0], "fields": []}
                sections.append(current_section)
                continue

            if not row[0]:
                raise ValueError(
                    f"Empty field name in PSI metadata at line {rows.line_num}"
                )
            if current_section is None:
                raise ValueError(
                    f"Field appears before the first section at line {rows.line_num}"
                )

            current_section["fields"].append(
                {"name": row[0], "values": row[1:]}
            )
    except csv.Error as error:
        raise ValueError(
            f"Invalid tab-delimited PSI metadata at line {rows.line_num}: {error}"
        ) from error

    return sections


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


def extract_document_metadata(text: str) -> dict:
    """Extract document metadata from labeled or tab-separated text."""

    metadata = {
        "title": None,
        "author": None,
        "principal_investigator": None
    }

    for line in text.splitlines():
        line = line.strip()

        if "\t" in line:
            field, value = line.split("\t", 1)
        elif ":" in line:
            field, value = line.split(":", 1)
        else:
            continue

        field = field.strip().lower()
        value = value.strip()

        if not value:
            continue

        if field in ("title", "proposal title"):
            metadata["title"] = value

        elif field in ("author", "authors"):
            metadata["author"] = value

        elif field == "principal investigator":
            metadata["principal_investigator"] = value

    return metadata


def load_text_document(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    if path.suffix.lower() != ".txt":
        raise ValueError("Only .txt files are supported.")

    text = path.read_text(encoding="utf-8-sig")

    if not text.strip():
        raise ValueError(f"Document is empty: {path.name}")

    match = re.search(r"PSI-\d+", path.name, re.IGNORECASE)

    if not match:
        match = re.search(r"PSI-\d+", text, re.IGNORECASE)

    document_metadata = extract_document_metadata(text)

    document = {
    "investigation_id": match.group(0).upper() if match else None,
    "source": path.name,
    "text": text,
    "metadata": {
        "file_type": path.suffix.lower(),
        "file_size": path.stat().st_size,
        "title": document_metadata["title"],
        "author": document_metadata["author"],
        "principal_investigator": document_metadata["principal_investigator"],
    },
    "references": extract_references(text),
}

    if path.name.lower() == "i_investigation.txt":
        document["sections"] = parse_psi_investigation(text)

    return document
