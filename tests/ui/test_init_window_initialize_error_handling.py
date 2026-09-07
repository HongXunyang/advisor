"""Regression test: a failure inside AppController.apply_parameters() must
actually reach InitWindow.initialize()'s QMessageBox.critical -- it
previously did not.

PyQt5 does not propagate an exception raised inside a slot back through the
emitting `.emit()` call for a direct (same-thread) connection: the exception
goes to `sys.excepthook` instead, and `.emit()` returns normally to its
caller. `InitWindow.initialize()` used to rely on
`self.initialized.emit(params)` (connected to `AppController.apply_parameters`)
re-raising back into its own `try/except`, which -- despite
`apply_parameters()` genuinely re-raising internally -- never actually
worked; the promised "recoverable user error" was never shown, only global
parameters silently went back to None. Fixed by having `initialize()` call
`apply_parameters()` directly (a plain synchronous method call) instead.
"""

import os

import pytest

from advisor.controllers.app_controller import AppController
from advisor.domain.cif_import import io as cif_io

from tests.conftest import LATTICE_CONFIGS

NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "advisor", "resources", "data", "nacl.cif")
)


@pytest.fixture
def controller(qapp):
    ctrl = AppController(qt_app=qapp)
    yield ctrl
    if ctrl.structure_source and ctrl.structure_source.effective_path:
        cif_io.cleanup_snapshot(ctrl.structure_source.effective_path)


class TestFailureDuringInitializeReachesTheUser:
    def test_real_button_click_path_shows_one_error_and_raises_nothing_unhandled(
        self, controller, message_box_calls, monkeypatch
    ):
        controller.import_cif(NACL_CIF)
        window = controller.init_window

        def _boom(params):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(controller.features[1], "set_parameters", _boom)

        unhandled = []
        monkeypatch.setattr(
            "sys.excepthook", lambda t, v, tb: unhandled.append(v)
        )

        window.initialize()  # the real Initialize button's slot

        assert len(message_box_calls.criticals) == 1
        assert "simulated failure" in message_box_calls.criticals[0][-1]
        assert unhandled == []
        assert controller.parameters is None

    def test_successful_retry_after_a_failure_works(self, controller, message_box_calls, monkeypatch):
        controller.import_cif(NACL_CIF)
        window = controller.init_window

        def _boom(params):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(controller.features[1], "set_parameters", _boom)
        window.initialize()
        assert len(message_box_calls.criticals) == 1
        assert controller.parameters is None

        monkeypatch.undo()  # restore the real set_parameters
        window.initialize()

        assert controller.parameters is not None
        assert controller.features[0].calculator.is_initialized() is True
