"""Non-Qt types for the CIF import pipeline.

`StructureSource` is the single, immutable snapshot of "the structure
currently accepted by the app" that every consumer (InitWindow, both feature
controllers) reads cell/atomic data from. It is never mutated in place -- a
structure change is always "replace the reference", never "edit the fields",
which is what lets consumers detect a no-op reselection by comparing
`identity_key()` rather than by comparing filenames or cell values.

No PyQt or feature-domain imports here (see folder-structure.mdc): this
package is shared, plain-Python infrastructure both features depend on.
"""

from dataclasses import dataclass
from typing import Literal, Optional, Tuple

ImportStatus = Literal["ready", "ready_geometry_only", "unchanged", "rejected"]
SourceKind = Literal["cif", "manual"]


@dataclass(frozen=True)
class CifCapabilityReport:
    """What a validated structure can be used for, and why not otherwise."""

    geometry_ok: bool
    structure_factor_ok: bool
    reasons: Tuple[str, ...] = ()
    message: str = ""


@dataclass(frozen=True)
class StructureSource:
    """Identity + full-precision data for one accepted structure."""

    content_digest: Optional[str]
    data_block: Optional[str]
    display_name: str
    display_path: str
    formula: Optional[str]
    space_group: Optional[str]
    a: float
    b: float
    c: float
    alpha: float
    beta: float
    gamma: float
    capabilities: CifCapabilityReport
    effective_path: Optional[str]
    source_kind: SourceKind

    def identity_key(self) -> Tuple[Optional[str], Optional[str]]:
        """(content_digest, data_block) -- used to detect a no-op reselection.

        Two `StructureSource`s with the same identity_key represent the same
        scientific input even if selected via a different display path.
        """
        return (self.content_digest, self.data_block)

    def cell_params(self) -> Tuple[float, float, float, float, float, float]:
        return (self.a, self.b, self.c, self.alpha, self.beta, self.gamma)


@dataclass(frozen=True)
class CifImportResult:
    """Outcome of attempting to prepare a candidate CIF for acceptance.

    Producing this never mutates any accepted application state -- see
    `advisor.controllers.cif_import_service.CifImportService`.
    """

    status: ImportStatus
    message: str
    source: Optional[StructureSource] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status in ("ready", "ready_geometry_only", "unchanged")
