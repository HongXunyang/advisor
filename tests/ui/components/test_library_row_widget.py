"""REVIEW.md finding #7: a very long display name/formula must not balloon
a picker row's size hint into forcing horizontal scrolling -- the label text
itself must be elided (with the full text kept reachable via tooltip), not
merely visually clipped."""

from advisor.ui.components.library_row_widget import LibraryRowWidget


class _FakeRecord:
    def __init__(self, display_name, formula=None, original_filename="f.cif"):
        self.display_name = display_name
        self.original_filename = original_filename
        self.formula = formula
        self.starred = False
        self.temperature_k = None
        self.pressure_kpa = None
        self.geometry_ok = True
        self.structure_factor_ok = True
        self.source_origin = "import"

    def effective_display_name(self):
        return self.display_name or self.original_filename


def test_very_long_name_is_elided_not_full_width(qapp):
    long_name = "x" * 500
    record = _FakeRecord(display_name=long_name)

    widget = LibraryRowWidget(record)
    widget.adjustSize()

    # The row's own sizeHint must stay within a sane bound regardless of
    # input length -- REVIEW.md reproduced a 4870px-wide row from a
    # 500-character name in a 560px-wide dialog.
    assert widget.sizeHint().width() < 700


def test_full_name_still_reachable_via_tooltip(qapp):
    long_name = "y" * 500
    record = _FakeRecord(display_name=long_name)

    widget = LibraryRowWidget(record)
    name_label = widget.layout().itemAt(0).layout().itemAt(0).widget()
    assert long_name in name_label.toolTip()


def test_normal_short_name_is_not_elided(qapp):
    record = _FakeRecord(display_name="quartz_hp.cif", formula="SiO2")
    widget = LibraryRowWidget(record)
    name_label = widget.layout().itemAt(0).layout().itemAt(0).widget()
    assert "quartz_hp.cif" in name_label.text()
