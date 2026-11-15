import csv
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Optional

from classifier.file_types import (
    FileCategory,
    PROCESSING_PRIORITY,
    SUPPORTED_EXTENSIONS,
)
from models.classified_file import ClassifiedFile
from models.classification_report import ClassificationReport


OLE_SIGNATURE = bytes.fromhex("D0 CF 11 E0 A1 B1 1A E1")
PNG_SIGNATURE = bytes.fromhex("89 50 4E 47 0D 0A 1A 0A")
JPEG_SIGNATURE = bytes.fromhex("FF D8 FF")


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _read_prefix(path: Path, size: int = 64 * 1024) -> bytes:
    with path.open("rb") as stream:
        return stream.read(size)


def _is_text(data: bytes) -> bool:
    if not data:
        return False
    # Accept UTF-8 and UTF-16 text; reject binary control characters.
    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = data.decode("utf-16")
        except UnicodeDecodeError:
            return False
    if "\x00" in decoded:
        return False
    controls = sum(ord(ch) < 32 and ch not in "\n\r\t\f\b" for ch in decoded)
    return controls / max(len(decoded), 1) < 0.01


def _looks_like_csv(data: bytes) -> bool:
    if not _is_text(data):
        return False
    try:
        sample = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            sample = data.decode("utf-16")
        except UnicodeDecodeError:
            return False
    sample = sample.strip()
    if not sample:
        return False
    try:
        dialect = csv.Sniffer().sniff(sample[:8192], delimiters=",;\t|")
        rows = list(csv.reader(io.StringIO(sample[:8192]), dialect))
        return len(rows) >= 2 and len(rows[0]) >= 2 and any(len(row) == len(rows[0]) for row in rows[1:])
    except (csv.Error, UnicodeError):
        # A single-column CSV is possible; treat it as text rather than confidently CSV.
        return False


def _zip_document_type(path: Path) -> Optional[str]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names:
                return None
            if "xl/workbook.xml" in names:
                return "XLSX"
            if "ppt/presentation.xml" in names:
                return "PPTX"
    except (zipfile.BadZipFile, OSError, RuntimeError):
        return None
    return None


def _mpeg_ts_valid(data: bytes) -> bool:
    # MPEG-TS packets are normally 188 bytes and begin with sync byte 0x47.
    # Check multiple packet boundaries to reduce false positives.
    packet_size = 188
    return (
        len(data) >= packet_size * 3
        and data[0] == 0x47
        and data[packet_size] == 0x47
        and data[packet_size * 2] == 0x47
    )


def _detect_content(path: Path, prefix: bytes) -> Optional[str]:
    if prefix.startswith(b"%PDF-"):
        return "PDF"
    if prefix.startswith(JPEG_SIGNATURE):
        return "JPEG"
    if prefix.startswith(PNG_SIGNATURE):
        return "PNG"
    if prefix.startswith(OLE_SIGNATURE):
        return "OLE"
    if _zip_document_type(path):
        return _zip_document_type(path)
    if len(prefix) >= 12 and prefix[4:8] == b"ftyp":
        return "MP4"
    if _mpeg_ts_valid(prefix):
        return "MPEG-TS"
    if _looks_like_csv(prefix):
        return "CSV"
    if _is_text(prefix):
        return "TXT"
    return None


def _expected_family(extension: str, detected: Optional[str]) -> bool:
    if detected is None:
        return False
    expected = SUPPORTED_EXTENSIONS[extension]["format"]
    if extension in {".xls", ".ppt"}:
        return detected == "OLE"
    if extension in {".xlsx", ".pptx"}:
        return detected == expected
    if extension == ".ts":
        return detected == "MPEG-TS"
    if extension == ".csv":
        return detected == "CSV"
    if extension == ".txt":
        return detected == "TXT"
    return detected == expected


def classify_file(
    file_path: str | Path,
    *,
    hash_file: bool = True,
    max_file_size: Optional[int] = None,
    root_directory: Optional[str | Path] = None,
) -> ClassifiedFile:
    path = Path(file_path)
    extension = path.suffix.lower()
    relative = path.name
    if root_directory is not None:
        try:
            relative = str(path.resolve().relative_to(Path(root_directory).resolve()))
        except ValueError:
            relative = path.name

    try:
        if path.is_symlink():
            raise ValueError("Symbolic links are not accepted by the classifier.")
        if not path.exists() or not path.is_file():
            raise ValueError("Path does not point to a regular file.")

        size = path.stat().st_size
        if size == 0:
            raise ValueError("File is empty.")

        if extension not in SUPPORTED_EXTENSIONS:
            return ClassifiedFile(
                filename=path.name, relative_path=relative, file_path=str(path.resolve()),
                extension=extension, detected_format="UNKNOWN",
                category=FileCategory.UNKNOWN, processor=None, file_size=size,
                status="unsupported", error="Unsupported file extension.",
            )

        if max_file_size is not None and size > max_file_size:
            raise ValueError(f"File exceeds configured size limit ({max_file_size} bytes).")

        prefix = _read_prefix(path)
        detected = _detect_content(path, prefix)
        expected = SUPPORTED_EXTENSIONS[extension]
        matches = _expected_family(extension, detected)

        # Preserve the extension's expected route only when the content check passes.
        category = expected["category"] if matches else FileCategory.UNKNOWN
        processor = expected["processor"] if matches else None
        status = "classified" if matches else "extension_mismatch"
        error = None if matches else (
            f"Expected {expected['format']} content for {extension}, "
            f"but detected {detected or 'unrecognized/binary content'}."
        )

        checksum = _sha256(path) if hash_file else None
        return ClassifiedFile(
            filename=path.name, relative_path=relative, file_path=str(path.resolve()),
            extension=extension, detected_format=detected or "UNKNOWN",
            category=category, processor=processor, file_size=size,
            status=status, error=error, sha256=checksum,
            processing_priority=PROCESSING_PRIORITY[category],
        )
    except Exception as exc:
        try:
            size = path.stat().st_size if path.exists() and path.is_file() else 0
        except OSError:
            size = 0
        return ClassifiedFile(
            filename=path.name, relative_path=relative, file_path=str(path.absolute()),
            extension=extension, detected_format="UNKNOWN",
            category=FileCategory.UNKNOWN, processor=None, file_size=size,
            status="error", error=str(exc),
        )


def classify_directory(
    directory: str | Path,
    *,
    hash_files: bool = True,
    max_file_size: Optional[int] = None,
) -> ClassificationReport:
    root = Path(directory).resolve()
    if not root.exists() or not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    report = ClassificationReport(root_directory=str(root))
    seen_hashes: dict[str, str] = {}

    # Do not follow symlinked directories. Symlinked files are rejected by classify_file.
    paths = sorted(
        (item for item in root.rglob("*") if item.is_file() or item.is_symlink()),
        key=lambda item: str(item).lower(),
    )
    for path in paths:
        result = classify_file(
            path,
            hash_file=hash_files,
            max_file_size=max_file_size,
            root_directory=root,
        )
        if result.sha256:
            previous = seen_hashes.get(result.sha256)
            if previous:
                result.duplicate_of = previous
            else:
                seen_hashes[result.sha256] = result.relative_path
        report.files.append(result)

    # Numerical and text inputs first; larger media can be processed later.
    report.files.sort(key=lambda item: (item.processing_priority, item.relative_path.lower()))
    return report