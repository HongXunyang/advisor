"""Non-Qt types for the local structure library (REQUIREMENT_2).

`LibraryRecord` is the plain-Python projection of one row of the
`structures` table (see `repository.py`) -- durable identity/metadata for a
CIF ADVISOR has saved a copy of. It is a separate type from
`advisor.domain.cif_import.types.StructureSource`: a `StructureSource` is
"the structure currently accepted this session" (may or may not be backed by
a saved library entry, e.g. remembering disabled, or a manual lattice), while
a `LibraryRecord` is "a durable row in the library," independent of whether
it is the currently accepted structure.

No PyQt imports here (see folder-structure.mdc): this package is shared,
plain-Python infrastructure, mirroring `cif_import/`'s own layering.
"""

from dataclasses import dataclass
from typing import Literal, Optional

SourceOrigin = Literal["import", "bundled_example"]
OutcomeStatus = Literal["saved", "updated", "skipped", "disabled", "error"]


@dataclass(frozen=True)
class LibraryRecord:
    """One durable row: identity, storage location, and metadata.

    `display_name`/`note` are user edits, kept separate from the
    CIF-extracted fields (`formula`, `space_group`, cell, `source_id`,
    `doi`, `temperature_k`, `pressure_kpa`) which are refreshed on every
    reimport of identical content but never overwrite a user's own edits.
    """

    id: str
    content_hash: str
    data_block: Optional[str]
    managed_relative_path: str
    original_filename: str
    display_name: Optional[str]
    note: Optional[str]
    starred: bool
    imported_at: float
    last_used_at: float
    source_origin: SourceOrigin
    formula: Optional[str]
    space_group: Optional[str]
    cell_a: Optional[float]
    cell_b: Optional[float]
    cell_c: Optional[float]
    cell_alpha: Optional[float]
    cell_beta: Optional[float]
    cell_gamma: Optional[float]
    source_id: Optional[str]
    doi: Optional[str]
    temperature_k: Optional[float]
    pressure_kpa: Optional[float]
    geometry_ok: Optional[bool]
    structure_factor_ok: Optional[bool]
    capability_message: Optional[str]
    schema_version: int

    def effective_display_name(self) -> str:
        return self.display_name or self.original_filename


@dataclass(frozen=True)
class LibraryOutcome:
    """Result of attempting to persist one accepted `StructureSource`.

    - "saved": a brand-new managed copy/record was created.
    - "updated": a record for this exact content already existed and was
      touched (last-used timestamp + refreshed extracted metadata) --
      distinguished from "saved" so a reopened/reselected structure isn't
      reported as newly "Added."
    - "skipped": the source has no bytes (manual lattice) -- not an error,
      nothing to report to the user.
    - "disabled": remembering is off *and* no record for this content
      already existed, so no new copy was created. An already-saved
      record is still "updated" even with remembering off -- turning
      remembering off only stops new saves, not usage-tracking of
      something already saved.
    - "error": storage failed (read-only dir, full disk, corrupt library);
      the accepted structure itself is unaffected.
    """

    status: OutcomeStatus
    record: Optional[LibraryRecord] = None
    detail: Optional[str] = None


class LibraryError(Exception):
    """Actionable library storage failure (missing/corrupt managed file,
    unavailable storage root, etc.) -- never silently substituted for."""


class LibraryUnavailableError(LibraryError):
    """The library's storage root/database could not be opened this
    session (e.g. corrupted DB, unknown schema version, permissions)."""


class LibraryCorruptionDetected(LibraryUnavailableError):
    """`PRAGMA integrity_check` failed or the schema is unrecognized.

    The offending file is never deleted/recreated -- this is raised so the
    caller can surface an actionable message while preserving whatever is
    on disk for potential manual recovery.
    """
