"""Tests for advisor.ui.visualizers.structure_factor_visualizer_2d."""
import numpy as np
import pytest

from advisor.ui.visualizers.structure_factor_visualizer_2d import (
    StructureFactorVisualizer2D,
    _format_magnitude,
    _hkl_for_plane_point,
)


class _FakeMouseEvent:
    """Minimal stand-in for a matplotlib MouseEvent, for headless hover tests."""

    def __init__(self, inaxes, x, y):
        self.inaxes = inaxes
        self.x = x
        self.y = y


@pytest.fixture
def visualizer(qapp):
    return StructureFactorVisualizer2D()


def _hover_at_data_point(visualizer, x_data, y_data):
    """Simulate a mouse-move event exactly at a data point and dispatch it."""
    px, py = visualizer.axes.transData.transform((x_data, y_data))
    event = _FakeMouseEvent(inaxes=visualizer.axes, x=px, y=py)
    visualizer._on_hover_motion(event)
    return event


class TestFormatMagnitude:
    def test_zero(self):
        assert _format_magnitude(0) == "0"

    def test_small_value_not_rounded_to_zero(self):
        assert _format_magnitude(1e-6) == "1e-06"

    def test_typical_value_three_sig_figs(self):
        assert _format_magnitude(123.456) == "123"

    def test_sub_one_value(self):
        assert _format_magnitude(0.0421) == "0.0421"


class TestHklForPlanePoint:
    def test_reconstructs_all_three_indices(self):
        values = _hkl_for_plane_point(2.0, 3.0, "H", "K", "L", 5)
        assert values == {"H": 2, "K": 3, "L": 5}

    def test_handles_different_axis_assignment(self):
        values = _hkl_for_plane_point(1.0, 4.0, "K", "L", "H", 7)
        assert values == {"H": 7, "K": 1, "L": 4}


class TestVisualizePlaneHoverRecords:
    def test_masked_points_excluded_from_hover_records(self, visualizer):
        x = np.array([0, 1, 2])
        y = np.array([0, 0, 0])
        f = np.array([0.1, 5.0, 300.0])  # value_max=300 -> sizes == f; 0.1 gets masked
        ok = visualizer.visualize_plane(x, y, f, "H", "K", "L", 0, value_max=300)
        assert ok is True
        assert len(visualizer._hover_records) == 2
        assert visualizer._hover_records[0] == {
            "H": 1, "K": 0, "L": 0, "f": 5.0, "x": 1.0, "y": 0.0,
        }
        assert visualizer._hover_records[1] == {
            "H": 2, "K": 0, "L": 0, "f": 300.0, "x": 2.0, "y": 0.0,
        }

    def test_hover_index_resets_on_redraw(self, visualizer):
        x = np.array([0, 1])
        y = np.array([0, 0])
        f = np.array([5.0, 300.0])
        visualizer.visualize_plane(x, y, f, "H", "K", "L", 0, value_max=300)
        _hover_at_data_point(visualizer, 0, 0)
        assert visualizer._hover_index == 0

        # Redraw (e.g. slider/plane change) must invalidate stale hover state.
        visualizer.visualize_plane(x, y, f, "H", "K", "L", 1, value_max=300)
        assert visualizer._hover_index is None


class TestVisualizeUvPlaneHoverRecords:
    def test_masked_points_excluded_from_hover_records(self, visualizer):
        uv_points = [
            {"u": 0, "v": 0, "H": 0, "K": 0, "L": 0},
            {"u": 1, "v": 0, "H": 1, "K": 0, "L": 0},
            {"u": 2, "v": 0, "H": 2, "K": 0, "L": 0},
        ]
        f = [0.1, 5.0, 300.0]
        ok = visualizer.visualize_uv_plane_points(
            uv_points, f, "U", "V", vector_center=(0, 0, 0), value_max=300
        )
        assert ok is True
        assert len(visualizer._hover_records) == 2
        assert visualizer._hover_records[0]["H"] == 1
        assert visualizer._hover_records[0]["f"] == 5.0
        assert visualizer._hover_records[1]["H"] == 2
        assert visualizer._hover_records[1]["f"] == 300.0

    def test_hover_index_resets_on_clear(self, visualizer):
        uv_points = [
            {"u": 0, "v": 0, "H": 0, "K": 0, "L": 0},
            {"u": 1, "v": 0, "H": 1, "K": 0, "L": 0},
        ]
        f = [5.0, 300.0]
        visualizer.visualize_uv_plane_points(uv_points, f, "U", "V", value_max=300)
        _hover_at_data_point(visualizer, 0, 0)
        assert visualizer._hover_index == 0

        visualizer.clear_plot()
        assert visualizer._hover_records == []
        assert visualizer._hover_index is None


