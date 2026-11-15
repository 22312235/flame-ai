from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageBackend(ABC):
    """
    Abstract interface for file storage providers.

    All storage implementations must provide these operations.
    This keeps the application independent of the underlying
    storage technology.
    """

    @abstractmethod
    def store_file(
        self,
        source_path: str | Path,
        object_key: str,
        overwrite: bool = False,
    ) -> str:
        """
        Store an existing file.

        Args:
            source_path: Path of the source file.
            object_key: Unique storage identifier.
            overwrite: Whether an existing object can be replaced.

        Returns:
            The storage key identifying the stored file.
        """
        raise NotImplementedError

    @abstractmethod
    def store_bytes(
        self,
        content: bytes,
        object_key: str,
        overwrite: bool = False,
    ) -> str:
        """
        Store binary content.

        Args:
            content: File content in bytes.
            object_key: Unique storage identifier.
            overwrite: Whether an existing object can be replaced.

        Returns:
            The storage key identifying the stored file.
        """
        raise NotImplementedError

    @abstractmethod
    def open_file(self, object_key: str) -> BinaryIO:
        """
        Open a stored file in binary mode.

        The caller is responsible for closing the returned stream.
        """
        raise NotImplementedError

    @abstractmethod
    def get_file_path(self, object_key: str) -> Path:
        """
        Resolve a storage key to a local filesystem path.

        This is useful for processors that require a physical path.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, object_key: str) -> bool:
        """Check whether a stored file exists."""
        raise NotImplementedError

    @abstractmethod
    def get_size(self, object_key: str) -> int:
        """Return the stored file size in bytes."""
        raise NotImplementedError

    @abstractmethod
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a stored file.

        Returns:
            True if the file was deleted, False if it did not exist.
        """
        raise NotImplementedError