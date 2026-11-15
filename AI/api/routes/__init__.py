"""API route registration for the Flame backend."""

from .catalog import router as catalog_router
from .filtering import router as filtering_router
from .analysis import router as analysis_router


__all__ = [
    "catalog_router",
    "filtering_router",
    "analysis_router",
]