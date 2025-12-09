# Adding a New Feature (Domain–Controller–View)

This codebase is structured by feature, with a clear split between backend calculations (domain), coordination logic (controllers), and PyQt5 UI (views). To add a new feature:

1) **Create the domain logic**
   - Add a package under `advisor/features/<feature_name>/domain/`.
   - Implement pure-Python calculators that avoid PyQt imports. Reuse the shared core models in `advisor/domain/core` and helpers in `advisor/domain/geometry.py` and `advisor/domain/unit_converter.py`.
   - Export the main calculator via `__init__.py` inside your domain folder.

2) **Add a feature controller**
   - Create `advisor/features/<feature_name>/controllers/<feature_name>_controller.py` that subclasses `FeatureController`.
   - The controller should own the domain calculator, build the tab view, and expose `title`, `description`, and optional `icon` (filename in `resources/icons/`).
   - Wire global parameters by implementing `set_parameters(self, params: dict)` and calling `self.view.set_parameters(...)` as needed.

3) **Build the view/tab**
   - Add your tab widget under `advisor/features/<feature_name>/ui/` (e.g., `<feature_name>_tab.py`) and subclass `TabInterface`.
   - Keep the UI PyQt-only: delegate all calculations to the domain calculator and all orchestration to the controller.
   - Place reusable widgets in `ui/components/` and visual elements in `advisor/ui/visualizers/` if they are shareable.

4) **Register the feature (no registry file)**
   - Open `advisor/controllers/app_controller.py` and append your controller instance to `self.features`.
   - Provide an icon in `advisor/resources/icons/` if you set `icon` on the controller.

5) **Resources and tips**
   - QSS lives in `advisor/resources/qss/styles.qss`.
   - Tooltips are loaded from `advisor/resources/config/tips.json`; extend this file to add new tip keys.
   - Sample data can be stored under `advisor/resources/data/`.

6) **Testing**
   - Place feature-specific tests under `tests/<feature_name>/` and import from the `advisor` package (not from `lagacy/`).
   - Keep domain logic deterministic and UI-free to enable fast unit testing.

7) **Run the app**
   - Use `python -m advisor` or `python main.py`. The startup flow shows the init screen, collects global parameters, and then loads feature tabs without any registry config.
