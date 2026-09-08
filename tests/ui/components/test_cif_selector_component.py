"""CifDropTarget: one deliberate cifSelected per valid action, and actionable
rejection (not silence) for multi-file/folder/non-local/wrong-extension
drops. Regression coverage for the confirmed pre-refactor bug where both old
drag-drop widgets manually re-emitted `textChanged` on top of Qt's own
signal, firing the import handler twice per drop.
"""

import os

from PyQt5.QtCore import QUrl

from advisor.ui.components.cif_selector import CifDropTarget, CifStructureSummary
from advisor.domain.cif_import.types import CifCapabilityReport, StructureSource

NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "advisor", "resources", "data", "nacl.cif")
)


class _FakeDropEvent:
    """Duck-typed stand-in for QDropEvent -- CifDropTarget.dropEvent only
    calls mimeData() and acceptProposedAction(), so a real QDropEvent
    (awkward to construct headlessly) isn't needed."""

    def __init__(self, urls):
        from PyQt5.QtCore import QMimeData

        self._mime = QMimeData()
        self._mime.setUrls(urls)
        self.accepted = False

    def mimeData(self):
        return self._mime

    def acceptProposedAction(self):
        self.accepted = True


def _local_url(path: str) -> QUrl:
    return QUrl.fromLocalFile(path)


class TestValidSelectionFiresExactlyOnce:
    def test_drop_of_valid_cif_fires_cif_selected_once(self, qapp):
        target = CifDropTarget()
        received = []
        target.cifSelected.connect(received.append)

        target.dropEvent(_FakeDropEvent([_local_url(NACL_CIF)]))

        assert received == [NACL_CIF]

    def test_uppercase_extension_is_accepted(self, qapp, tmp_path):
        upper = tmp_path / "STRUCTURE.CIF"
        upper.write_bytes(b"data_x\n")
        target = CifDropTarget()
        received = []
        target.cifSelected.connect(received.append)

        target.dropEvent(_FakeDropEvent([_local_url(str(upper))]))

        assert received == [str(upper)]

    def test_unicode_and_space_path_is_accepted(self, qapp, tmp_path):
        weird = tmp_path / "na cl étude.cif"
        weird.write_bytes(b"data_x\n")
        target = CifDropTarget()
        received = []
        target.cifSelected.connect(received.append)

        target.dropEvent(_FakeDropEvent([_local_url(str(weird))]))

        assert received == [str(weird)]


class TestRejectedSelectionsDoNotFireCifSelected:
    def test_multiple_files_dropped_is_rejected_not_first_pick(self, qapp, tmp_path):
        a = tmp_path / "a.cif"
        b = tmp_path / "b.cif"
        a.write_bytes(b"data_a\n")
        b.write_bytes(b"data_b\n")
        target = CifDropTarget()
        selected = []
        rejected = []
        target.cifSelected.connect(selected.append)
        target.selectionRejected.connect(rejected.append)

        target.dropEvent(_FakeDropEvent([_local_url(str(a)), _local_url(str(b))]))

        assert selected == []
        assert len(rejected) == 1
        assert "2 files" in rejected[0]

    def test_folder_is_rejected(self, qapp, tmp_path):
        target = CifDropTarget()
        selected = []
        rejected = []
        target.cifSelected.connect(selected.append)
        target.selectionRejected.connect(rejected.append)

        target.dropEvent(_FakeDropEvent([_local_url(str(tmp_path))]))

        assert selected == []
        assert "folder" in rejected[0]

    def test_non_cif_extension_is_rejected(self, qapp, tmp_path):
        txt = tmp_path / "notes.txt"
        txt.write_text("hello")
        target = CifDropTarget()
        selected = []
        rejected = []
        target.cifSelected.connect(selected.append)
        target.selectionRejected.connect(rejected.append)

        target.dropEvent(_FakeDropEvent([_local_url(str(txt))]))

        assert selected == []
        assert "not a .cif file" in rejected[0]

    def test_non_local_url_is_rejected(self, qapp):
        target = CifDropTarget()
        selected = []
        rejected = []
        target.cifSelected.connect(selected.append)
        target.selectionRejected.connect(rejected.append)

        target.dropEvent(_FakeDropEvent([QUrl("https://example.com/structure.cif")]))

        assert selected == []
        assert len(rejected) == 1


