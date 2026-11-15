from dataclasses import asdict, dataclass
from typing import Optional

from classifier.file_types import FileCategory


@dataclass
class ClassifiedFile:
    filename: str
    relative_path: str
    file_path: str
    extension: str
    detected_format: str
    category: FileCategory
    processor: Optional[str]
    file_size: int
    status: str = "classified"
    error: Optional[str] = None
    sha256: Optional[str] = None
    duplicate_of: Optional[str] = None
    processing_priority: int = 99

    def to_dict(self) -> dict:
        data = asdict(self)
        data["category"] = self.category.value
        return data