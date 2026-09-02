#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
"""Reflection List popup for the Structure Factor feature.

Reachable via an "Export" button next to each subtab's main action button
(HKL plane's "Initialize Calculator" and Customized plane's "Calculate
Structure Factor"), but backed by a single shared popup instance owned by
StructureFactorController -- opening it from either subtab reuses the same
window rather than creating a duplicate. By default the table shows exactly
the HKL points currently plotted on the caller's active 2D view; the H/K/L
range controls let the user additionally generate an arbitrary custom
range. Energy is read-only -- it always reflects the shared
StructureFactorCalculator's current authoritative state, so this popup can
never silently invalidate the existing plots.
"""
import os
from dataclasses import dataclass

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QDialog, QDoubleSpinBox, QFileDialog,
                             QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                             QPushButton, QSpinBox, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from advisor.features.structure_factor.domain.reflection_list import (
    DEFAULT_EXTINCTION_REL_TOL,
)
from advisor.features.structure_factor.domain.structure_factor_calculator import (
    SCATTERING_TYPE,
)

# Reasonable signed-integer bounds for HKL spin boxes; not a scientific
# limit, just a sane widget range (reciprocal-space indices this large are
# never realistic for the CIFs this tool targets).
_HKL_SPIN_RANGE = (-100, 100)

# Keeps the popup window a compact, fixed size regardless of result count --
# the table itself scrolls internally past this height instead of the
# window growing to fit every row.
_RESULTS_TABLE_MAX_HEIGHT = 320


@dataclass
class _ResultContext:
    """Exactly what produced the rows currently in the table.

    Export metadata is always built from this, never from live widget
    state -- toggling a filter checkbox after generating must not make the
    exported metadata describe a different operation than the exported
    rows.
    """

    source: str
    cif_filename: str
    energy_kev: float
    scattering_type: str
    generated_count: int
    filtered_count: int
    exclude_extinct: bool
    rel_tol: float
    min_intensity: float
    h_range: tuple = None
    k_range: tuple = None
    l_range: tuple = None


class _NumericTableWidgetItem(QTableWidgetItem):
    """QTableWidgetItem that sorts by a stored numeric value, not display text.

    Plain QTableWidgetItem sorts lexicographically on its display string
    (so "10" would sort before "2"), which breaks "strongest reflections
    first" sorting on the intensity column.
    """

    def __init__(self, value: float, text: str):
        super().__init__(text)
        self._value = value

    def __lt__(self, other):
        if isinstance(other, _NumericTableWidgetItem):
            return self._value < other._value
        return super().__lt__(other)


class ReflectionResultsTable(QTableWidget):
    """Sortable table of reflection results, default-sorted by intensity descending."""

    COLUMNS = ["H", "K", "L", "Re(F)", "Im(F)", "|F|", "|F|²"]
    INTENSITY_COLUMN = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)
        # Vertical scrollbar appears automatically once content exceeds this
        # height, instead of the popup window growing to fit every row.
        self.setMaximumHeight(_RESULTS_TABLE_MAX_HEIGHT)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def display_reflections(self, reflections):
        """Populate the table from a list of Reflection records."""
        self.setSortingEnabled(False)
        self.setRowCount(0)
        for r in reflections:
            row = self.rowCount()
            self.insertRow(row)
            h_item = _NumericTableWidgetItem(r.h, str(r.h))
            h_item.setData(Qt.UserRole, r)
            self.setItem(row, 0, h_item)
            self.setItem(row, 1, _NumericTableWidgetItem(r.k, str(r.k)))
            self.setItem(row, 2, _NumericTableWidgetItem(r.l, str(r.l)))
            self.setItem(row, 3, _NumericTableWidgetItem(r.f_real, f"{r.f_real:.4g}"))
            self.setItem(row, 4, _NumericTableWidgetItem(r.f_imag, f"{r.f_imag:.4g}"))
            self.setItem(row, 5, _NumericTableWidgetItem(r.f_magnitude, f"{r.f_magnitude:.4g}"))
            self.setItem(row, 6, _NumericTableWidgetItem(r.intensity, f"{r.intensity:.4g}"))
        self.setSortingEnabled(True)
        self.sortItems(self.INTENSITY_COLUMN, Qt.DescendingOrder)

    def reflections(self):
        """Return the Reflection records currently in the table, in display order."""
        return [self.item(row, 0).data(Qt.UserRole) for row in range(self.rowCount())]

    def clear_results(self):
        self.setRowCount(0)


