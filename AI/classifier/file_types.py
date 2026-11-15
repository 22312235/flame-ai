from enum import Enum


class FileCategory(str, Enum):
    NUMERICAL = "numerical_dataset"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    UNKNOWN = "unknown"


# Each extension maps to the expected content family and downstream processor.
SUPPORTED_EXTENSIONS = {
    ".csv": {"format": "CSV", "category": FileCategory.NUMERICAL, "processor": "csv_processor"},
    ".xls": {"format": "XLS", "category": FileCategory.NUMERICAL, "processor": "excel_processor"},
    ".xlsx": {"format": "XLSX", "category": FileCategory.NUMERICAL, "processor": "excel_processor"},
    ".txt": {"format": "TXT", "category": FileCategory.DOCUMENT, "processor": "document_processor"},
    ".pdf": {"format": "PDF", "category": FileCategory.DOCUMENT, "processor": "document_processor"},
    ".ppt": {"format": "PPT", "category": FileCategory.DOCUMENT, "processor": "document_processor"},
    ".pptx": {"format": "PPTX", "category": FileCategory.DOCUMENT, "processor": "document_processor"},
    ".jpg": {"format": "JPEG", "category": FileCategory.IMAGE, "processor": "image_processor"},
    ".jpeg": {"format": "JPEG", "category": FileCategory.IMAGE, "processor": "image_processor"},
    ".png": {"format": "PNG", "category": FileCategory.IMAGE, "processor": "image_processor"},
    ".mp4": {"format": "MP4", "category": FileCategory.VIDEO, "processor": "video_processor"},
    ".ts": {"format": "MPEG-TS", "category": FileCategory.VIDEO, "processor": "video_processor"},
}

PROCESSING_PRIORITY = {
    FileCategory.NUMERICAL: 10,
    FileCategory.DOCUMENT: 20,
    FileCategory.IMAGE: 30,
    FileCategory.VIDEO: 40,
    FileCategory.UNKNOWN: 99,
}