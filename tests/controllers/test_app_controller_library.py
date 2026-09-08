"""AppController <-> local structure library integration (REQUIREMENT_2).

Real `AppController`s (not fakes), each given an explicit `library_root`
(`tmp_path`) so tests never touch the real per-user library -- on top of the
autouse isolation fixture in `tests/conftest.py`. Mirrors the conventions in
`tests/controllers/test_structure_replacement_lifecycle.py`.
"""

import os

import pytest

from advisor.controllers.app_controller import AppController
from advisor.domain.cif_import import io as cif_io
from advisor.domain.library.bundled_examples import EXAMPLES

FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures", "cif"))
HIGH_PRECISION_CIF = os.path.join(FIXTURE_DIR, "high_precision.cif")
CELL_ONLY_CIF = os.path.join(FIXTURE_DIR, "cell_only.cif")
MALFORMED_CIF = os.path.join(FIXTURE_DIR, "malformed.cif")
NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "advisor", "resources", "data", "nacl.cif")
)


def _make_controller(qapp, tmp_path, name="lib"):
    return AppController(qt_app=qapp, library_root=str(tmp_path / name))


def _cleanup(controller):
    if controller.structure_source and controller.structure_source.effective_path:
        cif_io.cleanup_snapshot(controller.structure_source.effective_path)


class TestRestartAndRecent:
    def test_import_restart_recent_survives_moved_original(self, qapp, tmp_path):
        source_copy = tmp_path / "movable.cif"
        source_copy.write_bytes(open(HIGH_PRECISION_CIF, "rb").read())

        controller1 = _make_controller(qapp, tmp_path)
        try:
            result = controller1.import_cif(str(source_copy))
            assert result.status == "ready"
            assert result.library_note == "Added to My structures."
            recent = controller1.library.list_recent()
            assert len(recent) == 1
            record_id = recent[0].id
        finally:
            _cleanup(controller1)

        os.remove(source_copy)  # original moved/deleted

        controller2 = _make_controller(qapp, tmp_path)  # simulates app restart
        try:
            recent2 = controller2.library.list_recent()
            assert len(recent2) == 1
            assert recent2[0].id == record_id

            load_result = controller2.load_from_library(record_id)
            assert load_result.status == "ready"
            controller2.apply_parameters({
                **{k: getattr(load_result.source, k) for k in ("a", "b", "c", "alpha", "beta", "gamma")},
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "energy": 930.0,
                "cif_file": load_result.source.effective_path,
            })
            assert controller2.parameters is not None
        finally:
            _cleanup(controller2)