class TestCifStructureSummary:
    def _source(self, structure_factor_ok=True):
        return StructureSource(
            content_digest="abc",
            data_block="x",
            display_name="nacl.cif",
            display_path=NACL_CIF,
            formula="Cl Na",
            space_group="P m -3 m",
            a=2.86, b=2.86, c=2.86, alpha=90.0, beta=90.0, gamma=90.0,
            capabilities=CifCapabilityReport(
                geometry_ok=True,
                structure_factor_ok=structure_factor_ok,
                reasons=() if structure_factor_ok else ("no atoms",),
                message="Ready for geometry and structure factors." if structure_factor_ok
                else "Geometry available; no atoms prevents structure-factor calculations.",
            ),
            effective_path=NACL_CIF,
            source_kind="cif",
        )

    def test_empty_state_hides_secondary_actions(self, qapp):
        summary = CifStructureSummary()
        summary.set_empty()
        assert summary._manual_button.isHidden() is True
        assert summary._remove_button.isHidden() is True
        assert summary._details_button.isHidden() is True

    def test_ready_source_shows_secondary_actions(self, qapp):
        summary = CifStructureSummary()
        summary.set_source(self._source())
        assert summary._manual_button.isHidden() is False
        assert summary._remove_button.isHidden() is False
        assert summary._details_button.isHidden() is False
        assert summary.current_source().display_name == "nacl.cif"

    def test_geometry_only_source_shows_specific_message(self, qapp):
        summary = CifStructureSummary()
        summary.set_source(self._source(structure_factor_ok=False))
        assert "prevents structure-factor" in summary._status_label.text()

    def test_manual_source_hides_manual_and_remove_buttons(self, qapp):
        manual = StructureSource(
            content_digest=None, data_block=None,
            display_name="Manual lattice", display_path="",
            formula=None, space_group=None,
            a=5.0, b=5.0, c=5.0, alpha=90.0, beta=90.0, gamma=90.0,
            capabilities=CifCapabilityReport(
                geometry_ok=True, structure_factor_ok=False,
                reasons=("manual",), message="Geometry available; manual lattice has no atomic structure.",
            ),
            effective_path=None, source_kind="manual",
        )
        summary = CifStructureSummary()
        summary.set_source(manual)
        assert summary._manual_button.isHidden() is True
        assert summary._remove_button.isHidden() is True
        assert summary._details_button.isHidden() is False


class TestStructuresButtonAndLibraryNote:
    """REQUIREMENT_2: a single combined `Structures ▾` menu button (not two
    separate buttons), always visible in both empty and populated states,
    plus a quiet library-persistence note distinct from the scientific
    status line."""

    def test_structures_button_always_visible_empty_and_populated(self, qapp):
        summary = CifStructureSummary()
        summary.set_empty()
        assert summary._structures_button.isHidden() is False

        source = StructureSource(
            content_digest="abc", data_block="x", display_name="nacl.cif", display_path=NACL_CIF,
            formula="Cl Na", space_group="P m -3 m", a=2.86, b=2.86, c=2.86, alpha=90.0, beta=90.0, gamma=90.0,
            capabilities=CifCapabilityReport(geometry_ok=True, structure_factor_ok=True, message="Ready."),
            effective_path=NACL_CIF, source_kind="cif",
        )
        summary.set_source(source)
        assert summary._structures_button.isHidden() is False

    def test_structures_button_menu_has_library_and_example_actions(self, qapp):
        summary = CifStructureSummary()
        menu = summary._structures_button.menu()
        texts = [action.text() for action in menu.actions()]
        assert texts == ["My structures…", "Try an example"]

    def test_menu_actions_emit_dedicated_signals(self, qapp):
        summary = CifStructureSummary()
        library_calls = []
        example_calls = []
        summary.libraryPickerRequested.connect(lambda: library_calls.append(1))
        summary.tryExampleRequested.connect(lambda: example_calls.append(1))

        menu = summary._structures_button.menu()
        menu.actions()[0].trigger()
        menu.actions()[1].trigger()

        assert library_calls == [1]
        assert example_calls == [1]

    def test_compact_buttons_share_object_name(self, qapp):
        summary = CifStructureSummary()
        for button in (
            summary._structures_button, summary._details_button,
            summary._manual_button, summary._remove_button,
        ):
            assert button.objectName() == "cifCompactAction"

    def test_library_note_shown_then_cleared_on_empty(self, qapp):
        summary = CifStructureSummary()
        summary.set_empty()
        assert summary._library_note_label.isHidden() is True

        summary.set_library_note("Added to My structures.")
        assert summary._library_note_label.isHidden() is False
        assert summary._library_note_label.text() == "Added to My structures."

        summary.set_empty()
        assert summary._library_note_label.isHidden() is True

    def test_setting_a_new_source_clears_previous_library_note(self, qapp):
        summary = CifStructureSummary()
        summary.set_library_note("Added to My structures.")
        source = StructureSource(
            content_digest="abc", data_block="x", display_name="nacl.cif", display_path=NACL_CIF,
            formula="Cl Na", space_group="P m -3 m", a=2.86, b=2.86, c=2.86, alpha=90.0, beta=90.0, gamma=90.0,
            capabilities=CifCapabilityReport(geometry_ok=True, structure_factor_ok=True, message="Ready."),
            effective_path=NACL_CIF, source_kind="cif",
        )
        summary.set_source(source)
        assert summary._library_note_label.isHidden() is True
