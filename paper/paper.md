---
title: 'ADVISOR: ADvanced VIsualization of Scattering ORientation'
tags:
  - Python
  - X-ray scattering
  - X-ray diffraction
  - condensed matter physics
  - physics
  - experimental physics
  - Structure factor
  - Data visualization
authors:
  - name: Xunyang Hong
    orcid: 0000-0001-6219-2851 
    affiliation: "1, 2"
  - name: Sze Tung Li
    affiliation: 2
  - name: Leonardo Martinelli
    affiliation: 1
  - name: Qisi Wang
    affiliation: "2, 3"
  - name: Johan Chang
    affiliation: 1

affiliations:
  - name: Physik Institut, Universität Zürich, Winterthurerstrasse 190, CH-8057 Zürich, Switzerland
    index: 1
  - name: Department of Physics, The Chinese University of Hong Kong, Shatin, Hong Kong, China
    index: 2
  - name: State Key Laboratory of Quantum Information Technologies and Materials, The Chinese University of Hong Kong, Shatin, Hong Kong, China
    index: 3
date: 15 January 2026
bibliography: paper.bib
---

# Summary

ADVISOR is a python-based graphical user interface for planning and visualizing X-ray scattering experiments. The program is especially useful for experiments where scattering angles are constrained by X-ray kinematic conditions or by sample environments such as uniaxial pressure cells or magnets with specific scattering windows. ADVISOR can convert instrument angles to momentum-space coordinates, evaluate accessible regions of reciprocal space, and inspect Bragg reflections.
With interactive visualization, ADVISOR helps users to evaluate experimental scattering geometries before or during scattering experiments.

# Statement of need

Scattering experiments are essential tools for probing the structure, phase transitions, and dynamics of matter. Some experiments, such as powder diffraction for structural analysis, are well-standardized — similar measurement conditions are applied routinely across different setups and facilities.
Many experiments, however, are highly customized, targeting specific regions of reciprocal space. This momentum specificity is typically enforced by a combination of scientific requirements and experimental constraints. Resonant experiments, for instance, are limited by the choice of absorption edge, which in turn restricts access to reciprocal space [@ament2011]. Similarly, experiments conducted in extreme environments are often constrained by the scattering "windows" of pressure cells [@choi_unveiling_2022] or cryomagnets [@chang_direct_2012; @holmes_17_2012; @blackburn_exploring_2010].
Prior to undertaking such constrained experiments, it is valuable to evaluate the accessible regions of reciprocal space and compare them against known or anticipated structure factors. These considerations are critical when designing demanding experiments in which scattering geometries are restricted. ADVISOR is created to assist with precisely this kind of experimental planning for x-ray scattering experiments.

Synchrotron X-ray techniques are widely used in condensed matter physics and other areas of materials research. However, due to the limited synchrotron beamtimes, experimentalists oftentimes need to plan carefully and execute efficiently during their allocated time slots. During a typical beamtime, researchers need to first determine sample’s orientation, decide which point in the momentum space to probe, how to reorient the sample to get there, and whether it is accessible under certain instrumental and scattering geometrical constraints. These decisions are vital and will easily affect scientific output.

However, in practice these tasks are time-consuming. Researchers control instrumental angles, while what physically meaningful is the momentum in k-space. The conversion between real-space instrumental configuration and k-space momentum is tedious, especially for non-orthogonal crystal structure.
Constraints from scattering geometry further complicate the calculation. For example, soft X-ray scattering works only in backscattering geometry which should be further considered.
This type of calculation matters throughout the entire experiment, from sample orientation determination, geometry-momentum conversion, Bragg peak examining and visualizing, to accessible region assessment.

ADVISOR was developed to address these workflow bottlenecks on a single platform. The target users are synchrotron X-ray experimentalists who need practical decision support before and during beamtime.

# State of the field

Numerous crystallographic simulation packages [@olex2; @shelx; @vesta; @recipro] exist. Yet, none of these are designed to assist the planning or decision making of challenging scattering experiments. Although well-established in theory [@busing1967; @lumsden2005], the conversion between real space configuration to momentum transfer is a computational task. Especially for non-orthogonal crystal systems, the task is not a pen and paper exercise. ADVISOR provides a user interface for the conversion numerically, with all types of crystal structure supported. ADVISOR supports upload of a crystal CIF files and allows to
build a UB-matrix to describe specific crystal orientations.

# Software design

Advisor-Scattering is built on PyQt5 [@pyqt] for the graphical interface and
Matplotlib [@matplotlib] for visualization. NumPy [@numpy] and SciPy [@scipy]
handle the crystallographic and rotation-matrix calculations in the domain
layer. The Dans_Diffraction library [@dans_diffraction] handles the structure
factor and atomic form factor calculations. The architecture separates
domain logic from user interface components, facilitating maintenance and
extension. \autoref{fig:overview} illustrates the application's main
functionalities. The documentation is available at readthedocs [@advisor_doc].

