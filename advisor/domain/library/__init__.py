"""Shared, non-Qt local structure library infrastructure (REQUIREMENT_2).

Durable identity/metadata storage for previously-accepted CIFs. Mirrors
`advisor.domain.cif_import`'s layering: no PyQt imports, no feature-domain
imports. `advisor.controllers.library_service.LibraryService` is the
Qt-adjacent orchestration layer built on top of this package.
"""

from .bundled_examples import (
    BundledExample,
    EXAMPLES,
    find_example_by_content_hash,
    get_bundled_example,
    resource_absolute_path,
)
from .normalization import normalize_search_text
from .repository import LibraryRepository
from .types import LibraryCorruptionDetected, LibraryError, LibraryOutcome, LibraryRecord, LibraryUnavailableError

__all__ = [
    "BundledExample",
    "EXAMPLES",
    "find_example_by_content_hash",
    "get_bundled_example",
    "resource_absolute_path",
    "normalize_search_text",
    "LibraryRepository",
    "LibraryRecord",
    "LibraryOutcome",
    "LibraryError",
    "LibraryUnavailableError",
    "LibraryCorruptionDetected",
]
