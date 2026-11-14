from pptx.enum.chart import XL_CHART_TYPE
import re
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


def extract_shape_text(shape) -> list:
    """Extract text from a PowerPoint shape, including grouped shapes."""

    content = []

    # Extract text from text boxes and other text-containing shapes.
    if shape.has_text_frame:
        text = shape.text.strip()

        if text:
            content.append(text)

    # Recursively inspect shapes inside groups.
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        for grouped_shape in shape.shapes:
            content.extend(extract_shape_text(grouped_shape))

    return content
 

def extract_slide_tables(slide, slide_number: int) -> list:
    """Extract structured tables from a PowerPoint slide."""

    tables = []

    for shape_index, shape in enumerate(slide.shapes, start=1):

        if not shape.has_table:
            continue

        rows = []

        for row in shape.table.rows:
            cleaned_row = [
                cell.text.strip()
                for cell in row.cells
            ]

            if any(cleaned_row):
                rows.append(cleaned_row)

        if rows:
            tables.append({
                "table_id": f"slide{slide_number}_table{shape_index}",
                "slide": slide_number,
                "rows": rows
            })

    return tables

def extract_slide_charts(slide, slide_number: int) -> list:
    """Extract chart titles, categories and numerical series."""

    charts = []

    for shape_index, shape in enumerate(slide.shapes, start=1):

        if not shape.has_chart:
            continue

        chart = shape.chart

        chart_data = {
            "chart_id": f"slide{slide_number}_chart{shape_index}",
            "slide": slide_number,
            "chart_type": str(chart.chart_type),
            "title": (
                chart.chart_title.text_frame.text.strip()
                if chart.has_title
                else None
            ),
            "series": []
        }

        for series in chart.series:
            chart_data["series"].append({
                "name": series.name,
                "values": list(series.values)
            })

        # Extract category labels when available.
        try:
            chart_data["categories"] = [
                str(category.label)
                for category in chart.plots[0].categories
            ]
        except (IndexError, AttributeError, TypeError):
            chart_data["categories"] = []

        charts.append(chart_data)

    return charts

def extract_slide_notes(slide) -> str:
    """Extract speaker notes from a PowerPoint slide."""

    try:
        notes_slide = slide.notes_slide

        if notes_slide.notes_text_frame:
            return notes_slide.notes_text_frame.text.strip()

    except (AttributeError, ValueError):
        pass

    return ""


def extract_slide_images(
    slide,
    slide_number: int,
    output_dir: Path
) -> list:
    """Extract embedded images and preserve their slide references."""

    images = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for shape_index, shape in enumerate(slide.shapes, start=1):

        if not shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            continue

        try:
            image = shape.image
            extension = image.ext
            image_id = f"slide{slide_number}_image{shape_index}"

            image_path = output_dir / f"{image_id}.{extension}"
            image_path.write_bytes(image.blob)

            images.append({
                "image_id": image_id,
                "path": str(image_path),
                "slide": slide_number,
                "format": extension
            })

        except (AttributeError, ValueError):
            continue

    return images


def extract_presentation_metadata(presentation) -> dict:
    """Extract PowerPoint presentation metadata."""

    properties = presentation.core_properties

    return {
        "file_type": ".pptx",
        "title": properties.title,
        "author": properties.author,
        "subject": properties.subject,
        "created": (
            properties.created.isoformat()
            if properties.created else None
        ),
        "modified": (
            properties.modified.isoformat()
            if properties.modified else None
        ),
        "slide_count": len(presentation.slides)
    }

def extract_references(text: str) -> dict:
    """Extract DOI references from presentation text."""

    dois = re.findall(
        r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+",
        text,
        re.IGNORECASE
    )

    return {
        "dois": sorted(set(dois))
    }

def process_pptx(file_path: str) -> dict:
    """Extract text, tables, charts, notes, images and metadata."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() != ".pptx":
        raise ValueError("Only .pptx files are supported.")

    try:
        presentation = Presentation(path)

        extracted_content = []
        all_text = []
        warnings = []

        image_dir = path.parent / f"{path.stem}_extracted_images"

        for slide_number, slide in enumerate(
            presentation.slides, start=1
        ):
            slide_text = []

            for shape in slide.shapes:
                slide_text.extend(extract_shape_text(shape))

            notes = extract_slide_notes(slide)
            tables = extract_slide_tables(slide, slide_number)
            charts = extract_slide_charts(slide, slide_number)
            images = extract_slide_images(
                slide, slide_number, image_dir
            )

            text_content = "\n".join(slide_text)

            all_text.append(text_content)
            all_text.append(notes)

            extracted_content.append({
                "slide": slide_number,
                "text": text_content,
                "notes": notes,
                "tables": tables,
                "charts": charts,
                "images": images
            })

        full_text = "\n".join(all_text)

        investigation_match = re.search(
            r"PSI-\d+",
            path.name + "\n" + full_text,
            re.IGNORECASE
        )

        metadata = extract_presentation_metadata(presentation)

        metadata["file_size"] = path.stat().st_size

        return {
            "investigation_id": (
                investigation_match.group(0).upper()
                if investigation_match else None
            ),
            "source": path.name,
            "file_type": "pptx",
            "extracted_content": extracted_content,
            "metadata": metadata,
            "references": extract_references(full_text),
            "processing_status": (
                "success" if full_text.strip()
                or any(
                    item["tables"] or item["charts"] or item["images"]
                    for item in extracted_content
                )
                else "warning"
            ),
            "errors": [],
            "warnings": warnings
        }

    except (FileNotFoundError, ValueError):
        raise
    except Exception as error:
        raise RuntimeError(
            f"Failed to process PowerPoint file: {error}"
        ) from error
