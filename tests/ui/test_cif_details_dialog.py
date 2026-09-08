"""REVIEW.md finding #8: the on-demand Details dialog must show full cell
precision, not a `.6g`-rounded approximation -- and finding #3's Origin/
Citation rows for a bundled-example source."""

from advisor.domain.cif_import.types import CifCapabilityReport, StructureSource
from advisor.ui.dialogs.cif_details_dialog import CifDetailsDialog

HIGH_PRECISION_A = 5.431020511


def _source(**overrides):
    base = dict(
        content_digest="abc", data_block=None, display_name="high_precision.cif",
        display_path="/x/high_precision.cif", formula=None, space_group=None,
        a=HIGH_PRECISION_A, b=HIGH_PRECISION_A, c=HIGH_PRECISION_A,
        alpha=90.0, beta=90.0, gamma=90.0,
        capabilities=CifCapabilityReport(geometry_ok=True, structure_factor_ok=True, message="Ready."),
        effective_path="/x/high_precision.cif", source_kind="cif",
    )
    base.update(overrides)
    return StructureSource(**base)


def _cell_text(dialog):
    form = dialog.layout().itemAt(0).layout()
    for i in range(form.rowCount()):
        label_item = form.itemAt(i, form.LabelRole)
        if label_item and label_item.widget().text() == "Cell:":
            return form.itemAt(i, form.FieldRole).widget().text()
    raise AssertionError("Cell: row not found")


def test_cell_values_round_trip_full_precision(qapp):
    dialog = CifDetailsDialog(_source())
    text = _cell_text(dialog)
    assert str(HIGH_PRECISION_A) in text
    assert "5.43102" not in text.replace(str(HIGH_PRECISION_A), "")  # not the .6g-rounded form


def test_bundled_example_shows_origin_and_citation(qapp):
    source = _source(origin="bundled_example", citation="Idealized illustrative structure.")
    dialog = CifDetailsDialog(source)
    form = dialog.layout().itemAt(0).layout()
    labels = [
        form.itemAt(i, form.LabelRole).widget().text()
        for i in range(form.rowCount())
        if form.itemAt(i, form.LabelRole)
    ]
    assert "Origin:" in labels
    assert "Citation:" in labels


def test_ordinary_import_shows_no_origin_row(qapp):
    dialog = CifDetailsDialog(_source())
    form = dialog.layout().itemAt(0).layout()
    labels = [
        form.itemAt(i, form.LabelRole).widget().text()
        for i in range(form.rowCount())
        if form.itemAt(i, form.LabelRole)
    ]
    assert "Origin:" not in labels
