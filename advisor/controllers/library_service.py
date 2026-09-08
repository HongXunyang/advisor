"""Qt-adjacent orchestration for the local structure library (REQUIREMENT_2).

This is the only file in the library feature that imports
`PyQt5.QtCore.QStandardPaths` -- everything under `advisor.domain.library` is
plain Python. `AppController` owns one `LibraryService` instance, mirroring
how it already owns one `CifImportService`.
"""

import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Callable, List, Optional

from PyQt5.QtCore import QStandardPaths

from advisor.domain.cif_import.types import StructureSource
from advisor.domain.library import io as library_io
from advisor.domain.library.repository import LibraryRepository
from advisor.domain.library.types import (
    LibraryError,
    LibraryOutcome,
    LibraryRecord,
    LibraryUnavailableError,
)

_REMEMBER_PREFERENCE_KEY = "remember_imports_enabled"


def default_root() -> str:
    """The stable per-user application-data directory for this app.

    Resolved via Qt's own platform mechanism -- `app.setApplicationName(...)`
    (see `advisor/app.py`) is already set before `AppController`/this service
    is constructed, which is sufficient for a stable path across restarts and
    app updates. A standalone function (not a method) so tests can
    monkeypatch it directly to redirect every test's library to an isolated
    `tmp_path`, without touching this module's other code.
    """
    return QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)


@contextmanager
def _translate_storage_errors():
    """Any failure reaching here after a successful open (a deleted/locked
    database file, a disk that went away mid-session, etc.) must surface as
    an actionable `LibraryError`, never a raw `sqlite3`/`OSError` escaping
    into UI code that only expects the former."""
    try:
        yield
    except LibraryError:
        raise
    except (sqlite3.Error, OSError) as exc:
        raise LibraryError(f"The local structure library is unavailable: {exc}") from exc


