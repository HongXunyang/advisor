# Extending the App

The codebase uses a domain–controller–view split and groups code by feature. Here’s the short version for adding functionality.

## Anatomy of a feature
- **Domain**: pure Python calculators (no PyQt) in `advisor/features/<feature>/domain/`.
- **Controller**: wires the calculator to the tab view, sets `title/description/icon`, and forwards parameters in `set_parameters`.
- **View**: PyQt tab(s) in `advisor/features/<feature>/ui/`, typically subclassing `TabInterface`.

## Steps to add a feature
1) Create domain code in `features/<feature>/domain/` and export it via `__init__.py`.
2) Add a controller subclassing `FeatureController` in `features/<feature>/controllers/`.
3) Build a tab view in `features/<feature>/ui/` (and `ui/components/` if you need reusable widgets).
4) Register the controller in `AppController.features` so the tab appears.
5) Drop an icon (optional) in `resources/icons/` and set `icon` on the controller.

See `docs/feature_development.md` for more detail and testing notes.

<!-- TODO: Add a simple UML sketch or diagram of the domain–controller–view flow. -->

## Reusing shared pieces
- Core geometry: `advisor/domain/geometry.py`
- Lattice/Sample/Lab: `advisor/domain/core/`
- Visualizers: `advisor/ui/visualizers/`
- Tips/config: `advisor/ui/tips.py` and `resources/config/tips.json`

## Styling and UX
- QSS: `resources/qss/styles.qss`
- Icons: `resources/icons/`
- Add tooltips by extending `resources/config/tips.json`.

