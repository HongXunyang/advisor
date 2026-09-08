"""Shared presentation for the scientific workspace; no calculation state."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractSpinBox, QGroupBox, QLabel, QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QTabWidget, QTableWidget, QVBoxLayout, QWidget,
)


def control_rail(*controls, pin_action=None):
    """Keep forms compact and allow vertical scrolling on small displays."""
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    for control in controls:
        layout.addWidget(control)
    layout.addStretch(1)
    scroll = QScrollArea()
    scroll.setObjectName("workspaceRail")
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setFrameShape(QScrollArea.NoFrame)
    scroll.setWidget(content)
    if pin_action is not None:
        pin_action.parentWidget().layout().removeWidget(pin_action)
        wrapper = QWidget()
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll, 1)
        outer.addWidget(pin_action)
        return wrapper
    return scroll


def plot_tabs(*plots):
    """Keep the primary plot first, with supporting views one click away."""
    tabs = QTabWidget()
    tabs.setObjectName("workspacePlotTabs")
    for title, widget in plots:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(widget)
        widget.setMinimumSize(120, 120)
        widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        tabs.addTab(page, title)
    return tabs


def polish_workspace(root):
    """Mark only existing workspace controls, excluding future child dialogs."""
    root.setProperty("workRole", "workspace")
    for widget in root.findChildren(QWidget):
        if type(widget) is QWidget and widget.layout():
            widget.layout().setContentsMargins(0, 0, 0, 0)
            widget.layout().setSpacing(6)
    for group in root.findChildren(QGroupBox):
        group.setProperty("workRole", "panel")
        group.layout().setContentsMargins(12, 14, 12, 10)
        group.layout().setSpacing(8)
        group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
    for label in root.findChildren(QLabel):
        if label.property("workRole") is None:
            label.setProperty("workRole", "text")
    for field in root.findChildren(QAbstractSpinBox) + root.findChildren(QLineEdit):
        if isinstance(field, QLineEdit) and isinstance(field.parent(), QAbstractSpinBox):
            continue
        field.setProperty("workRole", "output" if field.isReadOnly() else "field")
    for button in root.findChildren(QPushButton):
        if button.isCheckable():
            button.setProperty("workRole", "toggle")
        elif button.text().startswith(("Calculate", "Initialize Calculator")):
            button.setProperty("workRole", "primary")
        else:
            button.setProperty("workRole", "secondary")
        if button.text() == "Show History":
            button.setText("History…")
            button.setMaximumWidth(110)
            if button.parentWidget().layout():
                button.parentWidget().layout().setAlignment(button, Qt.AlignRight)
    for table in root.findChildren(QTableWidget):
        table.setProperty("workRole", "results")
        table.verticalHeader().setDefaultSectionSize(26)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
    for tabs in root.findChildren(QTabWidget):
        if not tabs.objectName():
            tabs.setObjectName("workspaceSubtabs")


def fit_atomic_preview(canvas):
    """Fit the existing atomic drawing and legend without changing its data."""
    if canvas.render_error_message or not canvas.is_initialized:
        return
    axes, figure = canvas.axes, canvas.fig
    figure.subplots_adjust(left=0.04, right=0.96, bottom=0.2, top=0.94)
    axes.set_box_aspect(axes.get_box_aspect(), zoom=0.72)
    for text in axes.texts:
        text.set_fontsize(9)
    handles, labels = axes.get_legend_handles_labels()
    if handles:
        axes.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.01),
                    bbox_transform=figure.transFigure, ncol=min(3, len(handles)),
                    fontsize=8, frameon=False)
    canvas.draw_idle()
