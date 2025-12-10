# Ad-VISOR — Advanced Visual Scattering Toolkit for Reciprocal-space

Ad-VISOR is a PyQt5 desktop app for X-ray scattering/diffraction experiments. It helps you convert scattering angles ↔ momentum transfer (HKL), explore scattering geometry, and visualize structure factors—all with interactive plots. Full docs on *[Read the Docs](https://ad-visor.readthedocs.io/en/latest/)*.

![Demo video](https://raw.githubusercontent.com/HongXunyang/advisor/main/docs/source/_static/showcase.gif)
or use the link below to view the demo video.
▶  [Demo video (MP4)](https://raw.githubusercontent.com/HongXunyang/advisor/main/docs/source/_static/showcase.mp4)


## Features
- Convert scattering angles to momentum transfer (HKL) and vice versa.
- Visualize scattering geometry and unit cells
- Compute and visualize structure factors in reciprocal space.
- CIF file drop-in support


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
- Adjust Euler angles (roll, pitch, yaw) to orient the sample relative to the scattering plane;
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

### 4. Resetting
Use the toolbar button or **File → Reset Parameters** to return to the init window, clear the CIF lock, and re-enter parameters.

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
- Full Sphinx docs live in `docs/` and on *[Read the Docs](https://ad-visor.readthedocs.io/en/latest/)*.
- Appendix covers scattering angle definitions and HKL conventions.
