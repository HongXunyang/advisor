"""Top-level application controller."""

import json
import os
from typing import Optional

from PyQt5.QtWidgets import QApplication

from advisor.controllers.cif_import_service import CifImportService
from advisor.domain.cif_import import CifCapabilityReport, CifImportResult, StructureSource
from advisor.domain.cif_import import io as cif_io
from advisor.features.scattering_geometry.controllers import ScatteringGeometryController
from advisor.features.structure_factor.controllers import StructureFactorController
from advisor.ui.init_window import InitWindow
from advisor.ui.main_window import MainWindow


class AppController:
    """Coordinates application startup, feature wiring, and the CIF import
    lifecycle (prepare -> accept -> invalidate -> initialize).

    ``structure_source`` is the single accepted structure identity every
    feature/UI consumer should refer to; ``parameters`` is the separate,
    narrower "calculations are live" boundary that only ``Initialize``
    (``apply_parameters``) sets -- accepting a new structure always clears
    ``parameters`` and returns to setup for review, it never itself makes
    calculations active.
    """

    def __init__(self, qt_app: QApplication):
        self.app = qt_app
        self.config = self._load_config()
        self.parameters: Optional[dict] = None
        self.structure_source: Optional[StructureSource] = None
        self._cif_import_service = CifImportService()

        self.main_window = MainWindow(controller=self)
        self.init_window = InitWindow(controller=self)
        self.main_window.attach_init_view(self.init_window)

        self.features = [
            ScatteringGeometryController(self),
            StructureFactorController(self),
        ]
        for feature in self.features:
            self.main_window.add_feature_tab(
                feature.view, feature.title, feature.icon, feature.description
            )

        self.app.aboutToQuit.connect(self._cleanup_on_shutdown)

        # Deliberately NOT `self.init_window.initialized.connect(self.apply_parameters)`:
        # PyQt5 does not propagate an exception raised inside a slot back
        # through the emitting `.emit()` call (it goes to sys.excepthook
        # instead, and `.emit()` returns normally), so InitWindow.initialize()
        # calls apply_parameters() directly -- a plain synchronous method
        # call -- so its own try/except can actually catch a failure and
        # show the user an error. `initialized` is still emitted afterward,
        # on success, for any other interested listener.

    def show(self):
        """Show the main window."""
        self.main_window.show()

    def apply_parameters(self, params: dict):
        """Store and propagate global parameters, then show tabs.

        Every feature must accept the new params before any of them are
        considered live: if one raises partway through the loop, all
        features (including ones that already succeeded) are pushed back
        through ``invalidate_structure()`` so calculations stay explicitly
        inactive rather than leaving a mix of old- and new-structure state,
        the init view is not left, and the exception is re-raised so the
        caller's existing error dialog (``InitWindow.initialize``) still
        surfaces it to the user.
        """
        self.parameters = params
        try:
            for feature in self.features:
                feature.set_parameters(params)
        except Exception:
            self.parameters = None
            for feature in self.features:
                feature.invalidate_structure()
            raise
        self.main_window.show_tabs()

    def reset_parameters(self):
        """Reset parameters, invalidate every feature, and return to init view."""
        previous_source = self.structure_source
        self.parameters = None
        self.structure_source = None
        for feature in self.features:
            feature.invalidate_structure()
        if hasattr(self.init_window, "reset_inputs"):
            self.init_window.reset_inputs()
        self.main_window.show_init()
        self._release_snapshot(previous_source)

    def get_parameters(self) -> dict:
        """Return the current global parameters."""
        return self.parameters or {}

    def import_cif(self, path: str) -> CifImportResult:
        """Prepare and, if valid and genuinely new, accept a candidate CIF.

        Validation happens before any accepted state is touched -- a
        rejection or an exact reselection (same content + data block,
        regardless of path) leaves the current file/lattice/orientation/
        calculations/setup untouched.
        """
        result = self._cif_import_service.prepare_from_path(path)
        if not result.ok:
            return result

        if (
            self.structure_source is not None
            and result.source.identity_key() == self.structure_source.identity_key()
        ):
            # The just-materialized snapshot for this reselection is
            # redundant -- we keep using the existing accepted one -- and
            # has no other owner, so release it immediately rather than
            # leaking a temp directory on every re-drop of an already-
            # loaded file.
            self._release_snapshot(result.source)
            return CifImportResult(
                status="unchanged",
                message="This structure is already loaded.",
                source=self.structure_source,
            )

        self._accept_structure(result.source)
        return result

    def remove_structure(self):
        """Remove the current structure entirely (no lattice values retained)."""
        previous_source = self.structure_source
        self.structure_source = None
        self._invalidate_for_structure_change()
        self._release_snapshot(previous_source)

    def use_manual_lattice(self, a: float, b: float, c: float, alpha: float, beta: float, gamma: float):
        """Switch to manual lattice entry, keeping the given cell values as a
        starting point but discarding CIF association and atomic capabilities.
        """
        source = StructureSource(
            content_digest=None,
            data_block=None,
            display_name="Manual lattice",
            display_path="",
            formula=None,
            space_group=None,
            a=a,
            b=b,
            c=c,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            capabilities=CifCapabilityReport(
                geometry_ok=True,
                structure_factor_ok=False,
                reasons=("manually entered lattice has no atomic structure",),
                message=(
                    "Geometry available; manual lattice has no atomic "
                    "structure for structure-factor calculations."
                ),
            ),
            effective_path=None,
            source_kind="manual",
        )
        self._accept_structure(source)

    def _accept_structure(self, source: StructureSource):
        """Common acceptance cascade for a CIF-derived or manual structure."""
        previous_source = self.structure_source
        self.structure_source = source
        self._invalidate_for_structure_change()
        self._release_snapshot(previous_source)

    def _release_snapshot(self, source: Optional[StructureSource]):
        """Best-effort cleanup of a superseded/rejected/no-longer-accepted
        `StructureSource`'s temp CIF snapshot.

        Called only after every feature has already been pushed through
        `invalidate_structure()` (so nothing can still be reading the file),
        or on a candidate that was never accepted in the first place (a
        no-op reselection). Manual-entry sources have no `effective_path`
        and are a no-op here. This is what actually disposes of the temp
        directories `io.materialize_snapshot()` creates -- without it,
        every accepted-then-replaced/removed structure (and every rejected
        or redundant candidate) would leak its snapshot for the life of the
        process.
        """
        if source is not None and source.effective_path:
            cif_io.cleanup_snapshot(source.effective_path)

    def _cleanup_on_shutdown(self):
        """Release the final accepted structure's snapshot on app exit."""
        self._release_snapshot(self.structure_source)

    def _invalidate_for_structure_change(self):
        """Shared tail of accept/remove/use-manual: clear calculations,
        invalidate every feature, notify the init view, and return to setup
        for review (without forcing navigation if setup was already showing,
        e.g. during the very first pre-Initialize import).
        """
        self.parameters = None
        for feature in self.features:
            feature.invalidate_structure()
        if hasattr(self.init_window, "on_structure_changed"):
            self.init_window.on_structure_changed(self.structure_source)
        if self.main_window.is_showing_tabs():
            self.main_window.show_init()

    def _load_config(self) -> dict:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "resources", "config", "app_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as e:
            print(f"Warning: could not load app config from {config_path} ({e}); using defaults")
            return {
                "app_name": "Advisor-Scattering",
                "window_size": {"width": 1200, "height": 800},
            }