class TestDedupAndEditedContent:
    def test_reimport_identical_content_from_different_path_reuses_record(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.import_cif(HIGH_PRECISION_CIF)
            record_id = controller.library.list_recent()[0].id
            controller.library.set_starred(record_id, True)
            controller.library.rename(record_id, "My silicon")
            controller.library.set_note(record_id, "reference sample")

            copy_path = tmp_path / "copy.cif"
            copy_path.write_bytes(open(HIGH_PRECISION_CIF, "rb").read())
            controller.import_cif(str(copy_path))

            records = controller.library.list_all()
            assert len(records) == 1
            assert records[0].id == record_id
            assert records[0].starred is True
            assert records[0].display_name == "My silicon"
            assert records[0].note == "reference sample"
        finally:
            _cleanup(controller)

    def test_edited_content_at_same_path_creates_separate_record_and_invalidates(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            editable_path = tmp_path / "editable.cif"
            editable_path.write_bytes(open(HIGH_PRECISION_CIF, "rb").read())

            controller.import_cif(str(editable_path))
            sf_calc_before = controller.features[1].calculator

            editable_path.write_bytes(open(CELL_ONLY_CIF, "rb").read())
            result = controller.import_cif(str(editable_path))

            assert result.status in ("ready", "ready_geometry_only")
            assert len(controller.library.list_all()) == 2
            # A genuine structure change always invalidates every feature.
            assert controller.features[1].calculator is not sf_calc_before
        finally:
            _cleanup(controller)


class TestSameFormulaDistinctRecordsAndNoOpSelection:
    def test_same_formula_different_files_remain_separate(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.import_cif(HIGH_PRECISION_CIF)
            other_path = tmp_path / "other.cif"
            other_path.write_text(
                "data_other_silicon\n"
                "_cell_length_a 6.0\n_cell_length_b 6.0\n_cell_length_c 6.0\n"
                "_cell_angle_alpha 90.0\n_cell_angle_beta 90.0\n_cell_angle_gamma 90.0\n"
                "loop_\n_atom_site_label\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n"
                "Si1 0.0 0.0 0.0\n"
            )
            controller.import_cif(str(other_path))
            assert len(controller.library.list_all()) == 2
        finally:
            _cleanup(controller)

    def test_highlighting_and_cancelling_picker_selection_does_not_touch_session(self, qapp, tmp_path):
        """Simulates the picker's own "selecting a row previews without
        applying" contract at the AppController boundary: merely calling
        library read methods must never mutate `structure_source` or
        `last_used_at`."""
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.import_cif(HIGH_PRECISION_CIF)
            source_before = controller.structure_source
            record_before = controller.library.list_recent()[0]

            # "Highlighting" a row -- read-only.
            _ = controller.library.get(record_before.id)
            _ = controller.library.search("silicon")

            assert controller.structure_source is source_before
            assert controller.library.list_recent()[0].last_used_at == record_before.last_used_at
        finally:
            _cleanup(controller)


class TestRemembering:
    def test_remembering_off_permits_session_use_without_durable_copy(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.library.set_remember_enabled(False)
            result = controller.import_cif(HIGH_PRECISION_CIF)
            assert result.status == "ready"
            assert result.library_note is None
            assert controller.library.list_all() == []
        finally:
            _cleanup(controller)

    def test_toggle_survives_restart_and_does_not_erase_existing_entries(self, qapp, tmp_path):
        controller1 = _make_controller(qapp, tmp_path)
        try:
            controller1.import_cif(HIGH_PRECISION_CIF)
            controller1.library.set_remember_enabled(False)
        finally:
            _cleanup(controller1)

        controller2 = _make_controller(qapp, tmp_path)
        try:
            assert controller2.library.remember_enabled() is False
            assert len(controller2.library.list_all()) == 1
        finally:
            _cleanup(controller2)

    def test_rejected_and_cancelled_imports_are_never_saved(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            result = controller.import_cif(MALFORMED_CIF)
            assert result.status == "rejected"
            assert controller.library.list_all() == []
        finally:
            _cleanup(controller)

    def test_reselecting_unchanged_structure_still_updates_usage_metadata(self, qapp, tmp_path):
        """REVIEW.md finding #4: an "unchanged" reselection is scientifically
        a no-op (nothing is invalidated), but REQUIREMENT_2.md's "reimporting
        identical content ... updates usage metadata" still applies to it --
        the user did explicitly select/accept it again. Only *highlighting*
        a row (a read-only library call with no `import_cif()` at all -- see
        `TestSameFormulaDistinctRecordsAndNoOpSelection` below) must leave
        usage metadata untouched.
        """
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.import_cif(HIGH_PRECISION_CIF)
            record_before = controller.library.list_recent()[0]

            result = controller.import_cif(HIGH_PRECISION_CIF)
            assert result.status == "unchanged"
            assert result.library_note == "Already in My structures."

            record_after = controller.library.list_recent()[0]
            assert record_after.id == record_before.id
            assert record_after.last_used_at >= record_before.last_used_at
        finally:
            _cleanup(controller)

    def test_reselecting_unchanged_structure_with_remembering_off_still_updates_it(self, qapp, tmp_path):
        """REVIEW.md finding #4: turning remembering off must not suppress
        updating usage metadata for a record that already exists -- it only
        stops *new* records from being created."""
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.import_cif(HIGH_PRECISION_CIF)
            record_before = controller.library.list_recent()[0]
            controller.library.set_remember_enabled(False)

            result = controller.import_cif(HIGH_PRECISION_CIF)

            assert result.status == "unchanged"
            assert result.library_note == "Already in My structures."
            record_after = controller.library.get(record_before.id)
            assert record_after.last_used_at >= record_before.last_used_at
        finally:
            _cleanup(controller)


class TestStorageFailureIsolation:
    def test_storage_failure_still_accepts_structure_for_session(self, qapp, tmp_path, monkeypatch):
        controller = _make_controller(qapp, tmp_path)
        try:
            def _boom(*args, **kwargs):
                raise OSError("read-only filesystem")

            monkeypatch.setattr(
                "advisor.controllers.library_service.library_io.write_managed_file_atomic", _boom
            )
            result = controller.import_cif(HIGH_PRECISION_CIF)

            assert result.status == "ready"
            assert controller.structure_source is result.source
            assert result.library_note.startswith("Loaded for this session; could not save to My structures.")
            assert controller.library.list_all() == []
        finally:
            _cleanup(controller)


class TestRemoveFromLibrary:
    def test_remove_keeps_active_session_alive_and_does_not_resurrect(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.import_cif(HIGH_PRECISION_CIF)
            record_id = controller.library.list_recent()[0].id
            source_before = controller.structure_source

            controller.library.remove(record_id)

            assert controller.structure_source is source_before  # session untouched
            assert controller.library.get(record_id) is None

            # Recalculating (Initialize) must not recreate the removed entry.
            controller.apply_parameters({
                "a": source_before.a, "b": source_before.b, "c": source_before.c,
                "alpha": source_before.alpha, "beta": source_before.beta, "gamma": source_before.gamma,
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "energy": 930.0,
                "cif_file": source_before.effective_path,
            })
            assert controller.library.get(record_id) is None
        finally:
            _cleanup(controller)

    def test_remove_never_touches_external_original_file(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            movable = tmp_path / "keep_me.cif"
            movable.write_bytes(open(HIGH_PRECISION_CIF, "rb").read())
            controller.import_cif(str(movable))
            record_id = controller.library.list_recent()[0].id

            controller.library.remove(record_id)

            assert movable.exists()
        finally:
            _cleanup(controller)

    def test_remove_reports_error_and_keeps_record_when_file_deletion_fails(self, qapp, tmp_path, monkeypatch):
        """REVIEW.md finding #2: `remove()` must not drop the database row
        while silently swallowing a failure to delete the managed file --
        that would leave ADVISOR's exact managed copy on disk with no
        record pointing to it, and no way to retry."""
        from advisor.domain.library.types import LibraryError

        controller = _make_controller(qapp, tmp_path)
        try:
            controller.import_cif(HIGH_PRECISION_CIF)
            record_id = controller.library.list_recent()[0].id

            def _boom(*args, **kwargs):
                raise OSError("file is busy")

            monkeypatch.setattr("advisor.controllers.library_service.os.remove", _boom)

            with pytest.raises(LibraryError):
                controller.library.remove(record_id)

            # The row must still be there -- removal did not "succeed" while
            # actually leaving an orphaned file with no record.
            assert controller.library.get(record_id) is not None
        finally:
            _cleanup(controller)


class TestGeometryOnlyAndBundledExample:
    def test_geometry_only_record_reports_use_for_geometry_capability(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            result = controller.import_cif(CELL_ONLY_CIF)
            assert result.status == "ready_geometry_only"
            record = controller.library.list_recent()[0]
            assert record.geometry_ok is True
            assert record.structure_factor_ok is False

            controller.reset_parameters()  # so the reload below is genuine, not a no-op
            loaded = controller.load_from_library(record.id)
            assert loaded.status == "ready_geometry_only"
        finally:
            _cleanup(controller)

    def test_bundled_example_labeled_and_deduped(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            result = controller.load_bundled_example(EXAMPLES[0].key)
            assert result.status == "ready"
            record = controller.library.list_recent()[0]
            assert record.source_origin == "bundled_example"

            result2 = controller.load_bundled_example(EXAMPLES[0].key)
            assert result2.status == "unchanged"
            assert len(controller.library.list_all()) == 1
        finally:
            _cleanup(controller)

    def test_bundled_example_shows_friendly_name_origin_and_citation_in_current_session(self, qapp, tmp_path):
        """REVIEW.md finding #3: the live `StructureSource` -- not only a
        saved library record -- must carry the example's friendly name,
        "bundled_example" origin, and citation, so `CifDetailsDialog` can
        show them even with remembering disabled (i.e. with no library
        record to fall back on)."""
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.library.set_remember_enabled(False)
            result = controller.load_bundled_example(EXAMPLES[0].key)

            assert result.status == "ready"
            assert result.source.display_name == EXAMPLES[0].display_name
            assert result.source.origin == "bundled_example"
            assert result.source.citation == EXAMPLES[0].citation
            assert controller.library.list_all() == []  # confirms no record to fall back on
        finally:
            _cleanup(controller)

    def test_loading_saved_record_restores_friendly_name_not_managed_filename(self, qapp, tmp_path):
        """REVIEW.md finding #3: `load_from_library()` must not let a saved
        record reopen under its internal content-addressed managed filename
        (e.g. a SHA-256 hex string) -- the active session should show the
        record's own effective display name."""
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.import_cif(HIGH_PRECISION_CIF)
            record_id = controller.library.list_recent()[0].id
            controller.library.rename(record_id, "My favorite silicon")

            controller.reset_parameters()  # so the reload below is genuine, not a no-op
            result = controller.load_from_library(record_id)

            assert result.status == "ready"
            assert result.source.display_name == "My favorite silicon"
            # Never the raw content-hash-derived managed filename.
            managed_path = controller.library.resolve_managed_path(record_id)
            assert result.source.display_name != os.path.basename(managed_path)
            assert result.source.display_path != managed_path
        finally:
            _cleanup(controller)

    def test_bundled_example_respects_remembering_toggle(self, qapp, tmp_path):
        controller = _make_controller(qapp, tmp_path)
        try:
            controller.library.set_remember_enabled(False)
            result = controller.load_bundled_example(EXAMPLES[0].key)
            assert result.status == "ready"
            assert controller.library.list_all() == []
        finally:
            _cleanup(controller)
