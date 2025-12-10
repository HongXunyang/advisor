# Ad-VISOR — Advanced Visual Scattering Toolkit for Reciprocal-space

Ad-VISOR is a PyQt5 desktop app for scattering/diffraction prep. It helps you convert scattering angles ↔ momentum transfer (HKL), explore scattering geometry, and visualize structure factors—all with interactive plots. Full docs on *[Read the Docs](https://ad-visor.readthedocs.io/en/latest/)*.

<video controls width="640" style="margin: 1em 0; border-radius: 8px; box-shadow: 0 2px 12px #0002;">
  <source src="docs/source/_static/showcase.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

## Features
- Convert scattering angles to HKL and HKL to angles, including fixed-2θ scans.
- Visualize scattering geometry and unit cells as you type.
- Compute and visualize structure factors on HKL cubes or custom planes.
- CIF drop-in support in the init window; parameters flow into every tab.
- Reset to the init window at any time to reload parameters.

## Install
- Python 3.8+ with PyQt5, numpy, scipy, matplotlib, Dans_Diffraction (see `requirements.txt`).

From PyPI:
```bash
pip install ad-visor
```

From source:
```bash
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install .
```

## Run
```bash
ad-visor
# or
python -m advisor
# or
python main.py
```

## Minimal workflow (60 seconds)
1) Launch the app.  
2) Enter lattice constants/angles and beam energy, or drop a CIF file.  
3) Click **Initialize**.  
4) Use the feature tabs (Scattering Geometry / Structure Factor) to calculate and visualize.

![Init flow](docs/source/_static/init.gif)

## Using the app
### Init window
- Enter lattice constants (a, b, c) and angles (alpha, beta, gamma); beam energy auto-updates wavelength/|k|.
- Optional: drop a CIF to autofill lattice parameters and preview the unit cell.
- Adjust Euler angles (roll, pitch, yaw) to orient the sample; click **Initialize** to load the main interface.

### Scattering Geometry tab
- Angles → HKL: enter 2θ/θ/χ/φ, compute HKL.
- HKL → Angles: enter HKL, compute feasible angles.
- HK to Angles (fixed 2θ) and HKL scan (fixed 2θ) subtabs for trajectory planning.

![Scattering geometry demo](docs/source/_static/scattering_geometry_tab_demo.gif)

### Structure Factor tab
- Requires a CIF (from init) and an energy in the tab.
- HKL plane: explore a 3D HKL cube with linked HK/HL/KL slices.
- Customized plane: choose U/V vectors and a center to sample an arbitrary plane in reciprocal space.

![Structure factor demo](docs/source/_static/structure_factor_tab_demo.gif)

### Resetting
Use the toolbar button or **File → Reset Parameters** to return to the init window, clear the CIF lock, and re-enter parameters.

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

## Extending the app
- Pattern: domain (pure math) + controller (wiring) + view (PyQt tab).
- Add feature code under `advisor/features/<feature>/domain|controllers|ui/`.
- Register the controller in `advisor/controllers/app_controller.py`.
- Reuse visuals in `advisor/ui/visualizers/`, styles in `advisor/resources/qss/styles.qss`, and tooltips in `advisor/resources/config/tips.json`.
- See `docs/feature_development.md` for the step-by-step guide.

## Documentation
- Full Sphinx docs live in `docs/` and on *[Read the Docs](https://ad-visor.readthedocs.io/en/latest/)*.
- Appendix covers scattering angle definitions and HKL conventions.
