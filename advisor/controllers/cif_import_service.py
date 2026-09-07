"""Thin, stateless orchestration for turning a user-selected path into a
validated `CifImportResult`.

Owns no accepted application state -- this is the "prepare" half of the
prepare -> accept -> invalidate -> initialize flow; `AppController` is the
"accept" half (see `AppController.import_cif`).
"""

from advisor.domain.cif_import import io as cif_io
from advisor.domain.cif_import.cif_adapter import parse_cif_candidate
from advisor.domain.cif_import.types import CifImportResult


class CifImportService:
    """Reads a candidate CIF and validates it without touching accepted state."""

    def prepare_from_path(self, path: str) -> CifImportResult:
        try:
            raw_bytes = cif_io.read_cif_bytes(path)
        except cif_io.CifReadError as exc:
            return CifImportResult(status="rejected", message=str(exc), error=str(exc))

        digest = cif_io.content_digest(raw_bytes)

        try:
            effective_path = cif_io.materialize_snapshot(raw_bytes, path)
        except OSError as exc:
            return CifImportResult(
                status="rejected",
                message=f"Could not prepare '{path}' for import: {exc}",
                error=str(exc),
            )

        result = parse_cif_candidate(
            raw_bytes=raw_bytes,
            content_digest=digest,
            display_path=path,
            effective_path=effective_path,
        )
        if result.status == "rejected":
            # A rejected candidate never becomes the accepted structure, so
            # nothing else owns this snapshot -- clean it up here rather
            # than leaking a temp directory on every rejected selection.
            cif_io.cleanup_snapshot(effective_path)
        return result
