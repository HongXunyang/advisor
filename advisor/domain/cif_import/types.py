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
    # Optional, informational-only provenance/conditions -- extracted from the
    # same already-parsed CIF keys `formula`/`space_group` come from (see
    # cif_adapter.py). Never used for capability/validity decisions; absence
    # is not a failure. Kept on StructureSource (rather than a library-only
    # side structure) because they describe the parsed CIF itself, so an
    # unsaved import's CifDetailsDialog can show them too, not only a saved
    # library record's.
    source_id: Optional[str] = None
    doi: Optional[str] = None
    temperature_k: Optional[float] = None
    pressure_kpa: Optional[float] = None
    # Presentation-only provenance for the *current session* (REVIEW.md
    # finding #3): "import" for an ordinary user-selected file, or
    # "bundled_example" when this source was loaded via AppController.
    # load_bundled_example(). `citation` carries the bundled example's
    # attribution text so it's visible in CifDetailsDialog for the live
    # session even when remembering is disabled (and there is therefore no
    # library record to fall back on for this information). Neither field
    # is derived by cif_adapter.py from CIF content -- both are set by
    # AppController after the same validated parse, never by a second
    # parser, and never affect identity/capability.
    origin: str = "import"
    citation: Optional[str] = None

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
    # Populated only by AppController (the accept side of the pipeline), never
    # by CifImportService/cif_adapter (the prepare side) -- a side note about
    # whether this accepted structure could also be saved to the local
    # library, kept separate from `message` (the scientific readiness verdict).
    library_note: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status in ("ready", "ready_geometry_only", "unchanged")
