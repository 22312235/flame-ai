from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session


# =========================================================
# STANDARDIZED CALLABLE INTERFACES
# =========================================================

ProcessorCallable = Callable[
    [Path, dict[str, Any]],
    Any,
]

IngestionCallable = Callable[
    [Session, UUID, Any],
    Any,
]


# =========================================================
# PROCESSOR REGISTRATION
# =========================================================

@dataclass(frozen=True)
class ProcessorRegistration:
    """
    Defines the processing and persistence functions
    associated with a processor type.
    """

    processor_type: str

    processor: ProcessorCallable

    ingestion_adapter: IngestionCallable

    description: str = ""


# =========================================================
# PROCESSOR REGISTRY
# =========================================================

class ProcessorRegistry:
    """
    Central registry mapping processor identifiers
    to their processing functions and ingestion adapters.

    The registry does not execute processors.
    It only manages their registration and retrieval.
    """

    def __init__(self):
        self._processors: dict[str, ProcessorRegistration] = {}

    # =====================================================
    # REGISTER
    # =====================================================

    def register(
        self,
        processor_type: str,
        processor: ProcessorCallable,
        ingestion_adapter: IngestionCallable,
        description: str = "",
        replace: bool = False,
    ) -> None:
        """
        Register a processor and its ingestion adapter.

        Args:
            processor_type:
                Identifier used by processing jobs.

            processor:
                Function responsible for processing a file.

            ingestion_adapter:
                Function responsible for persisting
                the processor's output.

            description:
                Optional description of the processor.

            replace:
                Whether an existing registration can
                be replaced.
        """

        if not processor_type or not processor_type.strip():
            raise ValueError("processor_type cannot be empty.")

        if not callable(processor):
            raise TypeError("processor must be callable.")

        if not callable(ingestion_adapter):
            raise TypeError("ingestion_adapter must be callable.")

        key = self._normalize_processor_type(processor_type)

        if key in self._processors and not replace:
            raise ValueError(
                f"Processor '{key}' is already registered."
            )

        self._processors[key] = ProcessorRegistration(
            processor_type=key,
            processor=processor,
            ingestion_adapter=ingestion_adapter,
            description=description,
        )

    # =====================================================
    # RETRIEVE
    # =====================================================

    def get(
        self,
        processor_type: str,
    ) -> ProcessorRegistration:
        """
        Retrieve a processor registration.

        Raises:
            KeyError if the processor is not registered.
        """

        key = self._normalize_processor_type(processor_type)

        registration = self._processors.get(key)

        if registration is None:
            raise KeyError(
                f"No processor registered for type '{key}'."
            )

        return registration

    def exists(self, processor_type: str) -> bool:
        """Check whether a processor is registered."""

        key = self._normalize_processor_type(processor_type)

        return key in self._processors

    # =====================================================
    # REMOVE
    # =====================================================

    def unregister(self, processor_type: str) -> bool:
        """
        Remove a processor registration.

        Returns:
            True if removed, False if it did not exist.
        """

        key = self._normalize_processor_type(processor_type)

        if key not in self._processors:
            return False

        del self._processors[key]

        return True

    # =====================================================
    # LIST
    # =====================================================

    def list_processors(self) -> list[ProcessorRegistration]:
        """Return all registered processors."""

        return list(self._processors.values())

    def list_processor_types(self) -> list[str]:
        """Return all registered processor identifiers."""

        return sorted(self._processors.keys())

    # =====================================================
    # INTERNAL
    # =====================================================

    @staticmethod
    def _normalize_processor_type(processor_type: str) -> str:
        """Normalize processor identifiers."""

        if not isinstance(processor_type, str):
            raise TypeError("processor_type must be a string.")

        return processor_type.strip().lower()