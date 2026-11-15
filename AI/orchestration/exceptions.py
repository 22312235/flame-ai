class OrchestrationError(Exception):
    """Base exception for errors raised by the processing orchestrator."""


class ProcessorNotRegisteredError(OrchestrationError):
    """Raised when no processor is registered for a requested processor type."""

    def __init__(self, processor_type: str):
        self.processor_type = processor_type
        super().__init__(
            f"No processor is registered for type '{processor_type}'."
        )


class ProcessingJobError(OrchestrationError):
    """Raised when a processing job cannot be retrieved or executed."""

    def __init__(self, job_id: str, message: str):
        self.job_id = job_id
        super().__init__(f"Processing job '{job_id}': {message}")


class SourceFileNotFoundError(OrchestrationError):
    """Raised when a registered source file cannot be found in storage."""

    def __init__(self, file_id: str, storage_key: str):
        self.file_id = file_id
        self.storage_key = storage_key
        super().__init__(
            f"Source file '{file_id}' could not be found "
            f"at storage key '{storage_key}'."
        )


class ProcessorExecutionError(OrchestrationError):
    """Raised when a processor fails while processing a source file."""

    def __init__(self, processor_type: str, file_id: str, message: str):
        self.processor_type = processor_type
        self.file_id = file_id
        super().__init__(
            f"Processor '{processor_type}' failed for file "
            f"'{file_id}': {message}"
        )


class IngestionError(OrchestrationError):
    """Raised when a processor result cannot be persisted."""

    def __init__(self, processor_type: str, file_id: str, message: str):
        self.processor_type = processor_type
        self.file_id = file_id
        super().__init__(
            f"Ingestion failed for processor '{processor_type}' "
            f"and file '{file_id}': {message}"
        )