class LibraryService:
    """Best-effort durable storage for accepted CIF structures.

    `record_accepted()` never raises -- a storage failure must never be
    allowed to affect the current session's accepted structure (see
    `AppController._record_in_library`). Every other method may raise
    `LibraryError`/`LibraryUnavailableError` for the caller to translate into
    an actionable message.
    """

    def __init__(self, root_dir: Optional[str] = None, clock: Optional[Callable[[], float]] = None):
        self._root_dir = root_dir or default_root()
        self._clock = clock or time.time
        self._repository: Optional[LibraryRepository] = None
        self._unavailable_reason: Optional[str] = None
        self._open()

    def _open(self):
        try:
            self._repository = LibraryRepository(self._root_dir, clock=self._clock)
            self._unavailable_reason = None
        except LibraryUnavailableError as exc:
            self._repository = None
            self._unavailable_reason = str(exc)
        except Exception as exc:  # noqa: BLE001 -- an optional library must never
            # block application startup, regardless of what specifically went
            # wrong opening it (belt-and-suspenders: LibraryRepository itself
            # should already translate every anticipated failure mode into
            # LibraryUnavailableError/LibraryCorruptionDetected, but nothing
            # about "the library couldn't be opened" may ever propagate as an
            # unhandled exception this far up).
            self._repository = None
            self._unavailable_reason = f"The local structure library could not be opened: {exc}"

    def retry_open(self) -> bool:
        """Re-attempt opening the library (e.g. after the user freed disk
        space or fixed a permissions problem) without restarting the app.
        Returns the resulting `is_available`. Safe to call whether or not
        the library is currently available -- a no-op-ish re-open when it's
        already open."""
        self._open()
        return self.is_available

    @property
    def is_available(self) -> bool:
        return self._repository is not None

    @property
    def unavailable_reason(self) -> Optional[str]:
        return self._unavailable_reason

    def _require_repository(self) -> LibraryRepository:
        if self._repository is None:
            raise LibraryUnavailableError(
                self._unavailable_reason or "The local structure library is unavailable."
            )
        return self._repository

    # -- preference -----------------------------------------------------

    def remember_enabled(self) -> bool:
        if self._repository is None:
            return True
        with _translate_storage_errors():
            return self._repository.get_preference(_REMEMBER_PREFERENCE_KEY, "1") == "1"

    def set_remember_enabled(self, enabled: bool) -> None:
        with _translate_storage_errors():
            self._require_repository().set_preference(_REMEMBER_PREFERENCE_KEY, "1" if enabled else "0")

    # -- accept-time hook -------------------------------------------------

    def record_accepted(self, source: StructureSource, origin: str = "import") -> LibraryOutcome:
        """Best-effort persistence of one accepted CIF-derived structure.

        Never raises: any failure is reported as `LibraryOutcome(status="error")`
        so the caller can tell the user their session is fine but nothing was
        saved, rather than the acceptance itself failing.

        The remembering preference gates only *creating a new* managed copy.
        If a record for this exact content already exists, it is always
        touched (last-used timestamp + refreshed extracted metadata) even
        when remembering is currently off -- turning remembering off means
        "don't start saving new things," not "stop tracking usage of
        something already saved" (REQUIREMENT_2: reimporting/reselecting
        identical content, including via the library picker, must update
        usage metadata regardless of the toggle).
        """
        if source.source_kind != "cif" or source.content_digest is None or source.effective_path is None:
            return LibraryOutcome(status="skipped", detail="not a CIF-derived source")

        try:
            repository = self._require_repository()
            existing = repository.find_by_identity(source.content_digest, source.data_block)
            if existing is None and not self.remember_enabled():
                return LibraryOutcome(status="disabled")

            with open(source.effective_path, "rb") as handle:
                raw_bytes = handle.read()

            managed_relative_path = library_io.write_managed_file_atomic(
                self._root_dir, source.content_digest, raw_bytes
            )
            record = repository.upsert_accepted(
                content_hash=source.content_digest,
                data_block=source.data_block,
                managed_relative_path=managed_relative_path,
                original_filename=source.display_name,
                source_origin=origin,
                metadata={
                    "formula": source.formula,
                    "space_group": source.space_group,
                    "cell_a": source.a, "cell_b": source.b, "cell_c": source.c,
                    "cell_alpha": source.alpha, "cell_beta": source.beta, "cell_gamma": source.gamma,
                    "source_id": source.source_id,
                    "doi": source.doi,
                    "temperature_k": source.temperature_k,
                    "pressure_kpa": source.pressure_kpa,
                    "geometry_ok": source.capabilities.geometry_ok,
                    "structure_factor_ok": source.capabilities.structure_factor_ok,
                    "capability_message": source.capabilities.message,
                },
            )
            return LibraryOutcome(status="saved" if existing is None else "updated", record=record)
        except Exception as exc:  # noqa: BLE001 -- storage must never break acceptance
            return LibraryOutcome(status="error", detail=str(exc))

    # -- retrieval ----------------------------------------------------------

    def list_recent(self, limit: int = 10) -> List[LibraryRecord]:
        with _translate_storage_errors():
            return self._require_repository().list_recent(limit)

    def list_starred(self) -> List[LibraryRecord]:
        with _translate_storage_errors():
            return self._require_repository().list_starred()

    def list_all(self) -> List[LibraryRecord]:
        with _translate_storage_errors():
            return self._require_repository().list_all()

    def search(self, query: str) -> List[LibraryRecord]:
        from advisor.domain.library.normalization import normalize_search_text

        needle = normalize_search_text(query)
        if not needle:
            return self.list_all()
        results = []
        for record in self.list_all():
            haystack = " ".join(
                normalize_search_text(text or "")
                for text in (
                    record.display_name,
                    record.original_filename,
                    record.formula,
                    record.source_id,
                    record.note,
                )
            )
            if needle in haystack:
                results.append(record)
        return results

    def get(self, record_id: str) -> Optional[LibraryRecord]:
        with _translate_storage_errors():
            return self._require_repository().get(record_id)

    def resolve_managed_path(self, record_id: str) -> str:
        """Verify a saved record's managed file still matches its recorded
        hash and return its absolute path, ready to hand to
        `AppController.import_cif()`. Raises `LibraryError` (actionable,
        never a bare OSError) if the file is missing or has changed."""
        record = self.get(record_id)
        if record is None:
            raise LibraryError("This saved structure no longer exists in the library.")
        library_io.read_and_verify(self._root_dir, record.managed_relative_path, record.content_hash)
        return library_io.managed_absolute_path(self._root_dir, record.managed_relative_path)

    # -- editing / removal ----------------------------------------------

    def set_starred(self, record_id: str, starred: bool) -> None:
        with _translate_storage_errors():
            self._require_repository().set_starred(record_id, starred)

    def rename(self, record_id: str, display_name: Optional[str]) -> None:
        with _translate_storage_errors():
            self._require_repository().rename(record_id, display_name)

    def set_note(self, record_id: str, note: Optional[str]) -> None:
        with _translate_storage_errors():
            self._require_repository().set_note(record_id, note)

    def remove(self, record_id: str) -> None:
        """Delete ADVISOR's saved copy (file, then row). Never touches the
        user's original external file -- that path isn't even stored.

        Deletes the managed *file* first and only removes the database row
        once that succeeds (or the file was already absent, which still
        counts as "no managed copy left"). A `remove()` that reports success
        must actually match the filesystem result: dropping the row first
        and swallowing a subsequent file-deletion failure would silently
        leave ADVISOR's exact managed copy on disk with no record pointing
        to it, and no way for the user to retry.
        """
        with _translate_storage_errors():
            repository = self._require_repository()
            record = repository.get(record_id)
            if record is None:
                return
            absolute_path = library_io.managed_absolute_path(self._root_dir, record.managed_relative_path)
            try:
                os.remove(absolute_path)
            except FileNotFoundError:
                pass  # already gone -- still a successful removal
            except OSError as exc:
                raise LibraryError(f"Could not delete the saved file: {exc}") from exc
            repository.remove(record_id)
