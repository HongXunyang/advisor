"""2D Structure Factor Visualizer for sliced HK/HL/KL planes"""

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


class StructureFactorVisualizer2D(FigureCanvas):
    """2D visualizer that shows a sliced plane of HKL with fixed index.

    The canvas renders a 2D scatter where marker size and color scale with
    the magnitude of the structure factor.
    """

    def __init__(self, width: float = 5.0, height: float = 4.0, dpi: int = 100):
        self.fig = Figure(figsize=(float(width), float(height)), dpi=int(dpi), tight_layout=True)
        super().__init__(self.fig)
        self.axes = self.fig.add_subplot(111)
        self._colorbar = None
        self._initialized = True

    def clear_plot(self):
        try:
            if self._colorbar is not None:
                self._colorbar.remove()
                self._colorbar = None
            self.fig.clear()
            self.axes = self.fig.add_subplot(111)
            # Default range 0..5 with ±0.5 padding
            self.axes.set_xlim(-0.5, 5.5)
            self.axes.set_ylim(-0.5, 5.5)
            self.draw()
        except Exception:
            # Keep UI responsive even if clear fails
            pass

    def visualize_uv_plane_points(
        self,
        uv_points,
        sf_values,
        vector_u_label: str,
        vector_v_label: str,
        vector_center=None,
        value_max=None,
    ):
        """Render points in a user-defined plane parameterized by integers u,v.

        Args:
            uv_points: list of dicts with keys {'u','v','H','K','L'} for labels
            sf_values: 1D array-like of |F| values per point
            vector_u_label: text label for u-axis (e.g., "[h k l] of U")
            vector_v_label: text label for v-axis
            vector_center: a vector for center of the plane (e.g. [0,0,0])
        """
        try:
            import numpy as np

            if len(uv_points) == 0:
                return False
            u = np.array([p['u'] for p in uv_points])
            v = np.array([p['v'] for p in uv_points])
            f = np.asarray(sf_values)
            if value_max is None:
                value_max = f.max() if len(f) > 0 else 1.0

            if len(u) != len(v) or len(u) != len(f):
                return False

            # Reset axes
            if self._colorbar is not None:
                self._colorbar.remove()
                self._colorbar = None
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            self.axes = ax

            # Normalize sizes
            min_size, max_size = 0, 300
            if value_max > 0:
                sizes = min_size + (max_size - min_size) * (f / value_max)
            else:
                sizes = np.full_like(f, min_size, dtype=float)

            mask = sizes < 1
            sizes = sizes[~mask]
            u_plot = u[~mask]
            v_plot = v[~mask]
            f_plot = f[~mask]

            sc = ax.scatter(u_plot, v_plot, c=f_plot, s=sizes, cmap="viridis", alpha=0.9, vmax=value_max)

            # Labels per point with HKL
            for i, p in enumerate(uv_points):
                if mask[i]:
                    color_font = "silver"
                else:
                    color_font = "black"
                ax.text(
                    p['u'] + 0.05,
                    p['v'] + 0.05,
                    f"{p['H']} {p['K']} {p['L']}",
                    fontsize=7,
                    color=color_font,
                )

            ax.set_xlabel(f"u along {vector_u_label}")
            ax.set_ylabel(f"v along {vector_v_label}")
            if vector_center is not None:
                cx, cy, cz = vector_center
                subtitle = f" centered at [{cx} {cy} {cz}]"
            else:
                subtitle = ""

            # Limits and integer ticks
            u_min, u_max = u.min(), u.max()
            v_min, v_max = v.min(), v.max()
            ax.set_xlim(u_min - 0.5, u_max + 0.5)
            ax.set_ylim(v_min - 0.5, v_max + 0.5)
            try:
                from matplotlib.ticker import MaxNLocator
                ax.xaxis.set_major_locator(MaxNLocator(integer=True))
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            except Exception:
                pass
            ax.grid(True, alpha=0.3)
            self.draw()
            return True
        except Exception:
            return False

    def visualize_plane(
        self,
        x_values,
        y_values,
        sf_values,
        x_label: str,
        y_label: str,
        fixed_name: str,
        fixed_value: int,
        value_max = None,
    ):
        """Render a 2D plane plot.

        Args:
            x_values: 1D array-like for x-axis (e.g., H)
            y_values: 1D array-like for y-axis (e.g., K)
            sf_values: 1D array-like magnitudes |F|
            x_label: which HKL index the x-axis represents ("H"|"K"|"L")
            y_label: which HKL index the y-axis represents ("H"|"K"|"L")
            fixed_name: the fixed HKL index ("H"|"K"|"L")
            fixed_value: the integer value of the fixed index
        Returns:
            bool indicating success
        """
        try:
            x = np.asarray(x_values)
            y = np.asarray(y_values)
            f = np.asarray(sf_values)
            if value_max is None:
                value_max = f.max()
            if len(x) == 0 or len(y) == 0 or len(f) == 0 or len(x) != len(y) or len(x) != len(f):
                return False

            # Reset axes
            if self._colorbar is not None:
                self._colorbar.remove()
                self._colorbar = None
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            self.axes = ax

            # Normalize for size
            min_size, max_size = 0, 300
            if value_max > 0:
                sizes = min_size + (max_size - min_size) * (f / value_max)
            else:
                sizes = np.full_like(f, min_size, dtype=float)

            mask = sizes < 1
            sizes = sizes[~mask]
            x_plot = x[~mask]
            y_plot = y[~mask]
            f_plot = f[~mask]

            sc = ax.scatter(x_plot, y_plot, c=f_plot, s=sizes, cmap="viridis", alpha=0.9, vmax=value_max)

            # Add labels for each point (e.g., integer coordinates)
            x_key = x_label.upper()
            y_key = y_label.upper()
            f_key = fixed_name.upper()
            
            for i, (xi, yi) in enumerate(zip(x, y)):
                if mask[i]:
                    color_font = "silver"
                else:
                    color_font = "black"
                values = {"H": None, "K": None, "L": None}
                values[x_key] = int(round(float(xi)))
                values[y_key] = int(round(float(yi)))
                values[f_key] = int(fixed_value)
                ax.text(
                    xi + 0.05,
                    yi + 0.05,
                    f"{values['H']} {values['K']} {values['L']}",
                    fontsize=7,
                    color=color_font,
                )

            # Colorbar intentionally removed for cleaner 2D view

            ax.set_xlabel(f"{x_label} (r.l.u.)")
            ax.set_ylabel(f"{y_label} (r.l.u.)")
            ax.set_title(f"{x_label}{y_label} plane | {fixed_name} = {fixed_value}")

            # Set limits and integer ticks
            # Default limits 0..5 with auto-expand if needed
            x_max = max(x.max(), 5)
            y_max = max(y.max(), 5)
            ax.set_xlim(-0.5, x_max + 0.5)
            ax.set_ylim(-0.5, y_max + 0.5)
            try:
                from matplotlib.ticker import MaxNLocator

                ax.xaxis.set_major_locator(MaxNLocator(integer=True))
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            except Exception:
                pass

            ax.grid(True, alpha=0.3)
            self.draw()
            return True
        except Exception:
            return False


