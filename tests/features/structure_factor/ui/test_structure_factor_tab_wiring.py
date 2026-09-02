"""Wiring tests for the per-subtab 'Export' buttons."""
import pytest

from advisor.features.structure_factor.controllers.structure_factor_controller import (
    StructureFactorController,
)


class _FakeAppController:
    main_window = None

    def get_parameters(self):
        return {}


@pytest.fixture
def controller(qapp):
    return StructureFactorController(app_controller=_FakeAppController())


def test_hkl_plane_export_button_opens_popup_with_current_plane_snapshot(controller, monkeypatch):
    calls = []
    monkeypatch.setattr(
        controller, "open_reflection_popup", lambda **kwargs: calls.append(kwargs)
    )

    controller.view.hkl_controls.export_btn.click()

    assert len(calls) == 1
    assert "default_snapshot" in calls[0]
    # Nothing calculated yet in this test (calculator never initialized).
    assert calls[0]["default_snapshot"] is None


def test_customized_plane_export_button_opens_popup_with_current_plane_snapshot(controller, monkeypatch):
    calls = []
    monkeypatch.setattr(
        controller, "open_reflection_popup", lambda **kwargs: calls.append(kwargs)
    )

    controls = controller.view.customized_plane_widget.get_controls()
    controls.export_btn.click()

    assert len(calls) == 1
    assert "default_snapshot" in calls[0]
    assert calls[0]["default_snapshot"] is None


def test_export_button_is_next_to_initialize_button(controller):
    """The Export button should sit alongside 'Initialize Calculator', not
    in a separate shared toolbar."""
    hkl_controls = controller.view.hkl_controls
    assert hkl_controls.export_btn.parent() is hkl_controls.init_btn.parent()

    custom_controls = controller.view.customized_plane_widget.get_controls()
    assert custom_controls.export_btn.parent() is custom_controls.init_btn.parent()
