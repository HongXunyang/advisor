---
title: 'Advisor-Scattering: A Visual Toolkit for X-ray Scattering Geometry and Structure Factor Exploration'
tags:
  - Python
  - X-ray scattering
  - X-ray diffraction
  - Reciprocal space
  - Structure factor
  - Data visualization
authors:
  - name: Xunyang Hong
    orcid: 0000-0001-6219-2851 
    affiliation: 1, 2
  - name: Sze Tung Li
    index: 2
  - name: Leonardo Martinelli
    index: 1
  - name: Qisi Wang
    index: 2
  - name: Johan Chang
    index: 1

affiliations:
  - name: Physik Institut, Universität Zürich, Winterthurerstrasse 190, CH-8057 Zürich, Switzerland
    index: 1
  - name: Department of Physics, The Chinese University of Hong Kong, Shatin, Hong Kong, China
    index: 2
date: 15 January 2026
bibliography: paper.bib
---



# Summary

X-ray scattering and diffraction experiments are fundamental techniques for 
probing the atomic structure of crystalline materials. These experiments 
require careful planning of scattering geometry and understanding of the 
relationship between instrumental angles and momentum transfer in reciprocal 
space. Advisor-Scattering is a Python-based desktop application that provides 
interactive visualization and calculation tools for X-ray scattering 
experiment preparation. The software enables researchers to convert between 
scattering angles and Miller indices (HKL), visualize scattering geometry in 
three dimensions, and explore structure factors across reciprocal space 
planes—all through an intuitive graphical interface.



# Statement of need

Planning X-ray scattering experiments requires navigating complex 
relationships between instrumental coordinates (diffractometer angles) and 
reciprocal space coordinates (HKL indices). Experimentalists must determine 
which angular configurations will access specific Bragg reflections, account 
for sample orientation, and assess which reflections are kinematically 
accessible at a given photon energy. These calculations, while 
well-established in theory [@busing1967; @you1999], can be tedious and 
error-prone when performed manually, particularly for non-orthogonal crystal 
systems.

Furthermore, understanding the intensity distribution of structure factors 
across reciprocal space is essential for identifying strong reflections and 
planning efficient measurement strategies. While diffractometer control 
software and crystallographic packages exist, many are either proprietary, 
lack interactive visualization capabilities, or require significant expertise 
to operate [@spec; @sardana; @bluesky].

Advisor-Scattering addresses these needs by providing an open-source, 
cross-platform tool that combines:

1. **Bidirectional angle-HKL conversion** with real-time feasibility checking
2. **Interactive 3D visualization** of scattering geometry and crystal structures
3. **Structure factor exploration** across arbitrary planes in reciprocal space
4. **CIF file integration** for automatic lattice parameter extraction

The software is designed for beamline scientists, graduate students, and 
researchers preparing synchrotron or laboratory X-ray scattering experiments, 
offering immediate visual feedback that accelerates experiment planning and 
deepens understanding of reciprocal space geometry.



# Software description

Advisor-Scattering is built on PyQt5 [@pyqt] for the graphical interface and 
Matplotlib [@matplotlib] for visualization. The architecture separates 
domain logic from user interface components, facilitating maintenance and 
extension. \autoref{fig:overview} illustrates the application's main 
interface. The documentation is available at readthedocs [@advisor_doc].

![Overview of the Advisor-Scattering application showing the initialization 
window (top) and the Scattering Geometry tab with interactive 3D visualization 
(bottom).
\label{fig:overview}](../docs/source/_static/showcase.gif){ width=95% }


## Initialization and CIF support

Users begin by specifying lattice parameters (a, b, c, α, β, γ), beam energy, 
and sample orientation via Euler angles (roll, pitch, yaw). Alternatively, 
dropping a Crystallographic Information File (CIF) automatically extracts 
lattice parameters and enables structure factor calculations. The 
initialization window provides a live preview of the unit cell orientation 
as Euler angles are adjusted, helping users verify the sample mounting 
configuration before proceeding.


## Scattering Geometry module

The Scattering Geometry tab implements the core angle-HKL transformation 
mathematics following standard diffractometer conventions [@busing1967]. 
Four calculation modes are available:

- **Angles → HKL**: Given instrumental angles (2θ, θ, χ, φ), compute the 
  accessed momentum transfer in reciprocal lattice units.
- **HKL → Angles**: Given target Miller indices, compute all feasible angular 
  solutions. Solutions are color-coded by feasibility (positive θ with 
  θ < 2θ).
- **Fixed-2θ trajectory**: For a fixed scattering angle, compute the angular 
  path required to scan along specified HK directions.
