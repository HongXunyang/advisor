"""UnitcellVisualizer's load/reset contract.

A "clear" that only wipes the matplotlib axes but leaves crystal/
is_initialized/cif_file_path behind is a real state leak (a later render call
can silently reuse the stale crystal) -- reset() is the fix, and these tests
pin that contract down. Also covers the render-failure-vs-invalid-
crystallography distinction from REQUIREMENT_1 (a load/render failure must
surface via render_error_message, not only a console print, and must not
raise out of set_parameters()).
"""

import os
import subprocess
import sys

from advisor.ui.visualizers.unitcell_visualizer import UnitcellVisualizer

NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "advisor", "resources", "data", "nacl.cif")
)


def test_import_without_legacy_matplotlib_colormap_helper():
    """Newer Matplotlib must not fail at import due to the legacy patch."""
    result = subprocess.run(
        [sys.executable, "-c", """
import matplotlib.pyplot
import matplotlib.cm as cm
if hasattr(cm, '_ensure_cmap'):
    del cm._ensure_cmap
from advisor.ui.visualizers.unitcell_visualizer import UnitcellVisualizer
assert not hasattr(cm, '_ensure_cmap')
"""],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


class TestSetParametersSuccess:
    def test_valid_cif_initializes(self, qapp):
        viz = UnitcellVisualizer()
        viz.set_parameters({"cif_file": NACL_CIF})
        assert viz.is_initialized is True
        assert viz.crystal is not None
        assert viz.render_error_message is None

    def test_visualize_unitcell_does_not_raise(self, qapp):
        viz = UnitcellVisualizer()
        viz.set_parameters({"cif_file": NACL_CIF})
        viz.visualize_unitcell()
        assert viz.render_error_message is None


class TestSetParametersFailureDoesNotRaise:
    def test_missing_file_sets_error_message_instead_of_raising(self, qapp, tmp_path):
        viz = UnitcellVisualizer()
        missing = str(tmp_path / "does_not_exist.cif")
        viz.set_parameters({"cif_file": missing})
        assert viz.is_initialized is False
        assert viz.crystal is None
        assert viz.render_error_message is not None
        assert "Preview unavailable" in viz.render_error_message

    def test_garbage_content_sets_error_message_instead_of_raising(self, qapp, tmp_path):
        bogus = tmp_path / "bogus.cif"
        bogus.write_text("not a real cif file at all\n")
        viz = UnitcellVisualizer()
        viz.set_parameters({"cif_file": str(bogus)})
        # Dans_Diffraction.Crystal() doesn't raise on most malformed content --
        # it may still "succeed" with a default cell. Either outcome is fine
        # here; the key assertion is that nothing raises out of this call.
        assert viz.is_initialized in (True, False)


class TestFailedReloadClearsStalePreview:
    """Regression test: visualize_unitcell()'s "not initialized" guard used
    to silently `return` -- so after a successful preview followed by a
    failed reselection, the old artists (atoms, cell edges, labels) stayed
    on screen byte-for-byte identical, with the failure only recorded in
    render_error_message (which nothing rendered). Fixed to clear the axes
    and show the error text on the canvas itself.
    """

    def test_failed_reload_after_success_clears_old_atoms_from_the_axes(self, qapp, tmp_path):
        viz = UnitcellVisualizer()
        viz.set_parameters({"cif_file": NACL_CIF})
        viz.visualize_unitcell()
        assert len(viz.axes.collections) > 0 or len(viz.axes.lines) > 0  # something was drawn

        missing = str(tmp_path / "does_not_exist.cif")
        viz.set_parameters({"cif_file": missing})
        viz.visualize_unitcell()

        assert viz.crystal is None
        assert viz.is_initialized is False
        assert len(viz.axes.collections) == 0
        assert len(viz.axes.lines) == 0

    def test_failed_reload_shows_the_error_message_on_canvas(self, qapp, tmp_path):
        viz = UnitcellVisualizer()
        viz.set_parameters({"cif_file": NACL_CIF})
        viz.visualize_unitcell()

        missing = str(tmp_path / "does_not_exist.cif")
        viz.set_parameters({"cif_file": missing})
        viz.visualize_unitcell()

        assert len(viz.axes.texts) >= 1


class TestReset:
    def test_reset_clears_crystal_and_initialized_flag(self, qapp):
        viz = UnitcellVisualizer()
        viz.set_parameters({"cif_file": NACL_CIF})
        assert viz.is_initialized is True

        viz.reset()

        assert viz.is_initialized is False
        assert viz.crystal is None
        assert viz.cif_file_path is None
        assert viz.render_error_message is None

    def test_reset_prevents_stale_crystal_from_being_reused(self, qapp):
        """Regression: clear_plot() alone left crystal/is_initialized behind,
        so a subsequent guard check (`if not is_initialized or crystal is
        None: return`) would not trip, letting a render silently reuse the
        old structure. reset() must actually make that guard trip."""
        viz = UnitcellVisualizer()
        viz.set_parameters({"cif_file": NACL_CIF})
        viz.reset()

        # visualize_unitcell should now be a no-op (guard trips), not a
        # render of the previously-loaded NaCl structure.
        viz.visualize_unitcell()
        assert viz.crystal is None

    def test_clear_plot_alone_does_not_reset_crystal_state(self, qapp):
        """Documents the narrower, pre-existing clear_plot() contract:
        it only wipes the drawn axes, not the loaded-structure state --
        reset() is a distinct, stronger operation."""
        viz = UnitcellVisualizer()
        viz.set_parameters({"cif_file": NACL_CIF})

        viz.clear_plot()

        assert viz.is_initialized is True
        assert viz.crystal is not None