class TestHoverInteraction:
    def _setup(self, visualizer):
        x = np.array([0, 1, 2])
        y = np.array([0, 0, 0])
        f = np.array([5.0, 50.0, 300.0])
        visualizer.visualize_plane(x, y, f, "H", "K", "L", 0, value_max=300)

    def test_nearest_point_selected_and_tooltip_text_correct(self, visualizer):
        self._setup(visualizer)
        _hover_at_data_point(visualizer, 1, 0)
        assert visualizer._hover_index == 1
        assert visualizer._hover_annotation.get_visible() is True
        assert visualizer._hover_annotation.get_text() == "|F|: 50"

    def test_same_point_does_not_trigger_redundant_redraw(self, visualizer, monkeypatch):
        self._setup(visualizer)
        calls = []
        monkeypatch.setattr(visualizer, "draw_idle", lambda: calls.append(1))

        _hover_at_data_point(visualizer, 1, 0)
        _hover_at_data_point(visualizer, 1, 0)

        assert len(calls) == 1

    def test_different_point_triggers_redraw_and_updates_text(self, visualizer, monkeypatch):
        self._setup(visualizer)
        calls = []
        monkeypatch.setattr(visualizer, "draw_idle", lambda: calls.append(1))

        _hover_at_data_point(visualizer, 0, 0)
        _hover_at_data_point(visualizer, 2, 0)

        assert len(calls) == 2
        assert visualizer._hover_annotation.get_text() == "|F|: 300"

    def test_out_of_radius_hides_tooltip(self, visualizer):
        self._setup(visualizer)
        _hover_at_data_point(visualizer, 1, 0)
        assert visualizer._hover_index == 1

        event = _FakeMouseEvent(inaxes=visualizer.axes, x=-10_000, y=-10_000)
        visualizer._on_hover_motion(event)

        assert visualizer._hover_index is None
        assert visualizer._hover_annotation.get_visible() is False

    def test_event_outside_axes_hides_tooltip(self, visualizer):
        self._setup(visualizer)
        _hover_at_data_point(visualizer, 1, 0)
        assert visualizer._hover_index == 1

        event = _FakeMouseEvent(inaxes=None, x=0, y=0)
        visualizer._on_hover_motion(event)

        assert visualizer._hover_index is None

    def test_leaving_axes_hides_tooltip(self, visualizer):
        self._setup(visualizer)
        _hover_at_data_point(visualizer, 1, 0)
        assert visualizer._hover_index == 1

        visualizer._on_axes_leave(None)

        assert visualizer._hover_index is None
        assert visualizer._hover_annotation.get_visible() is False

    def test_hover_state_cleared_after_clear_plot(self, visualizer):
        self._setup(visualizer)
        _hover_at_data_point(visualizer, 1, 0)
        assert visualizer._hover_index == 1

        visualizer.clear_plot()

        assert visualizer._hover_records == []
        assert visualizer._hover_index is None

    def test_hover_ignored_before_any_plot_drawn(self, qapp):
        fresh = StructureFactorVisualizer2D()
        event = _FakeMouseEvent(inaxes=fresh.axes, x=0, y=0)
        # Must not raise even though no data has been plotted yet.
        fresh._on_hover_motion(event)
        assert fresh._hover_index is None

    def test_overlay_inaccessible_points_does_not_affect_hover_records(self, visualizer):
        self._setup(visualizer)
        before = list(visualizer._hover_records)

        visualizer.overlay_inaccessible_points([{"u": 1, "v": 0}])

        assert visualizer._hover_records == before

    def test_hover_annotation_excluded_from_layout(self, visualizer):
        self._setup(visualizer)
        # Must be excluded from tight_layout's bbox calculation, otherwise the
        # axes visibly resize every time the tooltip appears/moves near an edge.
        assert visualizer._hover_annotation.get_in_layout() is False

    def test_hovering_near_edge_does_not_resize_axes(self, visualizer):
        # A grid point right at the corner of the default axis limits is the
        # case where an in-layout annotation would force tight_layout to
        # shrink the axes to make room for the tooltip box.
        x = np.array([0, 5])
        y = np.array([0, 5])
        f = np.array([50.0, 300.0])
        visualizer.visualize_plane(x, y, f, "H", "K", "L", 0, value_max=300)
        visualizer.draw()
        bbox_before = visualizer.axes.get_position().bounds

        _hover_at_data_point(visualizer, 5, 5)
        visualizer.draw()

        assert visualizer.axes.get_position().bounds == bbox_before

    def test_hover_radius_is_12px(self, visualizer):
        assert visualizer._hover_radius_px == 12
