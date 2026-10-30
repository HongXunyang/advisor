# Advisor-Scattering — Advanced Visual Scattering Toolkit for Reciprocal-space

![Python](https://img.shields.io/badge/python-3.9-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)
![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)
[![Tests](https://github.com/HongXunyang/advisor/actions/workflows/tests.yml/badge.svg)](https://github.com/HongXunyang/advisor/actions/workflows/tests.yml)
[![Docs](https://readthedocs.org/projects/advisor-scattering/badge/?version=latest)](https://advisor-scattering.readthedocs.io/en/latest/)

Advisor-Scattering is a PyQt5 desktop app for X-ray scattering/diffraction experiments. It helps you convert scattering angles ↔ momentum transfer (HKL), explore scattering geometry, and visualize structure factors—all with interactive plots. Full docs on *[Read the Docs](https://advisor-scattering.readthedocs.io/en/latest/)*.

![Demo video](https://raw.githubusercontent.com/HongXunyang/advisor/main/docs/source/_static/showcase.gif)
or use the link below to view the demo video.
▶  [Demo video (MP4)](https://raw.githubusercontent.com/HongXunyang/advisor/main/docs/source/_static/showcase.mp4)


## Features
- Convert scattering angles to momentum transfer (HKL) and vice versa.
- Visualize scattering geometry and unit cells
- Compute and visualize structure factors in reciprocal space.
- CIF file drop-in support
- Local structure library ("My structures"): remembers CIFs you've loaded on this device, with Recent/Starred/search, and a bundled offline example to try immediately
- Import crystal orientation from diffraction test data


## Install
- Python 3.9 only, with PyQt5, numpy, scipy, matplotlib, Dans_Diffraction (see `requirements.txt`).

It is recommened to install from PyPI:
```bash
pip install advisor-scattering
```

## Run
```bash
advisor
# or
advisor-scattering
# or
python -m advisor
```

*Note: the install command is `pip install advisor-scattering`, and the import is `import advisor`*.

------

## Minimal workflow (60 seconds)
1) Launch the app.  
2) Enter lattice constants/angles and beam energy, or drop a CIF file.  
3) Click **Initialize**.  
4) Use the feature tabs (Scattering Geometry / Structure Factor) to calculate and visualize.

![Init flow](https://raw.githubusercontent.com/HongXunyang/advisor/main/docs/source/_static/init.gif)

----

## Using the app

### 1. Initialization window
- Enter lattice constants (a, b, c) and angles (alpha, beta, gamma); beam energy auto-updates wavelength/|k|.
- Optional: drop a CIF to autofill lattice parameters and preview the unit cell.
- Adjust Euler angles (roll, pitch, yaw) to orient the lattice/sample relative to the goniometer.
- **New:** Use **Import from Diffraction Test** to automatically determine Euler angles from known diffraction measurements.
- Click **Initialize** to load the main interface and pass parameters to all tabs.

### 2. Scattering Geometry tab
- Angles → HKL: enter 2θ/θ/χ/φ, compute HKL.
- HKL → Angles: enter HKL, compute feasible angles.
- HK to Angles (fixed 2θ) and HKL scan (fixed 2θ) subtabs for trajectory planning.

![Scattering geometry demo](https://raw.githubusercontent.com/HongXunyang/advisor/main/docs/source/_static/scattering_geometry_tab_demo.gif)

### 3. Structure Factor tab
- Requires a CIF (from init) and an energy in the tab.
- HKL plane: explore a 3D HKL cube with linked HK/HL/KL slices.
- Customized plane: choose U/V vectors and a center to sample an arbitrary plane in reciprocal space.

![Structure factor demo](https://raw.githubusercontent.com/HongXunyang/advisor/main/docs/source/_static/structure_factor_tab_demo.gif)

### 4. My structures and Try an example
- Click **Structures ▾** next to the CIF area (or **File → My structures…**) to reopen a previously loaded CIF, without finding the original file again.
- No CIF on hand? **Try an example** loads a small bundled structure, fully offline.
- Accepted CIFs are remembered automatically on this device (toggle in the picker); removing a saved entry never touches your original file on disk.

### 5. Changing or resetting the structure
Use the toolbar button or **File → Change Structure…** to pick a different CIF or start over, returning to the init window.

------

## Project structure (at a glance)
```
advisor/          application package
  app.py          bootstrap
  controllers/    app/feature coordinators
  domain/         math and geometry helpers (no PyQt)
  features/       per-feature domain/controller/ui code
  ui/             shared UI pieces (init window, main window, base tab, visualizers)
  resources/      QSS, icons, config JSON, sample data
docs/             Sphinx sources and assets
```

## Documentation
- Full Sphinx docs live in `docs/` and on *[Read the Docs](https://advisor-scattering.readthedocs.io/en/latest/)*.
- Appendix covers scattering angle definitions and HKL conventions.

## Contributing
Bug reports, feature requests, and pull requests are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, testing, and architecture
pointers. This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
