"""The "My structures" picker (REQUIREMENT_2).

Recent/Starred/All are views of one library, not separate storage. Selecting
a row only updates the detail/edit panel below the list -- it never touches
`AppController`; only "Use structure"/"Use for geometry" does, by calling
`AppController.load_from_library()`, the exact same accept/revalidate path
as any other CIF selection. Cancelling or changing filters/search leaves the
current session untouched.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from advisor.domain.library.bundled_examples import find_example_by_content_hash
from advisor.domain.library.types import LibraryError
from advisor.ui.components.library_row_widget import LibraryRowWidget
from advisor.ui.dialogs.library_record_details_dialog import LibraryRecordDetailsDialog


class LibraryPickerDialog(QDialog):
    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.library = app_controller.library
        self._current_filter = "recent"
        self._records = []
        self._selected_record_id = None

        self.setWindowTitle("My Structures")
        self.setMinimumSize(560, 460)

        outer = QVBoxLayout(self)

        unavailable_row = QHBoxLayout()
        self._unavailable_banner = QLabel("")
        self._unavailable_banner.setWordWrap(True)
        self._unavailable_banner.setStyleSheet("color: #C62828;")
        self._unavailable_banner.setVisible(False)
        unavailable_row.addWidget(self._unavailable_banner, 1)
        self._retry_button = QPushButton("Retry")
        self._retry_button.setObjectName("cifCompactAction")
        self._retry_button.setVisible(False)
        self._retry_button.clicked.connect(self._on_retry_clicked)
        unavailable_row.addWidget(self._retry_button)
        outer.addLayout(unavailable_row)

        filter_row = QHBoxLayout()
        self._recent_btn = self._make_filter_button("Recent", "recent")
        self._starred_btn = self._make_filter_button("Starred", "starred")
        self._all_btn = self._make_filter_button("All", "all")
        for btn in (self._recent_btn, self._starred_btn, self._all_btn):
            filter_row.addWidget(btn)
        self._recent_btn.setChecked(True)
        filter_row.addStretch(1)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search…")
        self._search_edit.textChanged.connect(lambda _text: self._reload())
        filter_row.addWidget(self._search_edit)
        outer.addLayout(filter_row)

        self._list_widget = QListWidget()
        # Vertical scrolling inside the library list is acceptable
        # (REQUIREMENT_2.md); horizontal scrolling of a primary control is
        # not, regardless of how long a row's content gets -- hard guarantee
        # on top of LibraryRowWidget's own text eliding (REVIEW.md finding #7).
        self._list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list_widget.setResizeMode(QListWidget.Adjust)
        self._list_widget.currentItemChanged.connect(self._on_selection_changed)
        outer.addWidget(self._list_widget, 1)

        self._empty_label = QLabel("")
        self._empty_label.setWordWrap(True)
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setVisible(False)
        outer.addWidget(self._empty_label)

        self._clear_search_btn = QPushButton("Clear search")
        self._clear_search_btn.setObjectName("cifCompactAction")
        self._clear_search_btn.setVisible(False)
        self._clear_search_btn.clicked.connect(self._search_edit.clear)
        outer.addWidget(self._clear_search_btn, alignment=Qt.AlignHCenter)

        detail_group = QGroupBox("Details")
        detail_layout = QVBoxLayout(detail_group)

        self._detail_label = QLabel("Select a structure to see details.")
        self._detail_label.setWordWrap(True)
        detail_layout.addWidget(self._detail_label)

        edit_row = QHBoxLayout()
        self._star_checkbox = QCheckBox("Starred")
        self._star_checkbox.setEnabled(False)
        self._star_checkbox.toggled.connect(self._on_star_toggled)
        edit_row.addWidget(self._star_checkbox)
        edit_row.addWidget(QLabel("Name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setEnabled(False)
        self._name_edit.editingFinished.connect(self._on_name_edited)
        edit_row.addWidget(self._name_edit)
        detail_layout.addLayout(edit_row)

        note_row = QHBoxLayout()
        note_row.addWidget(QLabel("Note:"))
        self._note_edit = QLineEdit()
        self._note_edit.setEnabled(False)
        self._note_edit.editingFinished.connect(self._on_note_edited)
        note_row.addWidget(self._note_edit)
        detail_layout.addLayout(note_row)

        detail_buttons = QHBoxLayout()
        self._details_button = QPushButton("Details…")
        self._details_button.setObjectName("cifCompactAction")
        self._details_button.setEnabled(False)
        self._details_button.clicked.connect(self._on_details_clicked)
        detail_buttons.addWidget(self._details_button)
        detail_buttons.addStretch(1)
        self._remove_button = QPushButton("Remove from library")
        self._remove_button.setObjectName("cifCompactAction")
        self._remove_button.setEnabled(False)
        self._remove_button.clicked.connect(self._on_remove_clicked)
        detail_buttons.addWidget(self._remove_button)
        detail_layout.addLayout(detail_buttons)

        outer.addWidget(detail_group)

        self._remember_checkbox = QCheckBox("Remember imported CIFs on this device")
        self._remember_checkbox.toggled.connect(self._on_remember_toggled)
        outer.addWidget(self._remember_checkbox)
        remember_help = QLabel("Off only affects future imports — saved structures stay available.")
        remember_help.setStyleSheet("color: #757575; font-size: 11px;")
        outer.addWidget(remember_help)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        bottom.addWidget(cancel_button)
        self._use_button = QPushButton("Use structure")
        self._use_button.setEnabled(False)
        self._use_button.clicked.connect(self._on_use_clicked)
        bottom.addWidget(self._use_button)
        outer.addLayout(bottom)

        self._reload()  # also refreshes the remember checkbox once available (or disables it)

    # -- filter buttons -----------------------------------------------------

    def _make_filter_button(self, label, key):
        button = QPushButton(label)
        button.setObjectName("cifCompactAction")
        button.setCheckable(True)
        button.clicked.connect(lambda: self._set_filter(key))
        return button

    def _set_filter(self, key):
        self._current_filter = key
        for btn, btn_key in (
            (self._recent_btn, "recent"), (self._starred_btn, "starred"), (self._all_btn, "all")
        ):
            btn.setChecked(btn_key == key)
        self._search_edit.blockSignals(True)
        self._search_edit.clear()
        self._search_edit.blockSignals(False)
        self._reload()

    # -- loading / rendering --------------------------------------------

    def _reload(self):
        if not self.library.is_available:
            # A prior failure might have been transient (disk space freed,
            # permissions fixed) -- retry automatically whenever the picker
            # reloads (including on open) before reporting it as unavailable,
            # so simply reopening the dialog is often enough to recover
            # without an explicit click (REVIEW.md findings #1 and #6: an
            # unavailable library needs a real, usable recovery path, not
            # just an explanatory message with no way back short of
            # restarting the app).
            self.library.retry_open()
        if not self.library.is_available:
            self._show_unavailable()
            return
        self._unavailable_banner.setVisible(False)
        self._retry_button.setVisible(False)
        for btn in (self._recent_btn, self._starred_btn, self._all_btn):
            btn.setEnabled(True)
        self._search_edit.setEnabled(True)
        self._list_widget.setEnabled(True)
        self._refresh_remember_checkbox()
        try:
            query = self._search_edit.text().strip()
            if query:
                records = self.library.search(query)
            elif self._current_filter == "starred":
                records = self.library.list_starred()
            elif self._current_filter == "all":
                records = self.library.list_all()
            else:
                records = self.library.list_recent(10)
        except LibraryError as exc:
            self._show_unavailable(str(exc))
            return
        self._records = records
        self._populate_list(records)

    def _on_retry_clicked(self):
        self._reload()

    def _show_unavailable(self, message=None):
        self._unavailable_banner.setText(
            message
            or self.library.unavailable_reason
            or "Your library couldn't be opened. Existing saved structures are safe but unavailable right now."
        )
        self._unavailable_banner.setVisible(True)
        self._retry_button.setVisible(True)
        self._list_widget.clear()
        self._list_widget.setEnabled(False)
        self._search_edit.setEnabled(False)
        for btn in (self._recent_btn, self._starred_btn, self._all_btn):
            btn.setEnabled(False)
        self._remember_checkbox.setEnabled(False)
        self._empty_label.setVisible(False)
        self._update_detail_panel(None)

    def _populate_list(self, records):
        self._list_widget.clear()
        if not records:
            query = self._search_edit.text().strip()
            self._list_widget.setVisible(False)
            self._empty_label.setVisible(True)
            if query:
                self._empty_label.setText(f"No matches for “{query}”.")
                self._clear_search_btn.setVisible(True)
            else:
                self._empty_label.setText(
                    "No saved structures yet.\nUse Browse to import a CIF, or Try an example."
                )
                self._clear_search_btn.setVisible(False)
        else:
            self._list_widget.setVisible(True)
            self._empty_label.setVisible(False)
            self._clear_search_btn.setVisible(False)
            for record in records:
                item = QListWidgetItem()
                item.setData(Qt.UserRole, record.id)
                widget = LibraryRowWidget(record)
                item.setSizeHint(widget.sizeHint())
                self._list_widget.addItem(item)
                self._list_widget.setItemWidget(item, widget)
        self._update_detail_panel(None)

    # -- selection / detail panel -----------------------------------------

    def _on_selection_changed(self, current, _previous):
        record_id = current.data(Qt.UserRole) if current is not None else None
        self._update_detail_panel(record_id)

    def _find_record(self, record_id):
        return next((r for r in self._records if r.id == record_id), None)

    def _update_detail_panel(self, record_id):
        self._selected_record_id = record_id
        record = self._find_record(record_id) if record_id else None

        for widget in (self._star_checkbox, self._name_edit, self._note_edit,
                       self._details_button, self._remove_button, self._use_button):
            widget.setEnabled(record is not None)

        if record is None:
            self._detail_label.setText("Select a structure to see details.")
            self._name_edit.clear()
            self._note_edit.clear()
            return

        lines = [
            f"Formula: {record.formula or 'Not recorded'}",
            f"Space group: {record.space_group or 'Not recorded'}",
        ]
        if all(v is not None for v in (record.cell_a, record.cell_b, record.cell_c)):
            lines.append(f"a={record.cell_a:.6g}  b={record.cell_b:.6g}  c={record.cell_c:.6g} Å")
        source_bits = []
        if record.source_id:
            source_bits.append(f"Source: {record.source_id}")
        if record.doi:
            source_bits.append(f"DOI: {record.doi}")
        if source_bits:
            lines.append("   ".join(source_bits))
        self._detail_label.setText("\n".join(lines))

        self._star_checkbox.blockSignals(True)
        self._star_checkbox.setChecked(record.starred)
        self._star_checkbox.blockSignals(False)

        self._name_edit.blockSignals(True)
        self._name_edit.setText(record.display_name or "")
        self._name_edit.setPlaceholderText(record.original_filename)
        self._name_edit.blockSignals(False)

        self._note_edit.blockSignals(True)
        self._note_edit.setText(record.note or "")
        self._note_edit.blockSignals(False)

        if record.geometry_ok and record.structure_factor_ok is False:
            self._use_button.setText("Use for geometry")
        else:
            self._use_button.setText("Use structure")

    # -- edits ------------------------------------------------------------

    def _on_star_toggled(self, checked):
        if not self._selected_record_id:
            return
        self.library.set_starred(self._selected_record_id, checked)
        self._reload_keep_selection()

    def _on_name_edited(self):
        if not self._selected_record_id:
            return
        text = self._name_edit.text().strip()
        self.library.rename(self._selected_record_id, text or None)
        self._reload_keep_selection()

    def _on_note_edited(self):
        if not self._selected_record_id:
            return
        text = self._note_edit.text().strip()
        self.library.set_note(self._selected_record_id, text or None)

    def _reload_keep_selection(self):
        keep = self._selected_record_id
        self._reload()
        if not keep:
            return
        for index in range(self._list_widget.count()):
            item = self._list_widget.item(index)
            if item.data(Qt.UserRole) == keep:
                self._list_widget.setCurrentItem(item)
                break

    def _on_details_clicked(self):
        record = self._find_record(self._selected_record_id)
        if record is None:
            return
        citation = None
        if record.source_origin == "bundled_example":
            example = find_example_by_content_hash(record.content_hash)
            citation = example.citation if example else None
        try:
            managed_path = self.library.resolve_managed_path(record.id)
        except LibraryError:
            managed_path = None
        LibraryRecordDetailsDialog(record, managed_path, citation, self).exec_()

    def _on_remove_clicked(self):
        record = self._find_record(self._selected_record_id)
        if record is None:
            return
        confirm = QMessageBox.question(
            self,
            "Remove from library",
            (
                f"Remove ADVISOR's saved copy of “{record.effective_display_name()}”?\n\n"
                "This only deletes ADVISOR's local copy. The original file on your "
                "computer (if it still exists) is never touched."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self.library.remove(record.id)
        self._selected_record_id = None
        self._reload()

    def _on_use_clicked(self):
        if not self._selected_record_id:
            return
        result = self.app_controller.load_from_library(self._selected_record_id)
        if result.status == "rejected":
            QMessageBox.warning(self, "Could not load structure", result.message)
            return
        self.accept()

    # -- remembering preference -----------------------------------------

    def _refresh_remember_checkbox(self):
        if self.library.is_available:
            self._remember_checkbox.setEnabled(True)
            self._remember_checkbox.blockSignals(True)
            self._remember_checkbox.setChecked(self.library.remember_enabled())
            self._remember_checkbox.blockSignals(False)
        else:
            self._remember_checkbox.setEnabled(False)

    def _on_remember_toggled(self, checked):
        try:
            self.library.set_remember_enabled(checked)
        except LibraryError:
            pass