- **HKL scan planning**: Generate angular trajectories for systematic 
  reciprocal space surveys.

All calculations are accompanied by interactive 3D visualizations showing 
the incident and scattered wavevectors, momentum transfer vector, and crystal 
orientation (\autoref{fig:geometry}).

![The Scattering Geometry tab displaying angle-to-HKL conversion with 
synchronized 3D scattering geometry and unit cell visualizations.
\label{fig:geometry}](../docs/source/_static/scattering_geometry_tab_demo.gif){ width=95% }


## Structure Factor module

When a CIF file is provided, the Structure Factor tab enables exploration of 
diffraction intensities across reciprocal space. The module leverages the 
Dans_Diffraction library [@dans_diffraction] for atomic form factor and 
structure factor calculations, supporting energy-dependent X-ray scattering 
cross-sections including anomalous dispersion corrections.

Two visualization modes are provided:

- **HKL planes**: A 3D reciprocal space cube with translucent slicing planes 
  (HK, HL, KL) that can be swept through integer L, K, or H values 
  respectively. Synchronized 2D heatmaps show structure factor magnitudes 
  |F(hkl)| on each plane.
- **Custom planes**: Users define arbitrary crystallographic planes by 
  specifying two in-plane vectors (U, V) and a center point in HKL 
  coordinates, enabling visualization of structure factors along 
  non-principal directions (\autoref{fig:structure}).

![The Structure Factor tab showing a 3D reciprocal space cube with 
adjustable slicing planes and corresponding 2D structure factor maps.
\label{fig:structure}](../docs/source/_static/structure_factor_tab_demo.gif){ width=95% }


## Technical implementation

The software follows a domain-controller-view architecture:

- **Domain layer**: Pure Python modules implementing crystallographic 
  calculations without GUI dependencies. This includes real/reciprocal 
  lattice vector computation, Euler angle rotations, diffractometer angle 
  matrices, and structure factor evaluation.
- **Controller layer**: Coordinates data flow between the domain and UI, 
  manages application state, and handles parameter propagation across 
  feature tabs.
- **View layer**: PyQt5 widgets and Matplotlib canvases providing interactive 
  visualizations and input forms.

This separation allows the calculation routines to be imported and used 
independently of the GUI for scripting and automation.



# Mathematics

The transformation between laboratory angles and reciprocal space coordinates 
follows the formalism of Busing and Levy [@busing1967]. For a four-circle 
diffractometer with angles 2θ (detector), θ (sample rotation), χ (tilt), 
and φ (azimuth), the total rotation matrix is:

$$R_{\text{total}} = R_{\theta} R_{\chi} R_{\phi}$$

The momentum transfer vector is:

$$\mathbf{Q} = \mathbf{k}_f - \mathbf{k}_i = \frac{2\pi}{\lambda}\left(\hat{k}_f - \hat{k}_i\right)$$

where $|\mathbf{Q}| = \frac{4\pi}{\lambda}\sin\theta$. The HKL indices are 
obtained by projecting onto the reciprocal lattice basis:

$$H = \frac{\mathbf{Q} \cdot \mathbf{a}}{2\pi}, \quad 
K = \frac{\mathbf{Q} \cdot \mathbf{b}}{2\pi}, \quad 
L = \frac{\mathbf{Q} \cdot \mathbf{c}}{2\pi}$$

where $\mathbf{a}^*$, $\mathbf{b}^*$, $\mathbf{c}^*$ are the reciprocal 
lattice vectors computed from the real-space unit cell.



# Conclusions and future work

Advisor-Scattering provides an accessible, visual approach to X-ray 
scattering experiment planning. By combining real-time angle-HKL conversion 
with interactive 3D visualization and structure factor exploration, the 
software reduces the barrier to understanding reciprocal space geometry and 
accelerates experimental preparation.

Planned developments include:

- Support for additional diffractometer geometries (six-circle, kappa)
- Export of calculated trajectories to beamline control formats
- Integration of absorption correction calculations
- Extension to neutron scattering cross-sections

# AI usage disclosure

- **Tool use**: Codex 5.2; Claude Sonnet 3.5, 4, 4.5; GPT 5; They were used in the code and the documentation. 
- **The nature and scope of assistance**: Claude Sonnet and GPT 5 assisted in writing code and
  debugging. Codex 5.2 were used in code restructuring. Claude Opus 4.5 and ChatGPT 5.2 assisted in drafting the
  documentation and the paper. 
- **Confirmation of review**: The author has reviewed, edited, and validated all AI-assisted outputs and
  made the core design decisions.


# Acknowledgements

The author acknowledges helpful discussions with colleagues at [institution] 
regarding diffractometer conventions and user interface design.



# References




