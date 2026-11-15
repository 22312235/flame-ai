from __future__ import annotations

import inspect

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from uuid import UUID

from processing.document_loader import load_text_document
from processing.pdf_processor import process_pdf
from processing.pptx_processor import process_pptx
from processing.tabular_processor import process_tabular_file
from processing.image_processor import process_image_file
from processing.video_processor import process_video

from database.ingestion.document_ingestion import DocumentIngestion
from database.ingestion.numerical_ingestion import NumericalIngestion
from database.ingestion.image_ingestion import ImageIngestion
from database.ingestion.video_ingestion import VideoIngestion

from orchestration.processor_registry import (
    ProcessorRegistry,
)


# ---------------------------------------------------------
# Processor helpers
# ---------------------------------------------------------

def _get_processor_options(
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Retrieve optional processor-specific parameters."""

    options = parameters.get("processor_options", {})

    return options if isinstance(options, dict) else {}


def _call_with_supported_options(
    processor: Any,
    file_path: Path,
    parameters: dict[str, Any],
) -> Any:
    """
    Call a processor with only the options supported by its signature.
    """

    options = _get_processor_options(parameters)
    signature = inspect.signature(processor)

    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        supported_options = options
    else:
        supported_options = {
            key: value
            for key, value in options.items()
            if key in signature.parameters
            and signature.parameters[key].kind
            in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
        }

    return processor(str(file_path), **supported_options)


# ---------------------------------------------------------
# Document processor
# ---------------------------------------------------------

def process_document_file(
    file_path: Path,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """
    Dispatch document processing according to file extension.

    Supported:
        TXT, PDF, PPTX
    """

    extension = file_path.suffix.lower()

    if extension == ".txt":
        return load_text_document(str(file_path))

    if extension == ".pdf":
        return process_pdf(str(file_path))

    if extension == ".pptx":
        return process_pptx(str(file_path))

    if extension == ".ppt":
        raise NotImplementedError(
            "Legacy .ppt files are not yet supported. "
            "Convert the file to .pptx before processing."
        )

    raise ValueError(
        f"Unsupported document extension: {extension}"
    )


# ---------------------------------------------------------
# Numerical processors
# ---------------------------------------------------------

def process_csv_file(
    file_path: Path,
    parameters: dict[str, Any],
) -> Any:
    return _call_with_supported_options(
        process_tabular_file,
        file_path,
        parameters,
    )


def process_excel_file(
    file_path: Path,
    parameters: dict[str, Any],
) -> Any:
    return _call_with_supported_options(
        process_tabular_file,
        file_path,
        parameters,
    )


# ---------------------------------------------------------
# Image processor
# ---------------------------------------------------------

def process_image_file_wrapper(
    file_path: Path,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    return _call_with_supported_options(
        process_image_file,
        file_path,
        parameters,
    )


# ---------------------------------------------------------
# Video processor
# ---------------------------------------------------------

def process_video_file(
    file_path: Path,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    return _call_with_supported_options(
        process_video,
        file_path,
        parameters,
    )


# ---------------------------------------------------------
# Ingestion adapters
# ---------------------------------------------------------

def ingest_document_result(
    db: Session,
    file_id: UUID,
    result: Any,
) -> Any:
    return DocumentIngestion.ingest_document(
        db=db,
        file_id=file_id,
        processor_result=result,
    )


def ingest_numerical_result(
    db: Session,
    file_id: UUID,
    result: Any,
) -> Any:
    return NumericalIngestion.ingest_profiles(
        db=db,
        file_id=file_id,
        profiles=result,
    )


def ingest_image_result(
    db: Session,
    file_id: UUID,
    result: Any,
) -> Any:
    return ImageIngestion.ingest_image(
        db=db,
        file_id=file_id,
        processor_result=result,
    )


def ingest_video_result(
    db: Session,
    file_id: UUID,
    result: Any,
) -> Any:
    return VideoIngestion.ingest_video(
        db=db,
        file_id=file_id,
        processor_result=result,
    )


# ---------------------------------------------------------
# Default processor registration
# ---------------------------------------------------------

def register_default_processors(
    registry: ProcessorRegistry,
    processor_types: dict[str, str],
) -> None:
    """
    Register processors using the exact labels assigned by
    the file classifier.

    Expected processor_types:
        {
            "csv": "csv_processor",
            "excel": "excel_processor",
            "document": "document_processor",
            "image": "image_processor",
            "video": "video_processor",
        }
    """

    registrations = {
        "csv": (
            process_csv_file,
            ingest_numerical_result,
            "CSV numerical dataset processor",
        ),
        "excel": (
            process_excel_file,
            ingest_numerical_result,
            "Excel numerical dataset processor",
        ),
        "document": (
            process_document_file,
            ingest_document_result,
            "TXT, PDF and PPTX document processor",
        ),
        "image": (
            process_image_file_wrapper,
            ingest_image_result,
            "Image metadata and thumbnail processor",
        ),
        "video": (
            process_video_file,
            ingest_video_result,
            "Video frames, scenes, audio and transcription processor",
        ),
    }

    for category, processor_type in processor_types.items():
        if category not in registrations:
            continue

        processor, adapter, description = registrations[category]

        registry.register(
            processor_type=processor_type,
            processor=processor,
            ingestion_adapter=adapter,
            description=description,
        )