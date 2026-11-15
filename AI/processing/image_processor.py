from __future__ import annotations

import hashlib
import json
import warnings

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ExifTags, UnidentifiedImageError


SUPPORTED_FORMATS = {
    "JPEG",
    "PNG",
    "TIFF",
    "BMP",
    "WEBP",
}

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
}

# Only extract useful, non-location EXIF fields.
EXIF_FIELDS = {
    "DateTime",
    "DateTimeOriginal",
    "DateTimeDigitized",
    "Make",
    "Model",
    "Software",
    "Orientation",
    "ExposureTime",
    "FNumber",
    "ISOSpeedRatings",
    "FocalLength",
}


@dataclass
class ImageProfile:
    file_name: str
    file_path: str
    file_size_bytes: int
    sha256: str

    image_format: str
    mime_type: str
    extension: str

    width: int
    height: int
    aspect_ratio: float
    pixel_count: int
    color_mode: str

    has_transparency: bool
    frame_count: int

    exif_metadata: dict[str, Any]
    thumbnail_path: str | None

    warnings: list[str]
    processing_status: str
    processed_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 checksum without loading the whole file."""
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    """Convert EXIF values into JSON-compatible values."""
    if value is None:
        return None

    if isinstance(value, bytes):
        return value.hex()

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, tuple):
        return [json_safe(item) for item in value]

    if isinstance(value, list):
        return [json_safe(item) for item in value]

    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def extract_exif_metadata(image: Image.Image) -> dict[str, Any]:
    """Extract a small, useful selection of EXIF fields."""
    metadata: dict[str, Any] = {}

    try:
        exif = image.getexif()

        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))

            if tag_name in EXIF_FIELDS:
                metadata[tag_name] = json_safe(value)

    except Exception:
        # EXIF is optional; its absence should not invalidate an image.
        pass

    return metadata


def detect_transparency(image: Image.Image) -> bool:
    """Check whether an image contains transparency."""
    if image.mode in ("RGBA", "LA"):
        return True

    if image.mode == "P":
        return "transparency" in image.info

    return False


def generate_thumbnail(
    image: Image.Image,
    source_hash: str,
    output_directory: Path,
    thumbnail_size: tuple[int, int],
) -> Path:
    """
    Generate a thumbnail while preserving the original image.

    The filename is based on the source checksum, making repeated
    processing of the same image deterministic.
    """
    output_directory.mkdir(parents=True, exist_ok=True)

    prepared = ImageOps.exif_transpose(image)
    prepared.thumbnail(thumbnail_size)

    if prepared.mode in ("RGBA", "LA", "P"):
        if prepared.mode == "P":
            prepared = prepared.convert("RGBA")

        output_path = output_directory / f"{source_hash[:16]}.png"
        prepared.save(output_path, format="PNG")
    else:
        prepared = prepared.convert("RGB")
        output_path = output_directory / f"{source_hash[:16]}.jpg"
        prepared.save(
            output_path,
            format="JPEG",
            quality=85,
            optimize=True,
        )

    return output_path


def process_image_file(
    file_path: str | Path,
    thumbnail_directory: str | Path | None = None,
    thumbnail_size: tuple[int, int] = (512, 512),
    max_pixels: int = 100_000_000,
) -> dict[str, Any]:
    """
    Validate and profile an image file.

    Parameters
    ----------
    file_path:
        Original image path.

    thumbnail_directory:
        Optional directory in which to save the generated thumbnail.
        If omitted, metadata is extracted without generating a thumbnail.

    thumbnail_size:
        Maximum thumbnail dimensions.

    max_pixels:
        Maximum allowed image pixel count. This helps protect against
        unexpectedly large or decompression-bomb images.

    Returns
    -------
    dict:
        JSON-serializable image profile.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Image does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {path}")

    if path.is_symlink():
        raise ValueError("Symbolic links are not accepted.")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported image extension: {path.suffix}"
        )

    if max_pixels <= 0:
        raise ValueError("max_pixels must be greater than zero.")

    if (
        len(thumbnail_size) != 2
        or any(not isinstance(value, int) or value <= 0
               for value in thumbnail_size)
    ):
        raise ValueError("thumbnail_size must contain two positive integers.")

    warnings_list: list[str] = []
    thumbnail_path: str | None = None

    file_size = path.stat().st_size
    checksum = calculate_sha256(path)

    try:
        # Treat Pillow's decompression-bomb warning as an error.
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning,
            )

            with Image.open(path) as image:
                image_format = image.format
                width, height = image.size
                color_mode = image.mode
                frame_count = getattr(image, "n_frames", 1)

                if image_format not in SUPPORTED_FORMATS:
                    raise ValueError(
                        f"Unsupported detected image format: {image_format}"
                    )

                if width <= 0 or height <= 0:
                    raise ValueError("Image has invalid dimensions.")

                pixel_count = width * height

                if pixel_count > max_pixels:
                    raise ValueError(
                        f"Image contains {pixel_count:,} pixels; "
                        f"the configured limit is {max_pixels:,}."
                    )

                # Verify the file structure before decoding it.
                image.verify()

            # verify() invalidates the image object, so reopen it.
            with Image.open(path) as image:
                image.load()

                exif_metadata = extract_exif_metadata(image)
                has_transparency = detect_transparency(image)

                if image_format == "TIFF" and frame_count > 1:
                    warnings_list.append(
                        "This TIFF contains multiple frames/pages. "
                        "The profile describes the first frame only."
                    )

                if width < 100 or height < 100:
                    warnings_list.append(
                        "Image dimensions are relatively small."
                    )

                if not exif_metadata:
                    warnings_list.append(
                        "No supported EXIF metadata was found."
                    )

                if path.suffix.lower() not in {
                    ".jpg", ".jpeg"
                } and image_format == "JPEG":
                    warnings_list.append(
                        "Detected JPEG content with a different extension."
                    )

                if thumbnail_directory is not None:
                    thumbnail = generate_thumbnail(
                        image=image,
                        source_hash=checksum,
                        output_directory=Path(thumbnail_directory),
                        thumbnail_size=thumbnail_size,
                    )
                    thumbnail_path = str(thumbnail)

        mime_type = Image.MIME.get(image_format, "application/octet-stream")

        profile = ImageProfile(
            file_name=path.name,
            file_path=str(path.resolve()),
            file_size_bytes=file_size,
            sha256=checksum,

            image_format=image_format,
            mime_type=mime_type,
            extension=path.suffix.lower(),

            width=width,
            height=height,
            aspect_ratio=round(width / height, 4),
            pixel_count=pixel_count,
            color_mode=color_mode,

            has_transparency=has_transparency,
            frame_count=frame_count,

            exif_metadata=exif_metadata,
            thumbnail_path=thumbnail_path,

            warnings=warnings_list,
            processing_status="completed",
            processed_at=datetime.now(timezone.utc).isoformat(),
        )

        return profile.to_dict()

    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
    ) as error:
        raise ValueError(
            f"Could not process image '{path.name}': {error}"
        ) from error


def save_image_profile(
    profile: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Save an image profile as JSON."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8") as file:
        json.dump(
            profile,
            file,
            indent=4,
            ensure_ascii=False,
        )

    return output