from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


class HKLScan2DVisualizer(FigureCanvas):
    """2D visualizer for HKL scan results with structure factor display and trajectory line."""

    def __init__(self, width: float = 5.0, height: float = 4.0, dpi: int = 100, parent=None):
        self.fig = Figure(figsize=(float(width), float(height)), dpi=int(dpi), tight_layout=True)
        super().__init__(self.fig)
        self.axes = self.fig.add_subplot(111)
        self._colorbar = None
        self._initialized = True

        # Default range settings: H,K in (-1,1), L in (-2,2)
        self.default_h_range = (-1.0, 1.0)
        self.default_k_range = (-1.0, 1.0)
        self.default_l_range = (-2.0, 2.0)
        
        # Current range settings
        self.h_range = self.default_h_range
        self.k_range = self.default_k_range
        self.l_range = self.default_l_range
        
        # Store last scan results for trajectory
        self.last_scan_results = None

    def _auto_detect_ranges(self, scan_results):
        """Auto-detect HKL ranges based on scan results.
        
        Args:
            scan_results: Dictionary containing H, K, L arrays from scan
            
        Returns:
            tuple: (h_range, k_range, l_range) where each range is (min, max)
        """
        import math
        epsilon = 1e-6
        try:
            # Extract HKL values from scan results
            h_vals = np.array(scan_results.get("H", []), dtype=np.float64)
            k_vals = np.array(scan_results.get("K", []), dtype=np.float64)
            l_vals = np.array(scan_results.get("L", []), dtype=np.float64)
            
            # Find max absolute values and round up to ceiling
            if len(h_vals) > 0:
                h_max = math.ceil(np.max(np.abs(h_vals)) + epsilon)
                h_range = (-h_max, h_max)
            else:
                h_range = self.default_h_range
                
            if len(k_vals) > 0:
                k_max = math.ceil(np.max(np.abs(k_vals)) + epsilon)
                k_range = (-k_max, k_max)
            else:
                k_range = self.default_k_range
                
            if len(l_vals) > 0:
                l_max = math.ceil(np.max(np.abs(l_vals)) + epsilon)
                l_range = (-l_max, l_max)
            else:
                l_range = self.default_l_range
                
            return h_range, k_range, l_range
            
        except Exception as e:
            print(f"Error auto-detecting ranges: {e}")
            return self.default_h_range, self.default_k_range, self.default_l_range

    def set_ranges(self, h_range=None, k_range=None, l_range=None):
        """Set the plotting ranges for H, K, L indices.
        
        Args:
            h_range: tuple (min, max) for H range, or None to keep current
            k_range: tuple (min, max) for K range, or None to keep current  
            l_range: tuple (min, max) for L range, or None to keep current
        """
        if h_range is not None:
            self.h_range = h_range
        if k_range is not None:
            self.k_range = k_range
        if l_range is not None:
            self.l_range = l_range


    def visualize_results(self, scan_results, plane_type="HK"):
        """Visualize HKL scan results with structure factors and trajectory line.
        
        Args:
            scan_results: Dictionary containing scan results from BrillouinCalculator
            plane_type: "HK", "HL", or "KL" - which plane to visualize
        """
        try:
            if not scan_results or not scan_results.get("success", False):
                self.clear_plot()
                return False
                
            # Store scan results for trajectory
            self.last_scan_results = scan_results
            
            # Auto-detect ranges based on scan results
            h_range, k_range, l_range = self._auto_detect_ranges(scan_results)
            self.set_ranges(h_range, k_range, l_range)
            
            # Extract deactivated index from scan results
            deactivated_index = scan_results.get("deactivated_index", None)
            
            # Map plane type to match deactivated index
            if deactivated_index == "L":
                plane_type = "HK"  # L deactivated means HK plane
                x_label = "H"
                y_label = "K"
                fixed_label = "L"
            elif deactivated_index == "K":
                plane_type = "HL"  # K deactivated means HL plane
                x_label = "H"
                y_label = "L"
                fixed_label = "K"
            elif deactivated_index == "H":
                plane_type = "KL"  # H deactivated means KL plane
                x_label = "K"
                y_label = "L"
                fixed_label = "H"
            
            
            # Plot only the trajectory points as scatter
            success = self._plot_trajectory_only(scan_results, plane_type, x_label, y_label)
            
            return success
            
        except Exception as e:
            print(f"Error in visualize_results: {e}")
            return False

    def _plot_trajectory_only(self, scan_results, plane_type, x_label, y_label):
        """Plot only the trajectory points as scatter without structure factor background.
        
        Args:
            scan_results: Dictionary containing H, K, L arrays from scan
            plane_type: "HK", "HL", or "KL"
            x_label: X axis label ("H", "K", or "L")
            y_label: Y axis label ("H", "K", or "L")
        """
        try:
            # Extract HKL coordinates from scan results
            h_vals = np.array(scan_results.get("H", []), dtype=np.float64)
            k_vals = np.array(scan_results.get("K", []), dtype=np.float64)  
            l_vals = np.array(scan_results.get("L", []), dtype=np.float64)
            
            if len(h_vals) == 0:
                self.clear_plot()
                return False
            
            # Get the appropriate coordinates for the plane
            if plane_type == "HK":
                x_traj = h_vals
                y_traj = k_vals
            elif plane_type == "HL":
                x_traj = h_vals
                y_traj = l_vals
            elif plane_type == "KL":
                x_traj = k_vals
                y_traj = l_vals
            else:
                self.clear_plot()
                return False

            # Reset axes
            if self._colorbar is not None:
                self._colorbar.remove()
                self._colorbar = None
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            self.axes = ax

            # Plot trajectory as scatter points
            # Use different colors for start, middle, and end points
            if len(x_traj) > 0:
                # Plot all points in blue
                scatter = ax.scatter(x_traj, y_traj, c='dodgerblue', s=15, alpha=0.7, 
                                   label='Scan points', zorder=3)
                



            ax.set_xlabel(f"{x_label} (r.l.u.)")
            ax.set_ylabel(f"{y_label} (r.l.u.)")
            ax.set_title(f"{x_label}{y_label} plane")

            # Set limits based on auto-detected ranges for the current plane
            if plane_type == "HK":
                x_min, x_max = self.h_range[0], self.h_range[1]
                y_min, y_max = self.k_range[0], self.k_range[1]
            elif plane_type == "HL":
                x_min, x_max = self.h_range[0], self.h_range[1]
                y_min, y_max = self.l_range[0], self.l_range[1]
            elif plane_type == "KL":
                x_min, x_max = self.k_range[0], self.k_range[1]
                y_min, y_max = self.l_range[0], self.l_range[1]
            else:
                # Fallback to trajectory data range
                x_min, x_max = x_traj.min(), x_traj.max()
                y_min, y_max = y_traj.min(), y_traj.max()
                
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            
            # Add grid and legend
            ax.grid(True, alpha=0.3)
            
            try:
                from matplotlib.ticker import MaxNLocator
                ax.xaxis.set_major_locator(MaxNLocator(integer=True))
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            except Exception:
                pass

            self.draw()
            return True
            
        except Exception as e:
            print(f"Error in _plot_trajectory_only: {e}")
            return False
