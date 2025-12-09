# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Ad-VISOR'
html_title = 'Ad-VISOR (Advanced Visual Scattering Toolkit for Reciprocal-space)'
copyright = '2025, Xunyang_Hong'
author = 'Xunyang_Hong'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# Prefer the Read the Docs theme if available; fall back to Alabaster.
try:  # pragma: no cover - config-time check
    import sphinx_rtd_theme  # type: ignore

    html_theme = 'sphinx_rtd_theme'
    # html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
except Exception:
    html_theme = 'alabaster'

html_static_path = ['_static']

# Logo
html_logo = '../logo/ad_visor_logo.png'
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 2,
    "logo_only": False,
    "style_nav_header_background": "#0f172a",
}
