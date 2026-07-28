"""Wiring tests for ScatteringGeometryTab's calculation slots.

These target the controller/UI glue layer that sits between the (heavily
unit-tested) domain-layer solvers and the results widgets/visualizers. This
layer previously had zero test coverage, and that is exactly where a real
bug lived: calculate_angles/calculate_angles_tth_fixed unconditionally did
result["tth"][0] to build a visualization payload, assuming at least one
solution always exists. The old fsolve-based solver always left a garbage
1-element list even when no solution existed, masking the bug; the analytic
solver correctly returns an empty list for number_of_solutions == 0, which
turned that latent assumption into a real IndexError crash.

These tests drive the real tab, real control widgets, and a real
BrillouinCalculator (only QMessageBox is stubbed, since it would otherwise
block on a modal dialog) to make sure the calculation slots handle the full
range of solver outcomes (0, 1, 2, and 4 solutions; calculator not
initialized) without raising, and surface the right user-facing message.
"""
import pytest

from advisor.features.scattering_geometry.domain import BrillouinCalculator
from advisor.features.scattering_geometry.ui.scattering_geometry_tab import (
    ScatteringGeometryTab,
)


def make_tab(calculator):
    """Build a ScatteringGeometryTab without a full AppController.

    controller=None makes __init__ skip the AppController-dependent
    parameter propagation, which calculate_angles/calculate_angles_tth_fixed
    never touch directly (they only use self.calculator, the controls
    widgets, the results widgets, and the visualizers), so this mirrors the
    real construction path closely enough for these slots.
    """
    return ScatteringGeometryTab(controller=None, calculator=calculator)


class TestCalculateAnglesWiring:
    """Wiring tests for the HKL -> Angles tab's calculate_angles() slot."""

    def test_warns_and_switches_tab_when_not_initialized(self, qapp, message_box_calls):
        tab = make_tab(BrillouinCalculator())
        tab.tab_widget.setCurrentIndex(2)

        tab.calculate_angles()

        assert len(message_box_calls.warnings) == 1
        assert message_box_calls.warnings[0][1] == "Warning"
        assert tab.tab_widget.currentIndex() == 0

    def test_reachable_point_updates_results_without_crash(self, qapp, make_calculator, message_box_calls):
        tab = make_tab(make_calculator("tetragonal"))
        tab.hkl_to_angles_controls.H_input.setValue(0.15)
        tab.hkl_to_angles_controls.K_input.setValue(0.1)
        tab.hkl_to_angles_controls.L_input.setValue(-0.5)

        tab.calculate_angles()

        assert not message_box_calls.warnings
        assert not message_box_calls.criticals
        assert tab.hkl_to_angles_results.current_result["number_of_solutions"] >= 1

    def test_unreachable_hkl_shows_warning_instead_of_crashing(self, qapp, make_calculator, message_box_calls):
        """Regression test for the exact reported crash: L too large for the
        current energy previously raised IndexError instead of warning."""
        tab = make_tab(make_calculator("tetragonal"))
        tab.hkl_to_angles_controls.H_input.setValue(0.1)
        tab.hkl_to_angles_controls.K_input.setValue(0.1)
        tab.hkl_to_angles_controls.L_input.setValue(10.0)  # unreachable at 930 eV

        tab.calculate_angles()  # must not raise IndexError

        assert len(message_box_calls.warnings) == 1
        assert message_box_calls.warnings[0][1] == "No Solution"
        assert not message_box_calls.criticals
        # The results panel should reflect "0 solutions", not stale/garbage data.
        assert tab.hkl_to_angles_results.current_result["number_of_solutions"] == 0

    def test_two_solutions_uses_first_without_crash(self, qapp, make_calculator, message_box_calls):
        """A point with 2 distinct angle solutions must not crash when only
        the first is used to drive the visualization."""
        tab = make_tab(make_calculator("tetragonal"))
        tab.hkl_to_angles_controls.H_input.setValue(0.3)
        tab.hkl_to_angles_controls.K_input.setValue(0.1)
        tab.hkl_to_angles_controls.L_input.setValue(-0.3)
        tab.hkl_to_angles_controls.chi_input.setValue(-20.0)

        tab.calculate_angles()

        assert not message_box_calls.criticals
        assert tab.hkl_to_angles_results.current_result["number_of_solutions"] == 2

    def test_unexpected_exception_shows_critical_instead_of_crashing(
        self, qapp, make_calculator, message_box_calls, monkeypatch
    ):
        """Any unexpected failure further down the pipeline (e.g. a
        visualizer bug) must surface as a QMessageBox.critical, not an
        unhandled exception, matching calculate_hkl/calculate_hkl_scan's
        existing try/except style."""
        tab = make_tab(make_calculator("tetragonal"))
        tab.hkl_to_angles_controls.H_input.setValue(0.15)
        tab.hkl_to_angles_controls.K_input.setValue(0.1)
        tab.hkl_to_angles_controls.L_input.setValue(-0.5)

        def boom(*args, **kwargs):
            raise RuntimeError("simulated visualizer failure")

        monkeypatch.setattr(tab.hkl_to_angles_visualizer, "visualize_lab_system", boom)

        tab.calculate_angles()  # must not raise

        assert len(message_box_calls.criticals) == 1
        assert message_box_calls.criticals[0][1] == "Error"
        assert "simulated visualizer failure" in message_box_calls.criticals[0][2]


