class CatalogNotFoundError(Exception):
    """Raised when an investigation catalog does not exist."""


class CatalogRepositoryError(Exception):
    """Raised when catalog persistence or retrieval fails."""