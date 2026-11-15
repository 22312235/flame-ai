from __future__ import annotations

import hashlib
import re

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.file import File
from models.video import Video, VideoFrame, AudioTrack, Transcript

from database.repositories.file_repository import FileRepository
from storage import LocalStorage, StorageBackend


@dataclass
class VideoIngestionResult:
    """Summary of a video ingestion operation."""

    video: Video

    frames_created: int = 0
    scenes_created: int = 0
    keyframes_created: int = 0

    audio_tracks_created: int = 0
    transcripts_created: int = 0

    registered_files: int = 0

    warnings: list[str] = field(default_factory=list)


class VideoIngestion:
    """
    Persists video processor output in the database.

    Original and generated files are stored through StorageBackend.
    Database records contain storage keys, not absolute paths.

    This adapter does not commit transactions.
    """

    STORAGE_BACKEND = "local"

    # ---------------------------------------------------------
    # General helpers
    # ---------------------------------------------------------

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Convert values into JSON-compatible structures."""

        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, Path):
            return value.name

        if isinstance(value, dict):
            return {
                str(key): VideoIngestion._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                VideoIngestion._json_safe(item)
                for item in value
            ]

        if hasattr(value, "item"):
            try:
                return value.item()
            except (ValueError, TypeError):
                pass

        return str(value)

    @staticmethod
    def _calculate_sha256(path: Path) -> str:
        """Calculate a file checksum without loading it entirely."""

        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(
                lambda: file.read(1024 * 1024),
                b"",
            ):
                digest.update(chunk)

        return digest.hexdigest()

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Produce a safe filename for a storage key."""

        name = Path(filename).name
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        name = name.strip("._")

        return name or "artifact"

    @staticmethod
    def _get_existing_video(
        db: Session,
        file_id: UUID,
    ) -> Video | None:
        """Retrieve the video record associated with a source file."""

        return db.scalar(
            select(Video).where(Video.file_id == file_id)
        )

    # ---------------------------------------------------------
    # Derived file registration
    # ---------------------------------------------------------

    @staticmethod
    def _register_derived_file(
        db: Session,
        original_file: File,
        artifact_path: str | Path | None,
        file_category: str,
        storage: StorageBackend,
    ) -> tuple[File | None, bool]:
        """
        Copy a generated artifact into managed storage and register it.

        Returns:
            (registered_file, was_created)

        The storage key includes a content hash. Re-ingesting identical
        artifacts therefore reuses their existing database records.
        """

        if not artifact_path:
            return None, False

        path = Path(artifact_path)

        if not path.exists() or not path.is_file():
            return None, False

        if path.is_symlink():
            return None, False

        checksum = VideoIngestion._calculate_sha256(path)
        file_size = path.stat().st_size
        filename = VideoIngestion._safe_filename(path.name)

        storage_key = (
            f"investigations/{original_file.investigation_id}/"
            f"derived/{file_category}/"
            f"{checksum[:16]}_{filename}"
        )

        existing_file = db.scalar(
            select(File).where(
                File.parent_file_id == original_file.file_id,
                File.storage_key == storage_key,
            )
        )

        # Ensure the artifact exists in managed storage.
        if not storage.exists(storage_key):
            storage.store_file(
                source_path=path,
                object_key=storage_key,
            )

        if existing_file:
            existing_file.filename = filename
            existing_file.extension = path.suffix.lower()
            existing_file.detected_format = (
                path.suffix.lower().lstrip(".")
            )
            existing_file.file_category = file_category
            existing_file.file_role = "derived"
            existing_file.file_size_bytes = file_size
            existing_file.sha256 = checksum
            existing_file.storage_backend = (
                VideoIngestion.STORAGE_BACKEND
            )
            existing_file.storage_key = storage_key
            existing_file.storage_path = None
            existing_file.processing_status = "processed"

            db.flush()

            return existing_file, False

        registered_file = FileRepository.create(
            db=db,
            investigation_id=original_file.investigation_id,
            filename=filename,
            file_category=file_category,
            storage_path=None,
            storage_key=storage_key,
            storage_backend=VideoIngestion.STORAGE_BACKEND,
            file_size_bytes=file_size,
            extension=path.suffix.lower(),
            detected_format=path.suffix.lower().lstrip("."),
            file_role="derived",
            parent_file_id=original_file.file_id,
            sha256=checksum,
            processing_status="processed",
        )

        return registered_file, True

    # ---------------------------------------------------------
    # Existing extraction cleanup
    # ---------------------------------------------------------

    @staticmethod
    def _clear_existing_extraction(
        db: Session,
        video: Video,
    ) -> None:
        """
        Remove previous extraction metadata.

        Derived File records and their stored binaries are retained.
        This preserves provenance and allows matching artifacts to
        be reused during re-ingestion.
        """

        for frame in list(video.frames):
            db.delete(frame)

        for audio_track in list(video.audio_tracks):
            db.delete(audio_track)

        db.flush()

    # ---------------------------------------------------------
    # Video metadata
    # ---------------------------------------------------------

    @staticmethod
    def _save_video_metadata(
        db: Session,
        original_file: File,
        metadata: dict[str, Any],
        existing_video: Video | None,
    ) -> Video:
        """Create or update the main video record."""

        video_data = {
            "duration_seconds": float(
                metadata.get("duration_seconds") or 0
            ),
            "width": metadata.get("width"),
            "height": metadata.get("height"),
            "fps": float(metadata.get("fps") or 0),
            "frame_count": int(metadata.get("frame_count") or 0),
            "video_codec": metadata.get("video_codec"),
            "audio_codec": metadata.get("audio_codec"),
            "has_audio": bool(metadata.get("has_audio", False)),
            "metadata_json": VideoIngestion._json_safe(metadata),
        }

        if existing_video:
            for key, value in video_data.items():
                setattr(existing_video, key, value)

            db.flush()
            return existing_video

        video = Video(
            file_id=original_file.file_id,
            **video_data,
        )

        db.add(video)
        db.flush()

        return video

    # ---------------------------------------------------------
    # Regular frames and scene keyframes
    # ---------------------------------------------------------

    @staticmethod
    def _save_frame(
        db: Session,
        original_file: File,
        video: Video,
        frame_data: dict[str, Any],
        frame_type: str,
        warnings_list: list[str],
        storage: StorageBackend,
    ) -> tuple[VideoFrame, bool]:
        """Register a frame and create its database record."""

        registered_file = None
        file_created = False

        frame_path = frame_data.get("path")

        if frame_type in {"regular", "keyframe"}:
            registered_file, file_created = (
                VideoIngestion._register_derived_file(
                    db=db,
                    original_file=original_file,
                    artifact_path=frame_path,
                    file_category="image",
                    storage=storage,
                )
            )

            if registered_file is None:
                warnings_list.append(
                    f"Could not register {frame_type} image: "
                    f"{frame_path}"
                )

        timestamp = float(
            frame_data.get("timestamp_seconds") or 0
        )

        frame = VideoFrame(
            video_id=video.video_id,
            frame_type=frame_type,
            timestamp_seconds=timestamp,
            frame_file_id=(
                registered_file.file_id
                if registered_file else None
            ),
            frame_name=(
                frame_data.get("frame_id")
                or frame_data.get("frame_name")
            ),
            metadata_json=VideoIngestion._json_safe(
                {
                    key: value
                    for key, value in frame_data.items()
                    if key not in {"path", "frame_id"}
                }
            ),
        )

        db.add(frame)
        db.flush()

        return frame, file_created

    # ---------------------------------------------------------
    # Scene events
    # ---------------------------------------------------------

    @staticmethod
    def _save_scene(
        db: Session,
        video: Video,
        scene_data: dict[str, Any],
    ) -> VideoFrame:
        """Store a scene-change timestamp without requiring an image."""

        scene = VideoFrame(
            video_id=video.video_id,
            frame_type="scene",
            timestamp_seconds=float(
                scene_data.get("timestamp_seconds") or 0
            ),
            frame_file_id=None,
            frame_name=None,
            metadata_json=VideoIngestion._json_safe(scene_data),
        )

        db.add(scene)
        db.flush()

        return scene

    # ---------------------------------------------------------
    # Audio extraction
    # ---------------------------------------------------------

    @staticmethod
    def _save_audio(
        db: Session,
        original_file: File,
        video: Video,
        audio_data: dict[str, Any],
        warnings_list: list[str],
        storage: StorageBackend,
    ) -> tuple[AudioTrack, bool]:
        """Register extracted audio and create an audio-track record."""

        audio_file, file_created = (
            VideoIngestion._register_derived_file(
                db=db,
                original_file=original_file,
                artifact_path=audio_data.get("path"),
                file_category="audio",
                storage=storage,
            )
        )

        if audio_file is None:
            warnings_list.append(
                "Audio metadata was returned, but its file "
                "could not be registered."
            )

        audio_track = AudioTrack(
            video_id=video.video_id,
            audio_file_id=(
                audio_file.file_id if audio_file else None
            ),
            sample_rate=audio_data.get("sample_rate"),
            channels=audio_data.get("channels"),
            audio_format=audio_data.get("format"),
            metadata_json=VideoIngestion._json_safe(
                {
                    key: value
                    for key, value in audio_data.items()
                    if key != "path"
                }
            ),
        )

        db.add(audio_track)
        db.flush()

        return audio_track, file_created

    # ---------------------------------------------------------
    # Transcription
    # ---------------------------------------------------------

    @staticmethod
    def _save_transcription(
        db: Session,
        original_file: File,
        audio_track: AudioTrack,
        transcription_data: dict[str, Any],
        warnings_list: list[str],
        storage: StorageBackend,
    ) -> tuple[Transcript, bool]:
        """Register the transcript and persist its segments."""

        transcript_file, file_created = (
            VideoIngestion._register_derived_file(
                db=db,
                original_file=original_file,
                artifact_path=transcription_data.get("path"),
                file_category="transcript",
                storage=storage,
            )
        )

        if transcript_file is None:
            warnings_list.append(
                "Transcription metadata was returned, but its "
                "JSON file could not be registered."
            )

        segments = transcription_data.get("transcript") or []

        if not isinstance(segments, list):
            warnings_list.append(
                "Transcript segments were not returned as a list."
            )
            segments = []

        transcript_warnings = (
            transcription_data.get("warnings") or []
        )

        if not isinstance(transcript_warnings, list):
            transcript_warnings = [str(transcript_warnings)]

        warnings_list.extend(
            str(item) for item in transcript_warnings
        )

        transcript = Transcript(
            audio_track_id=audio_track.audio_track_id,
            transcript_file_id=(
                transcript_file.file_id
                if transcript_file else None
            ),
            language=transcription_data.get("language"),
            segments=VideoIngestion._json_safe(segments),
            warnings=VideoIngestion._json_safe(
                transcript_warnings
            ),
            metadata_json=VideoIngestion._json_safe(
                {
                    key: value
                    for key, value in transcription_data.items()
                    if key not in {
                        "path",
                        "transcript",
                        "warnings",
                    }
                }
            ),
        )

        db.add(transcript)
        db.flush()

        return transcript, file_created

    # ---------------------------------------------------------
    # Main ingestion method
    # ---------------------------------------------------------

    @staticmethod
    def ingest_video(
        db: Session,
        file_id: UUID,
        processor_result: dict[str, Any],
        storage: StorageBackend | None = None,
    ) -> VideoIngestionResult:
        """
        Persist the output returned by processing.video_processor.

        The method does not commit. The caller controls the
        transaction and must roll back if ingestion fails.
        """

        storage = storage or LocalStorage()

        original_file = FileRepository.get_by_id(
            db,
            file_id,
        )

        if original_file is None:
            raise ValueError(
                f"Original file does not exist: {file_id}"
            )

        if not isinstance(processor_result, dict):
            raise TypeError(
                "Video processor result must be a dictionary."
            )

        metadata = processor_result.get("metadata")

        if not isinstance(metadata, dict):
            raise ValueError(
                "Video processor result is missing valid metadata."
            )

        warnings_list = list(
            processor_result.get("warnings") or []
        )

        existing_video = VideoIngestion._get_existing_video(
            db,
            file_id,
        )

        if existing_video:
            VideoIngestion._clear_existing_extraction(
                db,
                existing_video,
            )

        video = VideoIngestion._save_video_metadata(
            db=db,
            original_file=original_file,
            metadata=metadata,
            existing_video=existing_video,
        )

        result = VideoIngestionResult(
            video=video,
            warnings=warnings_list,
        )

        # 1. Regular frames

        frames = processor_result.get("frames") or []

        for frame_data in frames:
            if not isinstance(frame_data, dict):
                result.warnings.append(
                    "Skipped an invalid regular-frame entry."
                )
                continue

            _, file_created = VideoIngestion._save_frame(
                db=db,
                original_file=original_file,
                video=video,
                frame_data=frame_data,
                frame_type="regular",
                warnings_list=result.warnings,
                storage=storage,
            )

            result.frames_created += 1

            if file_created:
                result.registered_files += 1

        # 2. Scene events

        scenes = processor_result.get("scenes") or []

        for scene_data in scenes:
            if not isinstance(scene_data, dict):
                result.warnings.append(
                    "Skipped an invalid scene entry."
                )
                continue

            VideoIngestion._save_scene(
                db=db,
                video=video,
                scene_data=scene_data,
            )

            result.scenes_created += 1

        # 3. Scene keyframes

        keyframes = processor_result.get("scene_keyframes") or []

        for frame_data in keyframes:
            if not isinstance(frame_data, dict):
                result.warnings.append(
                    "Skipped an invalid scene-keyframe entry."
                )
                continue

            _, file_created = VideoIngestion._save_frame(
                db=db,
                original_file=original_file,
                video=video,
                frame_data=frame_data,
                frame_type="keyframe",
                warnings_list=result.warnings,
                storage=storage,
            )

            result.keyframes_created += 1

            if file_created:
                result.registered_files += 1

        # 4. Extracted audio

        audio_data = processor_result.get("audio")
        audio_track = None

        if audio_data:
            if not isinstance(audio_data, dict):
                result.warnings.append(
                    "Audio output has an invalid structure."
                )
            else:
                audio_track, file_created = (
                    VideoIngestion._save_audio(
                        db=db,
                        original_file=original_file,
                        video=video,
                        audio_data=audio_data,
                        warnings_list=result.warnings,
                        storage=storage,
                    )
                )

                result.audio_tracks_created += 1

                if file_created:
                    result.registered_files += 1

        # 5. Transcription

        transcription_data = processor_result.get("transcription")

        if transcription_data:
            if not isinstance(transcription_data, dict):
                result.warnings.append(
                    "Transcription output has an invalid structure."
                )

            elif audio_track is None:
                result.warnings.append(
                    "Transcription could not be associated with "
                    "an audio track."
                )

            else:
                _, file_created = (
                    VideoIngestion._save_transcription(
                        db=db,
                        original_file=original_file,
                        audio_track=audio_track,
                        transcription_data=transcription_data,
                        warnings_list=result.warnings,
                        storage=storage,
                    )
                )

                result.transcripts_created += 1

                if file_created:
                    result.registered_files += 1

        # 6. Update original file status

        FileRepository.update_status(
            db,
            file_id,
            "warning" if result.warnings else "processed",
        )

        db.flush()

        return result