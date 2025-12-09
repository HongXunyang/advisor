"""Structure Factor Visualizer for 3D HKL space plotting."""

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class StructureFactorVisualizer3D(FigureCanvas):
    """3D visualizer for structure factors in reciprocal space"""

    def __init__(self, width=8, height=6, dpi=100):
        """Initialize the 3D structure factor visualizer

        Args:
            width: Figure width in inches
            height: Figure height in inches
            dpi: Figure resolution
        """
        # Create figure with proper backend configuration
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        super().__init__(self.fig)

        # Initialize state
        self._initialized = False
        self._colorbar = None

        # Create 3D subplot
        self._create_3d_plot()

        # Plane highlight state
        self._active_plane = None  # one of {"H","K","L"} or None
        self._plane_alpha_active = 0.85
        self._plane_alpha_inactive = 0.4
        self._H_val = None
        self._K_val = None
        self._L_val = None

    def _create_3d_plot(self):
        """Create the 3D subplot and set up basic appearance"""
        try:
            # Clear any existing subplots
            self.fig.clear()

            # Create 3D subplot
            self.axes = self.fig.add_subplot(111, projection="3d")
            # Containers for plane artists
            self._plane_h = None
            self._plane_k = None
            self._plane_l = None
            self._plane_custom = None

            # Set basic labels and title
            self.axes.set_xlabel("H (r.l.u.)", fontsize=10)
            self.axes.set_ylabel("K (r.l.u.)", fontsize=10)
            self.axes.set_zlabel("L (r.l.u.)", fontsize=10)
            #self.axes.set_title("Structure Factors in Reciprocal Space", fontsize=12)

            # Set default axis limits (0, 5) with ±0.5 padding
            self.axes.set_xlim(-0.5, 5.5)
            self.axes.set_ylim(-0.5, 5.5)
            self.axes.set_zlim(-0.5, 5.5)

            # Set integer ticks only
            from matplotlib.ticker import MaxNLocator

            self.axes.xaxis.set_major_locator(MaxNLocator(integer=True))
            self.axes.yaxis.set_major_locator(MaxNLocator(integer=True))
            self.axes.zaxis.set_major_locator(MaxNLocator(integer=True))

            # Set background color
            self.axes.xaxis.pane.fill = False
            self.axes.yaxis.pane.fill = False
            self.axes.zaxis.pane.fill = False

            # Make grid lines less prominent
            self.axes.grid(True, alpha=0.3)

            # Set default viewing angle (rotate 180° around Z compared to prior)
            self.axes.view_init(elev=12.5, azim=200)

        except Exception as e:
            print(f"Error creating 3D plot: {e}")

    def initialize(self, params: dict = None):
        """Initialize the visualizer

        Args:
            params: Optional parameters (not used for structure factor visualization)
        """
        self._initialized = True
        self._create_3d_plot()
        self.draw()
        return True

    # --- Plane overlay API ---
    def set_plane_values(self, H=None, K=None, L=None):
        """Update translucent planes at constant H, K, L. Any None leaves it unchanged.

        Args:
            H: fixed H value for K-L plane (x = H)
            K: fixed K value for H-L plane (y = K)
            L: fixed L value for H-K plane (z = L)
        """
        try:
            ax = self.axes
            # Determine display extents from current limits
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            z_min, z_max = ax.get_zlim()

            import numpy as np

            # Helper to draw/update a plane
            def draw_plane(current, new_artist_name, const_val, axis: str):
                if const_val is None:
                    return current
                # Remove existing
                if current is not None:
                    try:
                        current.remove()
                    except Exception:
                        pass
                # Choose alpha based on active plane selection
                alpha = (
                    self._plane_alpha_active
                    if (self._active_plane is not None and axis == self._active_plane)
                    else self._plane_alpha_inactive
                )
                color = {
                    "H": (1.0, 0.8, 0.86, alpha),  # pinkish
                    "K": (0.80, 0.92, 0.773, alpha),  # greenish
                    "L": (0.635, 0.812, 0.996, alpha),  # bluish
                }[axis]

                if axis == "H":
                    X = np.full((2, 2), const_val)
                    Y = np.array([[y_min, y_min], [y_max, y_max]])
                    Z = np.array([[z_min, z_max], [z_min, z_max]])
                elif axis == "K":
                    X = np.array([[x_min, x_min], [x_max, x_max]])
                    Y = np.full((2, 2), const_val)
                    Z = np.array([[z_min, z_max], [z_min, z_max]])
                else:  # L
                    X = np.array([[x_min, x_max], [x_min, x_max]])
                    Y = np.array([[y_min, y_min], [y_max, y_max]])
                    Z = np.full((2, 2), const_val)

                artist = ax.plot_surface(X, Y, Z, color=color, linewidth=0, shade=False)
                return artist

            self._plane_h = draw_plane(self._plane_h, "_plane_h", H, "H")
            self._plane_k = draw_plane(self._plane_k, "_plane_k", K, "K")
            self._plane_l = draw_plane(self._plane_l, "_plane_l", L, "L")

            # Store current plane constants for future redraws
            if H is not None:
                self._H_val = H
            if K is not None:
                self._K_val = K
            if L is not None:
                self._L_val = L

            self.draw()
        except Exception as e:
            print(f"Error updating planes: {e}")

    def is_initialized(self):
        """Check if the visualizer is initialized"""
        return self._initialized

    def set_active_plane(
        self, axis: str, alpha_active: float = None, alpha_inactive: float = None
    ):
        """Highlight one of the planes by adjusting alpha values.

        Args:
            axis: one of "H", "K", or "L"
            alpha_active: optional override for active plane alpha
            alpha_inactive: optional override for inactive plane alpha
        """
        try:
            axis = (axis or "").upper()
            if axis not in {"H", "K", "L"}:
                return
            if alpha_active is not None:
                self._plane_alpha_active = float(alpha_active)
            if alpha_inactive is not None:
                self._plane_alpha_inactive = float(alpha_inactive)
            self._active_plane = axis
            # Redraw existing planes to apply new alphas
            # Re-issue current values for any planes we know
            if self._H_val is not None:
                self.set_plane_values(H=self._H_val)
            if self._K_val is not None:
                self.set_plane_values(K=self._K_val)
            if self._L_val is not None:
                self.set_plane_values(L=self._L_val)
        except Exception as e:
            print(f"Error setting active plane: {e}")

    # --- Custom plane overlay (spanned by two vectors) ---
    def set_custom_plane(
        self,
        vector_u: tuple,
        vector_v: tuple,
        u_min: float = -5.0,
        u_max: float = 5.0,
        v_min: float = -5.0,
        v_max: float = 5.0,
        steps: int = 2,
        center: tuple = (0, 0, 0),
    ):
        """Overlay a translucent plane spanned by two vectors in HKL space.

        Args:
            vector_u: (h, k, l) tuple for the first spanning vector
            vector_v: (h, k, l) tuple for the second spanning vector
            u_min/u_max: parameter range along vector_u
            v_min/v_max: parameter range along vector_v
            steps: grid resolution along each parameter (2 draws a quad)
            center: (h, k, l) tuple shifting the plane center in HKL space
        """
        try:
            # Remove existing custom plane
            if self._plane_custom is not None:
                try:
                    self._plane_custom.remove()
                except Exception:
                    pass
                self._plane_custom = None

            # Build parametric grid
            import numpy as np

            u_vals = np.linspace(u_min, u_max, max(2, int(steps)))
            v_vals = np.linspace(v_min, v_max, max(2, int(steps)))
            U, V = np.meshgrid(u_vals, v_vals)

            uh, uk, ul = vector_u
            vh, vk, vl = vector_v

            ch, ck, cl = center

            X = ch + (U * uh + V * vh)
            Y = ck + (U * uk + V * vk)
            Z = cl + (U * ul + V * vl)

            color = (0.9, 0.9, 0.2, 0.35)  # yellowish translucent
            self._plane_custom = self.axes.plot_surface(
                X, Y, Z, color=color, linewidth=1, shade=False
            )
            self.draw()
        except Exception as e:
            print(f"Error drawing custom plane: {e}")

    def visualize_structure_factors(self, hkl_list, sf_values):
        """Visualize structure factors as 3D scatter plot

        Args:
            hkl_list: List of [h, k, l] indices, shape (N, 3)
            sf_values: Array of structure factor magnitudes, shape (N,)
        """
        try:
            # Validate inputs
            if len(hkl_list) == 0 or len(sf_values) == 0:
                print("Warning: Empty HKL list or structure factor values")
                return False

            if len(hkl_list) != len(sf_values):
                print(
                    f"Error: HKL list length ({len(hkl_list)}) != SF values length ({len(sf_values)})"
                )
                return False

            # Remove existing colorbar if present
            if self._colorbar is not None:
                self._colorbar.remove()
                self._colorbar = None

            # Clear and recreate the 3D subplot
            self.fig.clear()
            self.axes = self.fig.add_subplot(111, projection="3d")

            # Convert to numpy arrays for easier handling
            hkl_array = np.array(hkl_list)
            sf_array = np.array(sf_values)

            # Extract H, K, L coordinates
            h_coords = hkl_array[:, 0]
            k_coords = hkl_array[:, 1]
            l_coords = hkl_array[:, 2]

            # Calculate dot sizes based on structure factor magnitude
            # Scale factors for visibility
            min_size = 0  # Increased minimum dot size for better visibility
            max_size = 300  # Increased maximum dot size

            print(f"SF array max: {sf_array.max()}, min: {sf_array.min()}")

            # Normalize structure factor values for sizing
            if sf_array.max() > 0:
                normalized_sf = sf_array / sf_array.max()
                dot_sizes = min_size + (max_size - min_size) * normalized_sf
            else:
                dot_sizes = np.full(len(sf_array), min_size)

            mask = dot_sizes < 1
            h_coords_plot = h_coords[~mask]
            k_coords_plot = k_coords[~mask]
            l_coords_plot = l_coords[~mask]
            sf_array_plot = sf_array[~mask]
            dot_sizes_plot = dot_sizes[~mask]
            # Create scatter plot
            scatter = self.axes.scatter(
                h_coords_plot,
                k_coords_plot,
                l_coords_plot,
                s=dot_sizes_plot,
                c=sf_array_plot,
                cmap="viridis",
                alpha=0.9,  # More opaque for better visibility
            )

            print(f"Created scatter plot with {len(h_coords)} points")

            # Add text labels next to each dot
            is_label_visible = False
            if is_label_visible:
                for i, (h, k, l) in enumerate(zip(h_coords, k_coords, l_coords)):
                    if mask[i]:
                        color_font = "silver"
                    else:
                        color_font = "black"
                    # Create label text (e.g., "010" for [0,1,0])
                    label = f"{h}{k}{l}"

                    # Add text annotation with slight offset
                    self.axes.text(
                        h + 0.1,
                        k + 0.1,
                        l + 0.1,  # Small offset from dot position
                        label,
                        fontsize=8,
                        ha="left",
                        va="bottom",
                        color=color_font,
                    )

                print(f"Added text labels for {len(hkl_list)} points")

            # Add colorbar
            self._colorbar = self.fig.colorbar(
                scatter, ax=self.axes, label="|Structure Factor|", shrink=0.6, pad=0.1
            )

            # Set axis labels and title
            self.axes.set_xlabel("H (r.l.u.)", fontsize=10)
            self.axes.set_ylabel("K (r.l.u.)", fontsize=10)
            self.axes.set_zlabel("L (r.l.u.)", fontsize=10)
            self.axes.set_title("Structure Factors in Reciprocal Space", fontsize=12)

            # Set axis limits with default range (0, 5) and adjust if needed
            default_max = 5.5

            # Calculate required ranges based on data with ±0.5 margin
            default_min = -0.5
            h_min = min(h_coords.min(), 0) - 0.5
            k_min = min(k_coords.min(), 0) - 0.5
            l_min = min(l_coords.min(), 0) - 0.5
            h_max = max(h_coords.max() + 0.5, default_max)
            k_max = max(k_coords.max() + 0.5, default_max)
            l_max = max(l_coords.max() + 0.5, default_max)

            # Set limits from calculated min to max
            self.axes.set_xlim(h_min if not np.isnan(h_min) else default_min, h_max)
            self.axes.set_ylim(k_min if not np.isnan(k_min) else default_min, k_max)
            self.axes.set_zlim(l_min if not np.isnan(l_min) else default_min, l_max)

            # Set integer ticks only
            from matplotlib.ticker import MaxNLocator

            self.axes.xaxis.set_major_locator(MaxNLocator(integer=True))
            self.axes.yaxis.set_major_locator(MaxNLocator(integer=True))
            self.axes.zaxis.set_major_locator(MaxNLocator(integer=True))

            print(f"Set axis limits: X(0, {h_max}), Y(0, {k_max}), Z(0, {l_max})")

            # Improve 3D viewing angle (rotated 180° around Z)
            self.axes.view_init(elev=12.5, azim=200)

            # Enable grid with low alpha
            self.axes.grid(True, alpha=0.3)

            # Update the canvas
            self.draw()

            print(f"Successfully plotted {len(hkl_list)} structure factors")
            return True

        except Exception as e:
            print(f"Error in visualize_structure_factors: {e}")
            return False

    def clear_plot(self):
        """Clear the current plot"""
        try:
            # Remove existing colorbar if present
            if self._colorbar is not None:
                self._colorbar.remove()
                self._colorbar = None

            # Recreate the 3D plot
            self._create_3d_plot()
            self.draw()
        except Exception as e:
            print(f"Error clearing plot: {e}")

    def visualize(self):
        """Create an empty visualization (placeholder)"""
        try:
            self._create_3d_plot()
            self.draw()
            return True
        except Exception as e:
            print(f"Error in visualize: {e}")
            return False
