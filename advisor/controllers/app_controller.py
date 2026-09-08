"""Top-level application controller."""

import json
import os
from dataclasses import replace
from typing import Optional

from PyQt5.QtWidgets import QApplication

from advisor.controllers.cif_import_service import CifImportService
from advisor.controllers.library_service import LibraryService
from advisor.domain.cif_import import CifCapabilityReport, CifImportResult, StructureSource
from advisor.domain.cif_import import io as cif_io
from advisor.domain.library.bundled_examples import (
    find_example_by_content_hash,
    get_bundled_example,
    resource_absolute_path,
)
from advisor.domain.library.types import LibraryError
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

    def __init__(self, qt_app: QApplication, library_root: Optional[str] = None):
        self.app = qt_app
        self.config = self._load_config()
        self.parameters: Optional[dict] = None
        self.structure_source: Optional[StructureSource] = None
        self._cif_import_service = CifImportService()
        # `library_root=None` resolves the real per-user app-data directory
        # (see `library_service.default_root`) -- tests always pass an
        # isolated `tmp_path` explicitly (also enforced by an autouse
        # fixture in `tests/conftest.py`) so no test can ever touch it.
        self._library_service = LibraryService(root_dir=library_root)

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

    def import_cif(
        self,
        path: str,
        origin: str = "import",
        display_name: Optional[str] = None,
        display_path: Optional[str] = None,
        citation: Optional[str] = None,
    ) -> CifImportResult:
        """Prepare and, if valid and genuinely new, accept a candidate CIF.

        Validation happens before any accepted state is touched -- a
        rejection or an exact reselection (same content + data block,
        regardless of path) leaves the current file/lattice/orientation/
        calculations/setup untouched.

        `origin` ("import" or "bundled_example") is stored on the accepted
        `StructureSource` and forwarded to the local library; it never
        affects validation/acceptance. `display_name`/`display_path`/
        `citation` are presentation-only overrides applied to the validated
        `StructureSource` *before* acceptance -- used by
        `load_from_library()`/`load_bundled_example()` so a reloaded
        structure shows its friendly name (or "Bundled example" + citation)
        instead of the internal managed-file/resource path `cif_adapter.py`
        would otherwise derive `display_name` from (REVIEW.md finding #3).
        This never touches validated bytes, capability, or identity -- only
        cosmetic fields.

        This is also the single entry point `load_from_library()`/
        `load_bundled_example()` use: because
        `CifImportService.prepare_from_path()` always materializes a fresh,
        independent temp snapshot regardless of the input path's origin,
        loading from a saved library file automatically gets its own
        session-owned copy, so removing that library entry later can never
        break an active session using it -- and every load re-runs full
        validation from scratch, so a cached "was ready" flag can never make
        a now-unsupported structure appear usable.
        """
        result = self._cif_import_service.prepare_from_path(path)
        if not result.ok:
            return result

        overrides = {"origin": origin}
        if display_name is not None:
            overrides["display_name"] = display_name
        if display_path is not None:
            overrides["display_path"] = display_path
        if citation is not None:
            overrides["citation"] = citation
        result = replace(result, source=replace(result.source, **overrides))

        if (
            self.structure_source is not None
            and result.source.identity_key() == self.structure_source.identity_key()
        ):
            # The just-materialized snapshot for this reselection is
            # redundant -- we keep using the existing accepted one -- and
            # has no other owner, so release it immediately rather than
            # leaking a temp directory on every re-drop of an already-
            # loaded file. Scientifically a no-op (nothing is invalidated),
            # but REQUIREMENT_2 still requires usage metadata (last-used) to
            # update on a genuine reselection/reimport of identical content
            # -- distinct from merely highlighting a row in the picker,
            # which must NOT touch it (that path never calls import_cif()).
            self._release_snapshot(result.source)
            library_note = self._record_in_library(self.structure_source, self.structure_source.origin)
            return CifImportResult(
                status="unchanged",
                message="This structure is already loaded.",
                source=self.structure_source,
                library_note=library_note,
            )

        library_note = self._record_in_library(result.source, origin)
        if library_note:
            result = replace(result, library_note=library_note)
        # Persistence is recorded BEFORE acceptance here (unlike the
        # unchanged-reselection branch above) specifically so the note is
        # already known when `_accept_structure()`'s invalidation cascade
        # renders the new state -- this is what lets EVERY accept entry
        # point (setup drop/Browse, File>Open CIF, Change Structure dialog,
        # Try an example, My structures) show a consistent "Added"/"could
        # not save" note via `InitWindow.on_structure_changed()`, not only
        # the setup screen's own handler (REVIEW.md finding #6).
        self._accept_structure(result.source, library_note=library_note)
        return result

    def _record_in_library(self, source: StructureSource, origin: str) -> Optional[str]:
        """Best-effort side effect of acceptance -- must never affect it.

        By the time this runs, `source` is already `self.structure_source`;
        a storage failure here can only ever produce an informational note,
        never roll back or block the already-live acceptance (REQUIREMENT_2:
        "a read-only directory/full disk/library error must not prevent an
        otherwise valid CIF from working in the current session").
        """
        if source.source_kind != "cif":
            return None
        try:
            outcome = self._library_service.record_accepted(source, origin=origin)
        except Exception:  # noqa: BLE001 -- see docstring above
            return "Loaded for this session; could not save to My structures. See Structures ▾ → My structures… for details."
        if outcome.status == "saved":
            return "Added to My structures."
        if outcome.status == "updated":
            return "Already in My structures."
        if outcome.status == "error":
            return "Loaded for this session; could not save to My structures. See Structures ▾ → My structures… for details."
        return None

    def load_from_library(self, record_id: str) -> CifImportResult:
        """Load a previously-saved library record through the exact same
        prepare/accept/revalidate path as any other CIF selection, restoring
        its friendly name/note-of-origin instead of the internal managed
        filename `cif_adapter.py` would otherwise derive `display_name` from.
        """
        record = self._library_service.get(record_id)
        if record is None:
            return CifImportResult(
                status="rejected",
                message="This saved structure no longer exists in the library.",
            )
        try:
            managed_path = self._library_service.resolve_managed_path(record_id)
        except LibraryError as exc:
            return CifImportResult(status="rejected", message=str(exc), error=str(exc))

        citation = None
        if record.source_origin == "bundled_example":
            example = find_example_by_content_hash(record.content_hash)
            citation = example.citation if example else None

        return self.import_cif(
            managed_path,
            origin=record.source_origin,
            display_name=record.effective_display_name(),
            display_path=f"My structures ({record.original_filename})",
            citation=citation,
        )

    def load_bundled_example(self, key: str) -> CifImportResult:
        """Load a bundled "Try an example" CIF through the same path, labeled
        with its friendly name/origin/citation rather than its resource
        filename."""
        example = get_bundled_example(key)
        return self.import_cif(
            resource_absolute_path(example),
            origin="bundled_example",
            display_name=example.display_name,
            display_path="Bundled example",
            citation=example.citation,
        )

    @property
    def library(self) -> LibraryService:
        return self._library_service

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

    def _accept_structure(self, source: StructureSource, library_note: Optional[str] = None):
        """Common acceptance cascade for a CIF-derived or manual structure."""
        previous_source = self.structure_source
        self.structure_source = source
        self._invalidate_for_structure_change(library_note=library_note)
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

    def _invalidate_for_structure_change(self, library_note: Optional[str] = None):
        """Shared tail of accept/remove/use-manual: clear calculations,
        invalidate every feature, notify the init view, and return to setup
        for review (without forcing navigation if setup was already showing,
        e.g. during the very first pre-Initialize import).
        """
        self.parameters = None
        for feature in self.features:
            feature.invalidate_structure()
        if hasattr(self.init_window, "on_structure_changed"):
            self.init_window.on_structure_changed(self.structure_source, library_note=library_note)
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
