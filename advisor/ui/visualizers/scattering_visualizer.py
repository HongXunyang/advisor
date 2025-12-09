#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This is a class to visualize the X-ray scattering geometry."""
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from advisor.domain import (
    get_reciprocal_space_vectors,
    get_rotation,
)
from advisor.domain.core import Lab

class ScatteringVisualizer(FigureCanvas):
    """Visualizer for scattering geometry with 3D interactive canvas."""

    def __init__(self, width=4, height=4, dpi=100):
        """Initialize the visualizer with a 3D canvas."""
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111, projection="3d")
        super().__init__(self.fig)

        # Set initial view (adjusted for x-y scattering plane, beam from -y)
        self.axes.view_init(elev=20, azim=30, roll=0)
        
        # Initialize reciprocal lattice vectors in lab frame
        self.a_star_lab = np.array([1, 0, 0])
        self.b_star_lab = np.array([0, 1, 0])
        self.c_star_lab = np.array([0, 0, 1])
        self.roll = 0
        self.pitch = 0
        self.yaw = 0

    def initialize(self, params: dict):
        """Initialize the visualizer with the given crystal coordinates system."""
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
            lab.get_reciprocal_space_vectors(is_normalized=True)
        )
        self.a_lab, self.b_lab, self.c_lab = lab.get_real_space_vectors(is_normalized=True)
        self.visualize_lab_system()
        return True

    def visualize_lab_system(self, chi=0, phi=0, plot_k_basis=True, plot_basis = False, is_clear=True):
        """Update the visualization with new crystal coordinates system."""
        if is_clear:
            # Clear previous plot
            self.axes.clear()

        # Define vertices of the sample (standing perpendicular to scattering plane)
        # Rotated 90° so thin dimension (0.25) is along x-axis, facing beam from -y
        vertices_sample = np.array(
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
        vertices_sample = _rotate_vertices(vertices_sample, phi, chi)
        # Define faces of the cube
        faces_sample = np.array(
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
                vertices_sample[faces_sample],
                facecolors=[0.3, 0.3, 0.3],
                edgecolors=[0.55, 0.55, 0.55, 0.2],
                alpha=0.05,
            )
        )

        # add extra color to the top face

        # add extra color to the top face
        self.axes.add_collection3d(
            Poly3DCollection(
                [vertices_sample[faces_sample[0]]],
                facecolors=[0.3, 0.3, 0.3],
                edgecolors=[0.55, 0.55, 0.55, 0.1],
                alpha=0.25,
            )
        )
        
        a_star_norm = self.a_star_lab if plot_k_basis else [0, 0, 0]
        a_star_label = "$a^*$" if plot_k_basis else None
        b_star_norm = self.b_star_lab if plot_k_basis else [0, 0, 0]
        b_star_label = "$b^*$" if plot_k_basis else None
        c_star_norm = self.c_star_lab if plot_k_basis else [0, 0, 0]
        c_star_label = "$c^*$" if plot_k_basis else None
        a_norm = self.a_lab if plot_basis else [0, 0, 0]
        a_label = "$a$" if plot_basis else None
        b_norm = self.b_lab if plot_basis else [0, 0, 0]
        b_label = "$b$" if plot_basis else None
        c_norm = self.c_lab if plot_basis else [0, 0, 0]
        c_label = "$c$" if plot_basis else None

        # Plot the normalized vectors
        vectors = [a_star_norm, b_star_norm, c_star_norm, a_norm, b_norm, c_norm]
        vectors = _rotate_vertices(vectors, phi, chi)
        colors = ["tomato", "tomato", "tomato", "dodgerblue", "dodgerblue", "dodgerblue"]
        labels = [a_star_label, b_star_label, c_star_label, a_label, b_label, c_label]

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
                alpha=0.25,
                linewidth=2,
                arrow_length_ratio=0.2,
            )

            # Add text label at the tip of the vector
            # Add a small offset to prevent text from overlapping with the arrow
            offset = 0.1
            self.axes.text(
                vec[0] + offset+0.1,
                vec[1] + offset,
                vec[2] + offset,
                label,
                color=color,
                fontsize=14,
                ha="center",
                alpha=0.4,
            )

        # plot the vector of the lab coordinate system, by default it is the unit vectors
        e_X = np.array([1, 0, 0]) / 0.65
        e_Y = np.array([0, 1, 0]) / 0.65
        e_Z = np.array([0, 0, 1]) / 0.65
        vectors = [e_X, e_Y, e_Z]
        #vectors = _rotate_vertices(vectors, phi, chi)
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
                alpha=0.4,
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
                alpha=0.4,
            )

        # Update the canvas
        # Set axis limits
        self.axes.set_xlim(-1, 1)
        self.axes.set_ylim(-1, 1)
        self.axes.set_zlim(-1, 1)

        self.axes.set_axis_off()
        self.fig.tight_layout()
        self.draw()

    def visualize_scattering_geometry(self, scattering_angles=None, is_clear=False):
        """Update the visualization with new scattering angles."""
        if is_clear:
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
                facecolors=[0.3510, 0.7850, 0.9330],  # light blue
                edgecolors=[0.7, 0.7, 0.7],
                alpha=0.3,
            )
        )

        # Plot the x-ray beam
        if scattering_angles is None:
            scattering_angles = {
                "theta": 50,
                "tth": 150,
            }

        # Extract angles from data
        theta = scattering_angles.get("theta", 50)  # theta angle
        tth = scattering_angles.get("tth", 150)  # two theta angle

        # Plot incident beam (k_in) - coming from -y direction (x-y plane)
        offset = 0
        k_in_length = 1.3
        # Rotated 90° so theta=0 means beam comes from -y direction
        k_in_x = -k_in_length * np.sin(np.radians(theta))
        k_in_y = -k_in_length * np.cos(np.radians(theta))
        k_in_z = 0
        # Draw colored arrow on top
        self.axes.quiver(
            -k_in_x,
            -k_in_y + offset,
            -k_in_z,
            k_in_x,
            k_in_y,
            k_in_z,
            color=(191 / 255, 44 / 255, 0),
            alpha=1,
            linewidth=5,
            arrow_length_ratio=0.2,
            zorder=10,
        )

        # Plot scattered beam (k_out) - in x-y plane, rotated 90° from original
        k_out_length = 1.3
        # Rotated 90° to match incident beam coming from -y
        k_out_x = k_out_length * np.sin(np.radians(tth - theta))
        k_out_y = -k_out_length * np.cos(np.radians(tth - theta))
        k_out_z = 0

        # Draw colored arrow on top
        self.axes.quiver(
            0,
            0 + offset,
            0,
            k_out_x,
            k_out_y,
            k_out_z,
            color=(2 / 255, 78 / 255, 191 / 255),
            linewidth=5,
            arrow_length_ratio=0.2,
            zorder=10,
        )

        # Set axis limits
        self.axes.set_xlim(-1, 1)
        self.axes.set_ylim(-1, 1)
        self.axes.set_zlim(-1, 1)

        self.axes.set_axis_off()
        self.fig.tight_layout()
        # Update the canvas
        self.draw()



def _rotate_vertices(vertices, phi, chi):
    """Rotate the vertices of the sample with respect to the scattering plane by the given phi and chi angles."""
    rotation_matrix = get_rotation(phi, chi)
    vertices = np.array(vertices)
    for i, vertex in enumerate(vertices):
        vertices[i] = rotation_matrix @ vertex
    return vertices
