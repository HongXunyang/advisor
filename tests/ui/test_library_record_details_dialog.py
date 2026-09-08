"""REVIEW.md finding #8: the saved-record Details dialog must also show
full cell precision, not `.6g`."""

from advisor.domain.library.types import LibraryRecord
from advisor.ui.dialogs.library_record_details_dialog import LibraryRecordDetailsDialog

HIGH_PRECISION_A = 5.431020511


def _record(**overrides):
    base = dict(
        id="rec1", content_hash="abc", data_block=None,
        managed_relative_path="cif_files/ab/abc.cif", original_filename="high_precision.cif",
        display_name=None, note=None, starred=False,
        imported_at=1.0, last_used_at=1.0, source_origin="import",
        formula=None, space_group=None,
        cell_a=HIGH_PRECISION_A, cell_b=HIGH_PRECISION_A, cell_c=HIGH_PRECISION_A,
        cell_alpha=90.0, cell_beta=90.0, cell_gamma=90.0,
        source_id=None, doi=None, temperature_k=None, pressure_kpa=None,
        geometry_ok=True, structure_factor_ok=True, capability_message=None,
        schema_version=1,
    )
    base.update(overrides)
    return LibraryRecord(**base)


def _cell_text(dialog):
    form = dialog.layout().itemAt(0).layout()
    for i in range(form.rowCount()):
        label_item = form.itemAt(i, form.LabelRole)
        if label_item and label_item.widget().text() == "Cell:":
            return form.itemAt(i, form.FieldRole).widget().text()
    raise AssertionError("Cell: row not found")


def test_cell_values_round_trip_full_precision(qapp):
    dialog = LibraryRecordDetailsDialog(_record(), None, None)
    text = _cell_text(dialog)
    assert str(HIGH_PRECISION_A) in text
    assert "5.43102" not in text.replace(str(HIGH_PRECISION_A), "")


def test_missing_cell_shows_not_recorded(qapp):
    dialog = LibraryRecordDetailsDialog(_record(cell_a=None), None, None)
    assert _cell_text(dialog) == "Not recorded"