![**Overview of the main functionalities**. \label{fig:overview}](functions.png)

The ADVISOR application is tailored for synchrotron X-ray experiment workflow: It starts with an initial panel where users can put in crystal information, and UB matrix for determining crystal orientation. After initialized, the main panel consists of two modules. The first module *Scattering Geometry* enables the conversion between instrumental
angles and momentum transfer in reciprocal space. The second module *Structure Factor*, with its
core based on the Dans_Diffraction library [@dans_diffraction], enables the calculation of structure factors
and visualization.

## Scattering Geometry module

![**Scattering Geometry module | angles to HKL sub-tab**. The left sidebar selects modules, while the top row provides multiple sub-tabs for different calculation modes (e.g., angles to HKL and HKL to angles). Users enter instrument angles $(2\theta,\theta,\phi,\chi)$ to compute momentum transfer $(H,K,L)$ (bottom-left), with interactive 3D views showing the corresponding experimental geometry (top-right) and the crystal structure (bottom-right). The right panel summarizes lattice parameters and X-ray settings (energy/wavelength) used in the calculation. \label{fig:geometry}](scattering_geometry.jpg)

This module implements the core angle-HKL transformation
mathematics.
Four calculation modes are available:

- **Angles → HKL**: Given instrumental angles (2θ, θ, χ, φ), compute the
  accessed momentum transfer in reciprocal lattice units.
- **HKL → Angles**: Given target momentum transfer, compute all feasible angular
  solutions. Solutions are color-coded by feasibility (positive θ with
  θ < 2θ) for back scattering experiment.
- **Fixed-2θ trajectory**: For a fixed scattering angle, compute the angular
  path required to scan along specified HK directions.

All calculations are accompanied by interactive 3D visualizations showing
the in-coming beam, out-going beam, and crystal
orientation (\autoref{fig:geometry}).

## Structure Factor module

![**Structure Factor module.** The top controls choose the reciprocal-space slice to explore (predefined HK/HL/KL planes or a user-defined plane). The 3D view (left) visualizes calculated structure-factor magnitudes in reciprocal space, where marker size/color indicates the structure factor $|F(\mathbf{Q})|$. The 2D view (right) shows the corresponding planar cut (here the HK plane at fixed $L=0$), facilitating identification of strong reflections. User inputs such as X-ray energy and the plane index are set in the configuration panel below. \label{fig:structure}](structure_factor.jpg)

When a CIF file is provided, the Structure Factor module enables exploration of
diffraction intensities (approximated by structure factors) across reciprocal space. The module leverages the
Dans_Diffraction library [@dans_diffraction] for atomic form factor and
structure factor calculations.

Two visualization modes are provided:

- **HKL planes**: A 3D reciprocal space cube with translucent slicing planes
  (HK, HL, KL) that can be swept through integer L, K, or H values
  respectively. Synchronized 2D map shows structure factor magnitudes
  |F(hkl)| on each plane.
- **Custom planes**: Users define arbitrary crystallographic planes by
  specifying two in-plane vectors (U, V) and a center point in HKL
  coordinates, enabling visualization of structure factors along any directions.

## Technical implementation

ADVISOR follows a domain-controller-view (or Model-view-controller) architecture: This separation allows the calculation routines to be imported and used
independently of the GUI for scripting and automation. ADVISOR also follows a feature-oriented code structure: this allows for adding more modular features and functionalities in the future.

# Research impact statement

ADVISOR has already been tested and used in *Laboratory for Quantum Matter Research* at University of Zurich and *Quantum Matter Laboratory* at the Chinese University of Hong Kong. It is documented at readthedocs [@advisor_doc], released on PyPI, which demonstrate readiness. Together, these provide evidence of current or near-term research impact.

# Conclusions and future work

Advisor-Scattering provides an accessible, visual approach to X-ray
scattering experiment planning. By combining real-time angle-momentum transfer conversion
with interactive 3D visualization and structure factor exploration, the
software reduces the barrier to understanding reciprocal space geometry and
accelerates experimental preparation and decision making.

Planned developments include:

- Customizable rotation conventions for different beamline geometries
- Export of calculated trajectories to beamline control formats
- Extension to neutron scattering.

# AI usage disclosure

- **Tool use**: Codex 5.2; Claude Sonnet 3.5, 4, 4.5; GPT 5; They were used in the code development and the documentation.
- **The nature and scope of assistance**: Claude Sonnet and GPT 5 assisted in writing code and
  debugging. Codex 5.2 were used in code restructuring. Claude Opus 4.5 and ChatGPT 5.2 assisted in drafting the
  documentation and the paper.
- **Confirmation of review**: The author has reviewed, edited, and validated all AI-assisted outputs and
  made the core design decisions.

# Acknowledgements

The authors acknowledge helpful discussions with colleagues at University of Zurich and the Chinese University of Hong Kong
regarding diffractometer conventions and user interface design.

# References
