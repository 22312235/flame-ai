import os
import shutil
import tempfile

from pathlib import Path, PurePosixPath
from typing import BinaryIO

from storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """
    Local filesystem implementation of the storage interface.

    Files are stored beneath a single configured root directory.

    Example:
        root = data/storage

        object_key =
            investigations/investigation_001/original/report.pdf

        Physical path =
            data/storage/investigations/investigation_001/original/report.pdf
    """

    def __init__(
        self,
        root_directory: str | Path | None = None,
    ) -> None:

        if root_directory is None:
            root_directory = os.getenv(
                "FLAME_STORAGE_ROOT",
                "data/storage",
            )

        self.root_directory = Path(root_directory).expanduser().resolve()

        self.root_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _resolve_key(self, object_key: str) -> Path:
        """
        Convert a relative storage key into a safe absolute path.

        Prevents:
        - Absolute paths.
        - Parent directory traversal.
        - Paths escaping the configured storage root.
        """

        if not object_key or not object_key.strip():
            raise ValueError("Storage key cannot be empty.")

        if "\\" in object_key:
            raise ValueError("Storage keys must use forward slashes.")

        relative_path = PurePosixPath(object_key)

        if relative_path.is_absolute():
            raise ValueError("Absolute storage keys are not allowed.")

        if any(part in ("", ".", "..") for part in relative_path.parts):
            raise ValueError("Invalid storage key.")

        destination = (
            self.root_directory / Path(*relative_path.parts)
        ).resolve()

        try:
            destination.relative_to(self.root_directory)
        except ValueError as exc:
            raise ValueError(
                "Storage key resolves outside the storage root."
            ) from exc

        return destination

    def store_file(
        self,
        source_path: str | Path,
        object_key: str,
        overwrite: bool = False,
    ) -> str:

        source = Path(source_path).expanduser().resolve()

        if not source.exists():
            raise FileNotFoundError(
                f"Source file does not exist: {source}"
            )

        if not source.is_file():
            raise ValueError(
                f"Source path is not a regular file: {source}"
            )

        destination = self._resolve_key(object_key)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if source == destination:
            return object_key

        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"Storage object already exists: {object_key}"
            )

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=".flame_tmp_",
                delete=False,
            ) as temporary_file:

                temporary_path = Path(temporary_file.name)

                with source.open("rb") as source_file:
                    shutil.copyfileobj(
                        source_file,
                        temporary_file,
                    )

            os.replace(temporary_path, destination)

        except Exception:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

            raise

        return object_key

    def store_bytes(
        self,
        content: bytes,
        object_key: str,
        overwrite: bool = False,
    ) -> str:

        if not isinstance(content, bytes):
            raise TypeError("Content must be bytes.")

        destination = self._resolve_key(object_key)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"Storage object already exists: {object_key}"
            )

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=".flame_tmp_",
                delete=False,
            ) as temporary_file:

                temporary_path = Path(temporary_file.name)

                temporary_file.write(content)

            os.replace(temporary_path, destination)

        except Exception:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

            raise

        return object_key

    def open_file(self, object_key: str) -> BinaryIO:

        file_path = self.get_file_path(object_key)

        if not file_path.is_file():
            raise FileNotFoundError(
                f"Stored file does not exist: {object_key}"
            )

        return file_path.open("rb")

    def get_file_path(self, object_key: str) -> Path:

        return self._resolve_key(object_key)

    def exists(self, object_key: str) -> bool:

        file_path = self._resolve_key(object_key)

        return file_path.is_file()

    def get_size(self, object_key: str) -> int:

        file_path = self.get_file_path(object_key)

        if not file_path.is_file():
            raise FileNotFoundError(
                f"Stored file does not exist: {object_key}"
            )

        return file_path.stat().st_size

    def delete_file(self, object_key: str) -> bool:

        file_path = self.get_file_path(object_key)

        if not file_path.is_file():
            return False

        file_path.unlink()

        return True