class ReflectionPopup(QDialog):
    """Modeless popup: reflection list (default = current plane) + export.

    Kept alive and reused across repeat "Export" button presses (see
    StructureFactorController.open_reflection_popup) -- closing the window
    just hides it (default Qt behavior, no WA_DeleteOnClose), it is never
    destroyed and recreated, so its state and geometry persist across opens
    within a session.
    """

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Reflection List & Export")
        self.setModal(False)
        self.setMinimumSize(600, 460)
        # What actually produced the currently-displayed rows -- see
        # _ResultContext and _display_results(). None until something has
        # been successfully loaded/generated.
        self._current_context = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.not_initialized_label = QLabel(
            "Calculator not initialized — initialize it from either subtab first."
        )
        self.not_initialized_label.setStyleSheet("color: orange; font-weight: bold;")
        self.not_initialized_label.setVisible(False)
        layout.addWidget(self.not_initialized_label)

        # --- Compact H/K/L bounds row ---
        bounds_row = QWidget()
        bounds_layout = QHBoxLayout(bounds_row)
        bounds_layout.setContentsMargins(0, 0, 0, 0)
        self.h_min = QSpinBox()
        self.h_max = QSpinBox()
        self.k_min = QSpinBox()
        self.k_max = QSpinBox()
        self.l_min = QSpinBox()
        self.l_max = QSpinBox()
        for label_text, spin, default in (
            ("H:", self.h_min, -3), ("to", self.h_max, 3),
            ("  K:", self.k_min, -3), ("to", self.k_max, 3),
            ("  L:", self.l_min, -3), ("to", self.l_max, 3),
        ):
            spin.setRange(*_HKL_SPIN_RANGE)
            spin.setValue(default)
            spin.setMinimumWidth(70)
            bounds_layout.addWidget(QLabel(label_text))
            bounds_layout.addWidget(spin)
        bounds_layout.addStretch()
        layout.addWidget(bounds_row)

        # --- Filters row ---
        filters_row = QWidget()
        filters_layout = QHBoxLayout(filters_row)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        self.exclude_extinct_checkbox = QCheckBox("Exclude extinct reflections")
        self.exclude_extinct_checkbox.setChecked(True)
        self.min_intensity_checkbox = QCheckBox("Min. intensity:")
        self.min_intensity_spin = QDoubleSpinBox()
        self.min_intensity_spin.setRange(0.0, 1e12)
        self.min_intensity_spin.setDecimals(6)
        self.min_intensity_spin.setMaximumWidth(100)
        self.min_intensity_spin.setEnabled(False)
        self.min_intensity_checkbox.toggled.connect(self.min_intensity_spin.setEnabled)
        filters_layout.addWidget(self.exclude_extinct_checkbox)
        filters_layout.addWidget(self.min_intensity_checkbox)
        filters_layout.addWidget(self.min_intensity_spin)
        filters_layout.addStretch()
        layout.addWidget(filters_row)

        # --- Compact action buttons row ---
        actions_row = QWidget()
        actions_layout = QHBoxLayout(actions_row)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        self.generate_btn = QPushButton("Generate")
        self.export_csv_btn = QPushButton("Export CSV…")
        self.export_json_btn = QPushButton("Export JSON…")
        for btn in (self.generate_btn, self.export_csv_btn, self.export_json_btn):
            btn.setAutoDefault(False)
            btn.setMaximumWidth(110)
        self.export_csv_btn.setEnabled(False)
        self.export_json_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self._on_generate_bulk)
        self.export_csv_btn.clicked.connect(lambda: self._on_export("csv"))
        self.export_json_btn.clicked.connect(lambda: self._on_export("json"))
        actions_layout.addWidget(self.generate_btn)
        actions_layout.addWidget(self.export_csv_btn)
        actions_layout.addWidget(self.export_json_btn)
        actions_layout.addStretch()
        layout.addWidget(actions_row)

        self.count_label = QLabel("")
        layout.addWidget(self.count_label)

        self.results_table = ReflectionResultsTable()
        layout.addWidget(self.results_table)

        self.refresh_from_calculator()

    def refresh_from_calculator(self):
        """Enable/disable controls based on whether the calculator is initialized."""
        initialized = self.controller.calculator.is_initialized
        self.not_initialized_label.setVisible(not initialized)

        for widget in (
            self.h_min, self.h_max, self.k_min, self.k_max, self.l_min, self.l_max,
            self.exclude_extinct_checkbox, self.min_intensity_checkbox, self.generate_btn,
        ):
            widget.setEnabled(initialized)

    def load_snapshot(self, snapshot):
        """Populate the table from a captured ``ReflectionSnapshot``, or show
        an empty/"nothing calculated yet" state if ``snapshot`` is None.

        Filtering is applied to the snapshot's frozen data via
        ``apply_filters_to_snapshot`` -- never through a fresh calculator
        call -- so the table always matches what was actually plotted, even
        if the shared calculator has since been reinitialized elsewhere.
        """
        if snapshot is None:
            self.results_table.clear_results()
            self.count_label.setText(
                "Nothing calculated for this view yet — initialize/calculate it first."
            )
            self.export_csv_btn.setEnabled(False)
            self.export_json_btn.setEnabled(False)
            self._current_context = None
            return

        exclude_extinct = self.exclude_extinct_checkbox.isChecked()
        min_intensity = (
            self.min_intensity_spin.value() if self.min_intensity_checkbox.isChecked() else None
        )
        result = self.controller.apply_filters_to_snapshot(
            snapshot, exclude_extinct=exclude_extinct, min_intensity=min_intensity
        )
        self._display_results(
            result,
            source="the current plane view",
            cif_filename=snapshot.cif_filename,
            energy_kev=snapshot.energy_kev,
            scattering_type=snapshot.scattering_type,
            exclude_extinct=exclude_extinct,
            min_intensity=min_intensity,
        )

    def _on_generate_bulk(self):
        h_range = (self.h_min.value(), self.h_max.value())
        k_range = (self.k_min.value(), self.k_max.value())
        l_range = (self.l_min.value(), self.l_max.value())
        exclude_extinct = self.exclude_extinct_checkbox.isChecked()
        min_intensity = (
            self.min_intensity_spin.value() if self.min_intensity_checkbox.isChecked() else None
        )

        result = self.controller.run_bulk_reflection_calculation(
            h_range, k_range, l_range,
            exclude_extinct=exclude_extinct,
            min_intensity=min_intensity,
        )
        if not result["success"]:
            QMessageBox.warning(self, "Cannot Generate", result.get("error", "Unknown error"))
            return

        calculator = self.controller.calculator
        self._display_results(
            result,
            source="the requested range",
            cif_filename=os.path.basename(calculator.cif_file_path),
            energy_kev=calculator.energy / 1000.0,
            scattering_type=SCATTERING_TYPE,
            exclude_extinct=exclude_extinct,
            min_intensity=min_intensity,
            h_range=h_range, k_range=k_range, l_range=l_range,
        )

    def _display_results(
        self, result, source, cif_filename, energy_kev, scattering_type,
        exclude_extinct, min_intensity, h_range=None, k_range=None, l_range=None,
    ):
        self.results_table.display_reflections(result["reflections"])
        self.count_label.setText(
            f"Showing {result['filtered_count']} of {result['generated_count']} reflections from {source}."
        )
        has_results = result["filtered_count"] > 0
        self.export_csv_btn.setEnabled(has_results)
        self.export_json_btn.setEnabled(has_results)

        self._current_context = _ResultContext(
            source=source,
            cif_filename=cif_filename,
            energy_kev=energy_kev,
            scattering_type=scattering_type,
            generated_count=result["generated_count"],
            filtered_count=result["filtered_count"],
            exclude_extinct=exclude_extinct,
            rel_tol=DEFAULT_EXTINCTION_REL_TOL if exclude_extinct else None,
            min_intensity=min_intensity,
            h_range=h_range, k_range=k_range, l_range=l_range,
        )

    def _default_export_filename(self, ext: str) -> str:
        if self._current_context is not None:
            cif_base = os.path.splitext(self._current_context.cif_filename)[0]
            energy_kev = self._current_context.energy_kev
        else:
            cif_base, energy_kev = "reflections", 0.0
        return f"{cif_base}_{energy_kev:g}keV_reflections.{ext}"

    def _on_export(self, fmt: str):
        reflections = self.results_table.reflections()
        if not reflections or self._current_context is None:
            QMessageBox.warning(self, "Nothing to Export", "There are no results to export.")
            return

        file_filter = "CSV Files (*.csv)" if fmt == "csv" else "JSON Files (*.json)"
        default_name = self._default_export_filename(fmt)

        # DontUseNativeDialog is deliberate: on macOS, the native save panel
        # opens as a "sheet" attached to this (modeless) popup, and
        # dismissing that sheet via Cancel can propagate a close event to
        # the popup itself, closing the whole reflection list -- not just
        # the file dialog. Qt's own (non-native) file dialog avoids that
        # sheet/parent interaction entirely. It still asks before
        # overwriting an existing file by default, so no behavior is lost.
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Reflections", default_name, file_filter,
            options=QFileDialog.DontUseNativeDialog,
        )
        if not file_path:
            return  # user cancelled

        if not file_path.lower().endswith(f".{fmt}"):
            file_path += f".{fmt}"

        ctx = self._current_context
        metadata = {
            "cif_filename": ctx.cif_filename,
            "energy_kev": ctx.energy_kev,
            "scattering_type": ctx.scattering_type,
            "source": ctx.source,
            "generated_count": ctx.generated_count,
            "filtered_count": ctx.filtered_count,
            "extinction_rel_tol": ctx.rel_tol,
            "min_intensity_filter": ctx.min_intensity,
            "h_range": list(ctx.h_range) if ctx.h_range else None,
            "k_range": list(ctx.k_range) if ctx.k_range else None,
            "l_range": list(ctx.l_range) if ctx.l_range else None,
        }

        result = self.controller.export_reflections(reflections, metadata, fmt, file_path)
        if result["success"]:
            QMessageBox.information(self, "Export Complete", f"Reflections exported to:\n{file_path}")
        else:
            QMessageBox.critical(self, "Export Failed", result.get("error", "Unknown error"))
