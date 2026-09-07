"""AppController's prepare -> accept -> invalidate -> initialize lifecycle,
exercised with real feature controllers (not fakes).

Covers: reject/no-op leave accepted state untouched, a genuine replacement
invalidates every feature (fresh calculators), switching to manual lattice
retains the given cell values as a manual starting point, Reset invalidates
every feature too (regression test for the confirmed pre-refactor gap where
``reset_parameters`` never touched feature controllers), and calculations
stay inactive until the next explicit Initialize.
"""

import glob
import os
import tempfile

import pytest

from advisor.controllers.app_controller import AppController
from advisor.domain.cif_import import io as cif_io

from tests.conftest import LATTICE_CONFIGS

NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "advisor", "resources", "data", "nacl.cif")
)
CELL_ONLY_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "cif", "cell_only.cif")
)
MALFORMED_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "cif", "malformed.cif")
)


@pytest.fixture
def controller(qapp):
    ctrl = AppController(qt_app=qapp)
    yield ctrl
    if ctrl.structure_source and ctrl.structure_source.effective_path:
        cif_io.cleanup_snapshot(ctrl.structure_source.effective_path)


@pytest.fixture
def cubic_params():
    return {**LATTICE_CONFIGS["cubic"], "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "energy": 930.0}


class TestImportAccepts:
    def test_valid_cif_is_accepted_and_invalidates_features(self, controller):
        scattering_calc_before = controller.features[0].calculator
        sf_calc_before = controller.features[1].calculator

        result = controller.import_cif(NACL_CIF)

        assert result.status == "ready"
        assert controller.structure_source is result.source
        assert controller.parameters is None
        assert controller.features[0].calculator is not scattering_calc_before
        assert controller.features[1].calculator is not sf_calc_before

    def test_calculations_inactive_until_initialize(self, controller, cubic_params):
        controller.import_cif(NACL_CIF)
        assert controller.features[0].calculator.is_initialized() is False
        assert controller.features[1].brillouin_calculator.is_initialized() is False

        controller.apply_parameters(cubic_params)
        assert controller.features[0].calculator.is_initialized() is True


class TestImportRejectsPreserveState:
    def test_rejected_cif_leaves_accepted_structure_untouched(self, controller):
        controller.import_cif(NACL_CIF)
        accepted = controller.structure_source

        result = controller.import_cif(MALFORMED_CIF)

        assert result.status == "rejected"
        assert controller.structure_source is accepted

    def test_missing_file_leaves_accepted_structure_untouched(self, controller):
        controller.import_cif(NACL_CIF)
        accepted = controller.structure_source

        result = controller.import_cif("/does/not/exist.cif")

        assert result.status == "rejected"
        assert controller.structure_source is accepted


class TestSameContentIsNoOp:
    def test_reselecting_same_file_is_unchanged(self, controller):
        controller.import_cif(NACL_CIF)
        accepted = controller.structure_source
        calc_before = controller.features[0].calculator

        result = controller.import_cif(NACL_CIF)

        assert result.status == "unchanged"
        assert controller.structure_source is accepted
        assert controller.features[0].calculator is calc_before

    def test_same_content_at_different_path_is_unchanged(self, controller, tmp_path):
        controller.import_cif(NACL_CIF)
        accepted = controller.structure_source

        copy_path = tmp_path / "nacl_copy.cif"
        with open(NACL_CIF, "rb") as fh:
            copy_path.write_bytes(fh.read())

        result = controller.import_cif(str(copy_path))

        assert result.status == "unchanged"
        assert controller.structure_source is accepted

    def test_different_content_at_same_path_is_a_replacement(self, controller, tmp_path):
        cif_path = tmp_path / "structure.cif"
        with open(NACL_CIF, "rb") as fh:
            cif_path.write_bytes(fh.read())

        first = controller.import_cif(str(cif_path))
        assert first.status == "ready"
        first_source = controller.structure_source

        with open(CELL_ONLY_CIF, "rb") as fh:
            cif_path.write_bytes(fh.read())

        second = controller.import_cif(str(cif_path))
        assert second.status == "ready_geometry_only"
        assert controller.structure_source is not first_source


class TestUseManualLattice:
    def test_retains_given_cell_values_as_manual(self, controller):
        controller.import_cif(NACL_CIF)

        controller.use_manual_lattice(5.0, 6.0, 7.0, 90.0, 90.0, 90.0)

        source = controller.structure_source
        assert source.source_kind == "manual"
        assert (source.a, source.b, source.c) == (5.0, 6.0, 7.0)
        assert source.capabilities.structure_factor_ok is False
        assert source.capabilities.geometry_ok is True

    def test_invalidates_features(self, controller):
        controller.import_cif(NACL_CIF)
        calc_before = controller.features[1].calculator

        controller.use_manual_lattice(5.0, 5.0, 5.0, 90.0, 90.0, 90.0)

        assert controller.features[1].calculator is not calc_before


class TestRemoveStructure:
    def test_clears_structure_source(self, controller):
        controller.import_cif(NACL_CIF)
        controller.remove_structure()
        assert controller.structure_source is None

    def test_invalidates_features(self, controller):
        controller.import_cif(NACL_CIF)
        calc_before = controller.features[0].calculator
        controller.remove_structure()
        assert controller.features[0].calculator is not calc_before


class TestResetParametersInvalidatesFeatures:
    """Regression test: reset_parameters() previously only cleared
    AppController.parameters and never touched either feature controller."""

    def test_reset_replaces_both_feature_calculators(self, controller, cubic_params):
        controller.import_cif(NACL_CIF)
        controller.apply_parameters(cubic_params)
        sg_calc_before = controller.features[0].calculator
        sf_calc_before = controller.features[1].calculator
        sf_brillouin_before = controller.features[1].brillouin_calculator

        controller.reset_parameters()

        assert controller.structure_source is None
        assert controller.features[0].calculator is not sg_calc_before
        assert controller.features[1].calculator is not sf_calc_before
        assert controller.features[1].brillouin_calculator is not sf_brillouin_before
        assert controller.features[0].calculator.is_initialized() is False


class TestApplyParametersAtomicity:
    def test_failure_in_one_feature_invalidates_all_and_reraises(self, controller, cubic_params, monkeypatch):
        controller.import_cif(NACL_CIF)
        sg_calc_before = controller.features[0].calculator

        def _boom(params):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(controller.features[1], "set_parameters", _boom)

        with pytest.raises(RuntimeError):
            controller.apply_parameters(cubic_params)

        assert controller.parameters is None
        # The first feature had already succeeded before the second raised --
        # it must still be pushed back to an inactive, fresh calculator.
        assert controller.features[0].calculator is not sg_calc_before
        assert controller.features[0].calculator.is_initialized() is False


def _advisor_cif_temp_dirs():
    return set(glob.glob(os.path.join(tempfile.gettempdir(), "advisor_cif_*")))


class TestSnapshotCleanupOwnership:
    """Regression tests: every readable candidate creates a temp snapshot
    directory (io.materialize_snapshot()) before validation, but nothing in
    AppController previously ever called cleanup_snapshot() -- rejection,
    an identical-content reselection, replacement, removal, and Reset all
    left their snapshot directories behind indefinitely. Fixed by releasing
    the previous/redundant/rejected snapshot at each of those transitions.
    """

    def test_reselect_reject_and_reset_leave_no_extra_snapshots(self, controller, cubic_params):
        before = _advisor_cif_temp_dirs()

        controller.import_cif(NACL_CIF)
        controller.import_cif(NACL_CIF)  # identical-content reselection: a no-op
        controller.import_cif(MALFORMED_CIF)  # rejected candidate
        controller.reset_parameters()

        after = _advisor_cif_temp_dirs()
        assert after == before

    def test_replacement_releases_the_superseded_snapshot(self, controller):
        before = _advisor_cif_temp_dirs()

        controller.import_cif(NACL_CIF)
        controller.import_cif(CELL_ONLY_CIF)

        after = _advisor_cif_temp_dirs()
        # Only the current (CELL_ONLY) snapshot should remain -- the
        # superseded NACL one must have been released, not just the fact
        # that *some* new directory exists.
        assert len(after - before) == 1

    def test_use_manual_lattice_releases_the_cif_snapshot(self, controller):
        before = _advisor_cif_temp_dirs()

        controller.import_cif(NACL_CIF)
        controller.use_manual_lattice(5.0, 5.0, 5.0, 90.0, 90.0, 90.0)

        after = _advisor_cif_temp_dirs()
        assert after == before

    def test_remove_structure_releases_the_snapshot(self, controller):
        before = _advisor_cif_temp_dirs()

        controller.import_cif(NACL_CIF)
        controller.remove_structure()

        after = _advisor_cif_temp_dirs()
        assert after == before

    def test_active_snapshot_survives_original_file_removal(self, controller, tmp_path):
        """The accepted snapshot itself must stay usable even though this
        same cleanup machinery now actively deletes *superseded* ones --
        cleanup must never touch the currently-accepted structure's file."""
        copy_path = tmp_path / "nacl_copy.cif"
        with open(NACL_CIF, "rb") as fh:
            copy_path.write_bytes(fh.read())

        controller.import_cif(str(copy_path))
        effective_path = controller.structure_source.effective_path
        copy_path.unlink()

        assert os.path.exists(effective_path)
