# Contributing to Advisor-Scattering

Thanks for your interest in contributing! This project follows the
[Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

## Getting started

```bash
git clone https://github.com/HongXunyang/advisor.git
cd advisor
pip install -r requirements-dev.txt
pip install -e .
```

Run the app:

```bash
python -m advisor
```

## Running tests

```bash
pytest                          # full suite
pytest tests/domain/test_orientation.py                       # single file
pytest tests/features/scattering_geometry/domain/test_core.py::test_name  # single test
```

The test suite includes PyQt5 widget tests that run headlessly; on Linux/CI
this requires `QT_QPA_PLATFORM=offscreen` (already set by `tests/conftest.py`
and the `tests` GitHub Actions workflow). Tests run automatically on every
push and pull request via `.github/workflows/tests.yml`.

## Project architecture

Before making non-trivial changes, please read:

- `CLAUDE.md` — high-level project overview, commands, and architecture summary.
- `.cursor/rules/folder-structure.mdc` — folder layout conventions.
- `.cursor/rules/code-logic.mdc` — data flow and calculation algorithm details.

The codebase follows a strict **Domain → Controller → UI** layering, both
globally and per-feature (`advisor/features/<name>/{domain,controller(s),ui}`).
Domain-layer code must not import PyQt5 or import across features — see
`docs/feature_development.md` for the step-by-step recipe for adding a new
feature.

If your change modifies folder structure, calculation algorithms, or
backend/frontend data contracts, please update the relevant `.cursor/rules/*.mdc`
file (and `CLAUDE.md` if it documents the same convention) in the same pull
request, so these stay accurate for the next contributor.

## Submitting changes

1. Fork the repository and create a branch for your change.
2. Add or update tests for any behavior change — domain-layer changes should
   have corresponding `pytest` coverage (see `tests/conftest.py` for shared
   lattice/calculator fixtures).
3. Make sure `pytest` passes locally before opening a pull request.
4. Open a pull request describing the change and its motivation.

## Reporting bugs / requesting features

Please open a [GitHub issue](https://github.com/HongXunyang/advisor/issues)
with a clear description and, for bugs, steps to reproduce.