class TestCalculateAnglesTthFixedWiring:
    """Wiring tests for the HK to Angles | tth fixed tab's
    calculate_angles_tth_fixed() slot."""

    def test_warns_and_switches_tab_when_not_initialized(self, qapp, message_box_calls):
        tab = make_tab(BrillouinCalculator())
        tab.tab_widget.setCurrentIndex(2)

        tab.calculate_angles_tth_fixed()

        assert len(message_box_calls.warnings) == 1
        assert message_box_calls.warnings[0][1] == "Warning"
        assert tab.tab_widget.currentIndex() == 0

    def test_reachable_point_updates_results_without_crash(self, qapp, make_calculator, message_box_calls):
        tab = make_tab(make_calculator("tetragonal"))
        tab.hk_angles_controls.H_input.setValue(0.15)
        tab.hk_angles_controls.K_input.setValue(0.1)
        tab.hk_angles_controls.tth_input.setValue(60.0)

        tab.calculate_angles_tth_fixed()

        assert not message_box_calls.warnings
        assert not message_box_calls.criticals
        assert tab.hk_angles_results.current_result["number_of_solutions"] >= 1

    def test_unreachable_hk_shows_warning_instead_of_crashing(self, qapp, make_calculator, message_box_calls):
        """Same crash class as HKL -> Angles: H, K too large for tth=150 at
        930 eV means no momentum root exists at all."""
        tab = make_tab(make_calculator("tetragonal"))
        tab.hk_angles_controls.H_input.setValue(5.0)
        tab.hk_angles_controls.K_input.setValue(5.0)
        tab.hk_angles_controls.tth_input.setValue(150.0)

        tab.calculate_angles_tth_fixed()  # must not raise IndexError

        assert len(message_box_calls.warnings) == 1
        assert message_box_calls.warnings[0][1] == "No Solution"
        assert not message_box_calls.criticals
        assert tab.hk_angles_results.current_result["number_of_solutions"] == 0

    def test_two_momentum_roots_uses_first_without_crash(self, qapp, make_calculator, message_box_calls):
        """Up to 2 momentum roots (each with its own angle solution) can now
        be returned by the analytic quadratic solve; the tab must handle
        that 4-solutions-in-the-worst-case shape without crashing, and H/K/L
        must come back as per-solution lists (see result["H"][0] usage)."""
        tab = make_tab(make_calculator("tetragonal"))
        tab.hk_angles_controls.H_input.setValue(-0.1)
        tab.hk_angles_controls.K_input.setValue(-0.1)
        tab.hk_angles_controls.tth_input.setValue(150.0)

        tab.calculate_angles_tth_fixed()

        assert not message_box_calls.warnings
        assert not message_box_calls.criticals
        result = tab.hk_angles_results.current_result
        assert result["number_of_solutions"] == 2
        assert isinstance(result["H"], list) and isinstance(result["L"], list)

    def test_unexpected_exception_shows_critical_instead_of_crashing(
        self, qapp, make_calculator, message_box_calls, monkeypatch
    ):
        """Same guarantee as the HKL -> Angles tab: an unexpected failure
        further down the pipeline must surface as a QMessageBox.critical,
        not an unhandled exception."""
        tab = make_tab(make_calculator("tetragonal"))
        tab.hk_angles_controls.H_input.setValue(0.15)
        tab.hk_angles_controls.K_input.setValue(0.1)
        tab.hk_angles_controls.tth_input.setValue(60.0)

        def boom(*args, **kwargs):
            raise RuntimeError("simulated visualizer failure")

        monkeypatch.setattr(tab.hk_fixed_tth_visualizer, "visualize_lab_system", boom)

        tab.calculate_angles_tth_fixed()  # must not raise

        assert len(message_box_calls.criticals) == 1
        assert message_box_calls.criticals[0][1] == "Error"
        assert "simulated visualizer failure" in message_box_calls.criticals[0][2]


@pytest.mark.parametrize("crystal_type", ["cubic", "tetragonal", "orthorhombic", "hexagonal", "monoclinic", "triclinic"])
class TestTabConstructionSmoke:
    """A minimal smoke test across all crystal types: constructing the tab
    and running both calculation slots with default control values must
    never raise, regardless of lattice symmetry."""

    def test_calculate_angles_default_values(self, qapp, make_calculator, message_box_calls, crystal_type):
        tab = make_tab(make_calculator(crystal_type))
        tab.calculate_angles()
        assert not message_box_calls.criticals

    def test_calculate_angles_tth_fixed_default_values(self, qapp, make_calculator, message_box_calls, crystal_type):
        tab = make_tab(make_calculator(crystal_type))
        tab.calculate_angles_tth_fixed()
        assert not message_box_calls.criticals
