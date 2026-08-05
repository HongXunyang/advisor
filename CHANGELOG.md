# Changelog

All notable changes to Advisor-Scattering are documented here. The format is
loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions before 1.0.0 iterated rapidly during initial development; see the
git tag history for that period rather than a detailed per-tag log here.

## [1.0.1] - Unreleased

### Fixed
- Fixed a circular import (`advisor.controllers` ↔ `advisor.features.*.controllers`)
  that raised `ImportError` when a feature controller module was imported
  before `AppController` — only "worked" previously by accident of the app's
  specific startup order. `AppController` is no longer re-exported from
  `advisor/controllers/__init__.py`; import it directly from
  `advisor.controllers.app_controller`.
- Fixed `from advisor import *` raising `AttributeError` (`__all__` claimed a
  `main` export that was never actually imported into `advisor/__init__.py`).
- Fixed a broken image reference in the Sphinx docs (`using_app.rst` pointed
  at a nonexistent `init.jpg` instead of `init.gif`).
- Removed dead `fsolve`/`angle_to_matrix` imports left over from the switch
  to closed-form analytic angle solving.

### Added
- `advisor.__version__`, sourced from installed package metadata.
- CI workflow (`.github/workflows/tests.yml`) running `pytest` on push/PR
  across Python 3.9/3.11/3.12.
- Test coverage for `advisor/domain/geometry.py`, `Lattice`/`Sample`/`Lab`,
  `UnitConverter`, the `structure_factor` feature's domain layer, and both
  feature controllers plus `AppController`.
- `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.

### Changed
- Corrected stale architecture documentation (`CLAUDE.md`,
  `.cursor/rules/code-logic.mdc`): HKL→angle solving is closed-form/analytic,
  not `scipy.optimize.fsolve`-based; the sample-rotation convention is
  phi↔X-axis / chi↔Y-axis (previously documented backwards).
- Cleaned up committed Sphinx build output (`docs/build/`) and a stale,
  unreferenced duplicate doc tree (`docs/non_sphinx_docs/`) — both removed
  from version control.

## [1.0.0] - 2026-07-28

First stable release. Core functionality:

- Bidirectional angle ↔ HKL conversion (`Angles → HKL`, `HKL → Angles`,
  fixed-2θ trajectory, HKL scan planning) via closed-form analytic solving.
- Interactive 3D visualization of scattering geometry, unit cells, and
  scattering trajectories.
- Structure factor calculation and visualization from CIF files
  (HKL-plane and arbitrary custom-plane exploration), built on
  [Dans_Diffraction](https://github.com/DanPorter/Dans_Diffraction).
- Crystal orientation fitting from diffraction test data.
- Published on PyPI as `advisor-scattering`.
