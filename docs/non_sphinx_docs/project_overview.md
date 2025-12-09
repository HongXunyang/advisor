# Project Overview (Plain English)

Ad-VISOR (Advanced Visual Scattering Toolkit for Reciprocal-space) helps with X-ray scattering/diffraction prep by keeping the math separated from the PyQt UI. Here’s how it is organized and how it works at runtime.

## How the app starts
- You run `python main.py` (or `python -m advisor`).
- A small bootstrap loads the stylesheet and shows the **Init window**. You enter lattice constants/angles, energy, and optionally drop a CIF file.
- When you click **Initialize**, those parameters are shared with every feature tab and the main tab view is shown.

## Folder layout (top-level)
- `advisor/` – the actual code package.
  - `app.py` – bootstrap logic.
  - `controllers/` – coordinators that wire views to backend logic.
  - `domain/` – pure math/geometry helpers and core classes (Lattice, Sample, Lab).
  - `features/` – each feature lives here with its own domain/controller/ui folders.
  - `ui/` – shared UI pieces: main window, init window, base tab class, tips loader, visualizers.
  - `resources/` – QSS, icons, config JSON, sample data.
- `docs/` – documentation (this file, plus the feature development guide).
- `main.py` – convenience entrypoint in the repo root.

## Key ideas (not too technical)
- **Keep the UI dumb.** Buttons, forms, and plots live in `ui/` or `features/*/ui/`. They don’t do heavy calculations themselves.
- **Put the math in the domain.** Calculators and geometry helpers live in `domain/` or `features/*/domain/`. No PyQt imports there.
- **Controllers glue things together.** Each feature controller owns its calculator and its tab, passes parameters down, and reacts to init/reset events from the app.
- **No registry files.** Tabs are added in one place: `AppController` builds a list of feature controllers and inserts their tabs. Adding a new feature = add controller + tab + calculator, then list it in `AppController`.
- **Shared visuals.** Common matplotlib canvases (scattering geometry, unit cell, structure factor plots, HKL scan) sit in `ui/visualizers/` so features reuse them.

## Runtime flow
1) App starts, loads QSS and config from `resources/config/app_config.json`.
2) Init window collects parameters (and CIF if provided) and emits them.
3) `AppController` stores the parameters and calls `set_parameters` on each feature controller/tab.
4) Tabs are shown; each can open/save files if they implement those hooks.
5) Reset brings you back to the init window and clears the CIF lock.

## Where to look for what
- **Change the look**: `resources/qss/styles.qss`.
- **Icons**: `resources/icons/`.
- **Tips text**: `resources/config/tips.json`.
- **Core math / coordinate frames**: `domain/core/` and `domain/geometry.py`.
- **Scattering geometry (Brillouin/angles ↔ HKL) feature**: `features/scattering_geometry/` (domain/controller/ui/components).
- **Structure factor feature**: `features/structure_factor/` (domain/controller/ui/components).
- **Base UI plumbing**: `ui/main_window.py`, `ui/init_window.py`, `ui/tab_interface.py`.

## Adding features
See `docs/feature_development.md` for the step-by-step. In short: create domain code, create a controller, build a tab view, and list the controller in `AppController`.
