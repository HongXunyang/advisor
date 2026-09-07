"""HKLScan2DVisualizer.clear_plot()/plot_accessible_area(): regression tests
for a bug introduced and then fixed within the same change -- adding
clear_plot() by editing only up through plot_accessible_area()'s last
`self.axes.text(...)` call orphaned that method's real trailing
`self.draw(); return True` into the newly-inserted clear_plot() instead,
so the accessible-region overlay was added to the axes but never actually
drawn until something else redrew the canvas.
"""

from advisor.ui.visualizers.HKLScan2DVisualizer import HKLScan2DVisualizer


class TestPlotAccessibleAreaDrawsAndReturns:
    def test_returns_true_and_actually_draws(self, qapp, monkeypatch):
        viz = HKLScan2DVisualizer()
        drawn = []
        monkeypatch.setattr(viz, "draw", lambda: drawn.append(True))

        result = viz.plot_accessible_area("HK", h_max=2.0, k_max=2.0, l_max=2.0, message="test")

        assert result is True
        assert drawn == [True]

    def test_ellipse_patch_is_added(self, qapp):
        viz = HKLScan2DVisualizer()
        viz.plot_accessible_area("HK", h_max=2.0, k_max=2.0, l_max=2.0)
        assert len(viz.axes.patches) >= 1


class TestClearPlotDoesNotDrawTwiceOrReturnAValue:
    def test_clear_plot_draws_exactly_once(self, qapp, monkeypatch):
        viz = HKLScan2DVisualizer()
        draw_calls = []
        monkeypatch.setattr(viz, "draw", lambda: draw_calls.append(True))

        result = viz.clear_plot()

        assert len(draw_calls) == 1
        assert result is None

    def test_clear_plot_resets_last_scan_results(self, qapp):
        viz = HKLScan2DVisualizer()
        viz.last_scan_results = {"success": True}
        viz.clear_plot()
        assert viz.last_scan_results is None
