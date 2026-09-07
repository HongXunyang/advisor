"""Shared, non-Qt CIF import infrastructure.

Both `scattering_geometry` and `structure_factor` consume a structure, so
validation/identity/capability logic lives here rather than in either
feature's `domain/` package. This package must never import from any
feature's `domain/` package (see folder-structure.mdc).
"""

from .cell_validation import validate_cell
from .cif_adapter import parse_cif_candidate
from .types import CifCapabilityReport, CifImportResult, StructureSource

__all__ = [
    "validate_cell",
    "parse_cif_candidate",
    "CifCapabilityReport",
    "CifImportResult",
    "StructureSource",
]
