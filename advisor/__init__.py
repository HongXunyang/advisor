"""Advisor-Scattering: Advanced Visual Scattering Toolkit for Reciprocal-space."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("advisor-scattering")
except PackageNotFoundError:
    # Package is not installed (e.g. running from a source checkout without
    # `pip install -e .`).
    __version__ = "0.0.0"

# Note: `main` deliberately isn't imported/re-exported here (use
# `from advisor.app import main`, as the `advisor`/`advisor-scattering`
# console scripts and `python -m advisor` already do) — importing `.app`
# eagerly at package-import time would pull in PyQt5 and the full
# controller/UI stack as a side effect of any `import advisor.<submodule>`,
# including the domain-only imports used throughout the test suite.
__all__ = ["__version__"]
