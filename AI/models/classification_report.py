from dataclasses import dataclass, field
from typing import List

from models.classified_file import ClassifiedFile


@dataclass
class ClassificationReport:
    root_directory: str
    files: List[ClassifiedFile] = field(default_factory=list)

    def to_dict(self) -> dict:
        counts = {}
        for item in self.files:
            key = item.category.value
            counts[key] = counts.get(key, 0) + 1

        return {
            "root_directory": self.root_directory,
            "summary": {
                "total_files": len(self.files),
                "total_bytes": sum(item.file_size for item in self.files),
                "category_counts": counts,
                "classified": sum(item.status == "classified" for item in self.files),
                "extension_mismatches": sum(item.status == "extension_mismatch" for item in self.files),
                "unsupported": sum(item.status == "unsupported" for item in self.files),
                "errors": sum(item.status == "error" for item in self.files),
                "duplicates": sum(item.duplicate_of is not None for item in self.files),
            },
            "files": [item.to_dict() for item in self.files],
        }