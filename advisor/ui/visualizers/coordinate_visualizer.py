"""This module provides a class for visualizing the coordinate system in a 3D space. More
specifically, it visualizes the relative position of of crystal coordinates with respect to the lab
coordinate system.
"""
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from advisor.domain.core import Lab

class CoordinateVisualizer(FigureCanvas):
    """Visualizer for coordinate system with 3D interactive canvas."""

    def __init__(self, width=4, height=4, dpi=100):
        """Initialize the visualizer with a 3D canvas."""
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111, projection="3d")
        self.axes.set_axis_off()
        super().__init__(self.fig)
    

        # Set background color to white
        self.fig.patch.set_facecolor("white")
        self.axes.set_facecolor("white")

        # Set initial view (adjusted for x-y scattering plane, beam from -y)
        self.axes.view_init(elev=20, azim=30, roll=0)


        # Set initial limits
        self.axes.set_xlim(-0.75, 0.75)
        self.axes.set_ylim(-0.75, 0.75)
        self.axes.set_zlim(-0.75, 0.75)

        # Initialize reciprocal lattice vectors in lab frame
        self.a_star_lab = np.array([1, 0, 0])
        self.b_star_lab = np.array([0, 1, 0])
        self.c_star_lab = np.array([0, 0, 1])
        self.roll = 0
        self.pitch = 0
        self.yaw = 0

    def initialize(self, params: dict):
        """Initialize the visualizer with the given parameters."""
        self.roll = params["roll"]
        self.pitch = params["pitch"]
        self.yaw = params["yaw"]
        a, b, c = params["a"], params["b"], params["c"]
        alpha, beta, gamma = params["alpha"], params["beta"], params["gamma"]

        lab = Lab()
        lab.initialize(
            a, b, c, alpha, beta, gamma, self.roll, self.pitch, self.yaw, 0, 0, 0
        )
        # calculate the corresponding a_star_lab, b_star_lab, c_star_lab
        self.a_star_lab, self.b_star_lab, self.c_star_lab = (
            lab.get_reciprocal_space_vectors()
        )
        return True

    def visualize_lab_system(self):
        """Update the visualization with new crystal coordinates system."""
        # Clear previous plot
        self.axes.clear()

        # Plot the scattering plane (x-y plane, z=0), adjusted for beam from -y
        scatter_plane_vertices = np.array(
            [
                [1.25, -1.25, 0],  # bottom right
                [-0.25, -1.25, 0],  # bottom left
                [1.25, 1.25, 0],  # top right
                [-0.25, 1.25, 0],  # top left
            ]
        )

        scatter_plane_faces = np.array([[0, 1, 3, 2]])  # single face
        self.axes.add_collection3d(
            Poly3DCollection(
                scatter_plane_vertices[scatter_plane_faces],
                facecolors=[0.3010, 0.7450, 0.9330],  # light blue
                edgecolors=[0.7, 0.7, 0.7],
                alpha=0.15,
            )
        )

        # Define vertices of the cube (standing perpendicular to scattering plane)
        # Rotated 90° so thin dimension (0.25) is along x-axis, facing beam from -y
        ver = np.array(
            [
                [0.125, 0.25, 0.5],  # top front right
                [0.125, -0.25, 0.5],  # top front left
                [-0.125, -0.25, 0.5],  # top back left
                [-0.125, 0.25, 0.5],  # top back right
                [0.125, 0.25, -0.5],  # bottom front right
                [0.125, -0.25, -0.5],  # bottom front left
                [-0.125, -0.25, -0.5],  # bottom back left
                [-0.125, 0.25, -0.5],  # bottom back right
            ]
        )

        # Define faces of the cube
        fac = np.array(
            [
                [0, 1, 2, 3],  # top face
                [4, 5, 6, 7],  # bottom face
                [0, 1, 5, 4],  # front face
                [2, 3, 7, 6],  # back face
                [0, 3, 7, 4],  # right face
                [1, 2, 6, 5],  # left face
            ]
        )

        # Plot the cube
        self.axes.add_collection3d(
            Poly3DCollection(
                ver[fac],
                facecolors=[0.3, 0.3, 0.3],
                edgecolors=[0.55, 0.55, 0.55],
                alpha=0.2,
            )
        )

        # Normalize the vectors
        a_star_norm = self.a_star_lab / np.linalg.norm(self.a_star_lab)
        b_star_norm = self.b_star_lab / np.linalg.norm(self.b_star_lab)
        c_star_norm = self.c_star_lab / np.linalg.norm(self.c_star_lab)

        # Plot the normalized vectors
        vectors = [a_star_norm, b_star_norm, c_star_norm]
        colors = ["r", "r", "r"]
        labels = ["$a^*$", "$b^*$", "$c^*$"]

        for vec, color, label in zip(vectors, colors, labels):
            # Plot the vector
            self.axes.quiver(
                0,
                0,
                0,  # origin
                vec[0],
                vec[1],
                vec[2],  # vector components
                color=color,
                alpha=1,
                linewidth=2,
                arrow_length_ratio=0.2,
            )

            # Add text label at the tip of the vector
            # Add a small offset to prevent text from overlapping with the arrow
            offset = 0.2
            self.axes.text(
                vec[0] + offset,
                vec[1] + offset,
                vec[2] + offset,
                label,
                color=color,
                fontsize=14,
                ha="center",
            )

        # plot the vector of the lab coordinate system, by default it is the unit vectors
        e_X = np.array([1, 0, 0]) / 0.65
        e_Y = np.array([0, 1, 0]) / 0.65
        e_Z = np.array([0, 0, 1]) / 0.65
        vectors = [e_X, e_Y, e_Z]
        colors = ["r", "g", "b"]
        labels = ["$X$", "$Y$", "$Z$"]

        for vec, color, label in zip(vectors, colors, labels):
            # Plot the vector
            self.axes.quiver(
                0,
                0,
                0,  # origin
                vec[0],
                vec[1],
                vec[2],  # vector components
                color=(64 / 255, 148 / 255, 184 / 255),
                alpha=1,
                linewidth=0.8,
                arrow_length_ratio=0.1,
            )

            # Add text label at the tip of the vector
            # Add a small offset to prevent text from overlapping with the arrow
            offset = 0.2
            self.axes.text(
                vec[0] + offset,
                vec[1] + offset,
                vec[2] + offset,
                label,
                color=(64 / 255, 148 / 255, 184 / 255),
            )

        # Set axis limits
        self.axes.set_xlim(-1, 1)
        self.axes.set_ylim(-1, 1)
        self.axes.set_zlim(-1, 1)

        self.axes.set_axis_off()
        self.fig.tight_layout()
        # Update the canvas
        self.draw()
