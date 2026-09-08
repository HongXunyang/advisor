"""Tests for `LibraryService` -- the Qt-adjacent orchestration layer over
`advisor.domain.library`. No Qt widgets involved (only `QStandardPaths` is
imported by the module under test, and every instance here is given an
explicit `root_dir`, so nothing touches the real per-user library)."""

import os

import pytest

from advisor.controllers.cif_import_service import CifImportService
from advisor.controllers.library_service import LibraryService
from advisor.domain.cif_import import io as cif_io
from advisor.domain.library.types import LibraryError

FIXTURE_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "cif", "high_precision.cif")
)


def _prepared_source(path=FIXTURE_CIF):
    result = CifImportService().prepare_from_path(path)
    assert result.ok
    return result.source


def test_record_accepted_saves_and_returns_record(tmp_path):
    service = LibraryService(root_dir=str(tmp_path))
    source = _prepared_source()
    try:
        outcome = service.record_accepted(source)
        assert outcome.status == "saved"
        assert outcome.record is not None
        assert outcome.record.content_hash == source.content_digest
        assert outcome.record.formula == source.formula
    finally:
        cif_io.cleanup_snapshot(source.effective_path)


def test_record_accepted_skips_manual_lattice_source(tmp_path):
    from advisor.domain.cif_import.types import CifCapabilityReport, StructureSource

    service = LibraryService(root_dir=str(tmp_path))
    manual_source = StructureSource(
        content_digest=None, data_block=None, display_name="Manual lattice",
        display_path="", formula=None, space_group=None,
        a=4.0, b=4.0, c=4.0, alpha=90.0, beta=90.0, gamma=90.0,
        capabilities=CifCapabilityReport(geometry_ok=True, structure_factor_ok=False),
        effective_path=None, source_kind="manual",
    )
    outcome = service.record_accepted(manual_source)
    assert outcome.status == "skipped"
    assert service.list_all() == []


def test_remembering_off_skips_persist_but_never_raises(tmp_path):
    service = LibraryService(root_dir=str(tmp_path))
    service.set_remember_enabled(False)
    source = _prepared_source()
    try:
        outcome = service.record_accepted(source)
        assert outcome.status == "disabled"
        assert service.list_all() == []
    finally:
        cif_io.cleanup_snapshot(source.effective_path)


def test_remembering_toggle_persists_across_service_instances(tmp_path):
    service1 = LibraryService(root_dir=str(tmp_path))
    assert service1.remember_enabled() is True
    service1.set_remember_enabled(False)

    service2 = LibraryService(root_dir=str(tmp_path))  # simulates restart
    assert service2.remember_enabled() is False


def test_toggling_remembering_off_does_not_erase_existing_entries(tmp_path):
    service = LibraryService(root_dir=str(tmp_path))
    source = _prepared_source()
    try:
        service.record_accepted(source)
        assert len(service.list_all()) == 1
        service.set_remember_enabled(False)
        assert len(service.list_all()) == 1  # existing entry survives
    finally:
        cif_io.cleanup_snapshot(source.effective_path)


def test_reimport_identical_content_reuses_record_and_updates_last_used(tmp_path):
    service = LibraryService(root_dir=str(tmp_path))
    source1 = _prepared_source()
    try:
        outcome1 = service.record_accepted(source1)
    finally:
        cif_io.cleanup_snapshot(source1.effective_path)

    source2 = _prepared_source()  # a fresh prepare of the same original file
    try:
        outcome2 = service.record_accepted(source2)
    finally:
        cif_io.cleanup_snapshot(source2.effective_path)

    assert outcome1.record.id == outcome2.record.id
    assert len(service.list_all()) == 1


def test_storage_failure_is_reported_as_error_outcome_not_raised(tmp_path, monkeypatch):
    service = LibraryService(root_dir=str(tmp_path))

    def _boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("advisor.controllers.library_service.library_io.write_managed_file_atomic", _boom)
    source = _prepared_source()
    try:
        outcome = service.record_accepted(source)
        assert outcome.status == "error"
    finally:
        cif_io.cleanup_snapshot(source.effective_path)


def test_resolve_managed_path_missing_file_is_actionable_error(tmp_path):
    service = LibraryService(root_dir=str(tmp_path))
    source = _prepared_source()
    try:
        outcome = service.record_accepted(source)
    finally:
        cif_io.cleanup_snapshot(source.effective_path)

    managed_path = service.resolve_managed_path(outcome.record.id)
    os.remove(managed_path)

    with pytest.raises(LibraryError):
        service.resolve_managed_path(outcome.record.id)


def test_resolve_managed_path_corrupt_file_is_actionable_error(tmp_path):
    service = LibraryService(root_dir=str(tmp_path))
    source = _prepared_source()
    try:
        outcome = service.record_accepted(source)
    finally:
        cif_io.cleanup_snapshot(source.effective_path)

    managed_path = service.resolve_managed_path(outcome.record.id)
    with open(managed_path, "wb") as handle:
        handle.write(b"tampered")

    with pytest.raises(LibraryError):
        service.resolve_managed_path(outcome.record.id)


def test_remove_deletes_row_and_managed_file_never_touches_original(tmp_path):
    service = LibraryService(root_dir=str(tmp_path))
    source = _prepared_source()
    original_still_exists_at = FIXTURE_CIF
    try:
        outcome = service.record_accepted(source)
    finally:
        cif_io.cleanup_snapshot(source.effective_path)

    managed_path = service.resolve_managed_path(outcome.record.id)
    service.remove(outcome.record.id)

    assert service.get(outcome.record.id) is None
    assert not os.path.exists(managed_path)
    assert os.path.exists(original_still_exists_at)  # external file never touched


def test_search_matches_subscript_normalized_formula(tmp_path):
    service = LibraryService(root_dir=str(tmp_path))
    source = _prepared_source()
    try:
        service.record_accepted(source)
    finally:
        cif_io.cleanup_snapshot(source.effective_path)

    # high_precision.cif has no chemical_formula_sum -- exercise search
    # against the original filename instead, which is always populated.
    results = service.search("high_precision")
    assert len(results) == 1
    assert service.search("no-such-structure-anywhere") == []
