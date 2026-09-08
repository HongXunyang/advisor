"""Adapts Dans_Diffraction's own CIF facilities into a validated
`StructureSource` or an actionable rejection.

Deliberately does not invent a new CIF grammar: parsing goes through
`Dans_Diffraction.functions_crystallography.readcif` /
`functions_general.readstfm`, the same facilities the library's own
`Crystal()` uses internally (uncertainty notation like "5.4310(2)", quoted
values, loops, and multiline text are already handled there).

A successfully-parsed dict is not proof of a valid or complete structure:
`Dans_Diffraction.Crystal()` silently falls back to a default 1 A cubic cell
and a synthetic atom when required CIF keys are missing (it warns via
`warnings.warn`, it does not raise) -- so capability is decided by checking
the *raw parsed CIF keys* via `Dans_Diffraction`'s own `cif_check`, never by
introspecting a constructed `Crystal`/`Atoms` object, which would report a
false positive.

Multi-block CIFs (more than one `data_...` block in one file) are rejected
with an actionable message rather than silently merged (which is what both
Dans_Diffraction's and the app's own former vendored `readcif` do if handed
one) or resolved via a picker UI (out of scope for this task).
"""

import os
import re
from typing import List, Optional, Tuple

import Dans_Diffraction.functions_crystallography as fc
import Dans_Diffraction.functions_general as fg
from Dans_Diffraction.classes_crystal import Atoms as _DifAtoms
from Dans_Diffraction.classes_crystal import Cell as _DifCell

from .cell_validation import validate_cell
from .types import CifCapabilityReport, CifImportResult, StructureSource

_CELL_KEYS = tuple(_DifCell()._required_cif)
_ATOM_KEYS = tuple(_DifAtoms()._required_cif)

# A CIF value that is actually numeric (float, optionally with a leading
# sign, a "(uncertainty)" suffix per readstfm(), and/or exponent notation).
# Deliberately stricter than Dans_Diffraction.functions_general.readstfm(),
# which never raises -- garbage input (including the standard CIF "unknown"/
# "inapplicable" markers '?' and '.') silently becomes 0.0 there, which is
# exactly the false-"ready" failure mode this guards against.
_NUMERIC_VALUE_RE = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)(\(\d+\))?([eE][-+]?\d+)?$")


def _is_numeric_cif_value(value) -> bool:
    return bool(_NUMERIC_VALUE_RE.match(str(value).strip()))


# Optional, informational-only descriptive metadata (source id, DOI, ambient
# temperature/pressure) for the local structure library (REQUIREMENT_2) --
# extracted from the same `cifvals` dict already parsed for formula/space
# group below, never used for capability/validity decisions. Absence of any
# of these is not a failure; they are purely for a library row/details view.
_SOURCE_ID_KEYS = (
    "_database_code_amcsd",
    "_cod_database_code",
    "_database_code_ICSD",
    "_database_code_depnum_ccdc_archive",
)
_TEMPERATURE_KEYS = ("_diffrn_ambient_temperature", "_cell_measurement_temperature")
_PRESSURE_KEYS = ("_diffrn_ambient_pressure", "_cell_measurement_pressure")


# CIF's two standard "value not given" markers -- a bare '.' (inapplicable)
# or '?' (unknown). `_atoms_are_usable()` already accounts for these on
# numeric coordinates; string-valued descriptive fields (formula, space
# group, source id, DOI) need the same treatment so a null marker is never
# displayed as if it were real provenance.
_NULL_MARKERS = {".", "?"}


def _is_null_marker(value) -> bool:
    return isinstance(value, str) and value.strip(" '\"") in _NULL_MARKERS


def _clean_optional_str(value) -> Optional[str]:
    """Strip quotes and treat CIF null markers as absent, for any optional
    string-valued descriptive field (formula, space group, source id, DOI)."""
    if isinstance(value, str):
        value = value.strip(" '\"")
    if not value or _is_null_marker(value):
        return None
    return value


def _first_present(cifvals, keys) -> Optional[str]:
    for key in keys:
        value = _clean_optional_str(cifvals.get(key))
        if value is not None:
            return value
    return None


def _first_numeric(cifvals, keys) -> Optional[float]:
    """CIF convention fixes the units for these specific keys (Kelvin for
    temperature, kPa for pressure), so no separate unit field is stored."""
    raw = _first_present(cifvals, keys)
    if raw is None:
        return None
    try:
        value, _ = fg.readstfm(raw)
    except (TypeError, ValueError):
        return None
    return value if _is_numeric_cif_value(raw) else None


def _decode(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


def _find_data_blocks(text: str) -> List[str]:
    """Scan for `data_...` block headers, CIF-aware enough to not be fooled
    by a semicolon-delimited multiline text field containing prose that
    happens to start with "data_" (a false positive the naive
    `^data_` regex this replaced was vulnerable to), while still detecting
    a genuine second block regardless of leading whitespace (a plain
    `^data_` anchor missed an indented `data_...` line entirely, letting it
    fall through to Dans_Diffraction's own block-unaware readcif() and
    silently merge into the first block -- exactly the failure mode this
    function exists to prevent).

    Mirrors how `readcif()` itself tokenizes: a text field starts/ends at a
    line whose first character is literally ';' (not merely a stripped
    match), while an ordinary line's first whitespace-separated token is
    what's checked against "data_" (so leading indentation before the token
    doesn't hide it, matching `line.split()`'s behavior in the real parser).
    """
    blocks: List[str] = []
    in_text_field = False
    for raw_line in text.splitlines():
        if in_text_field:
            if raw_line.startswith(";"):
                in_text_field = False
            continue
        if raw_line.startswith(";"):
            in_text_field = True
            continue
        stripped = raw_line.strip()
        if not stripped:
            continue
        token = stripped.split(None, 1)[0]
        if token[:5].lower() == "data_":
            blocks.append(token[5:] or "(unnamed)")
    return blocks


def _atoms_are_usable(cifvals) -> Tuple[bool, str]:
    """Stricter than `fc.cif_check()` alone: that only checks required keys
    are present and that the literal string '?' isn't one of the values --
    it does not recognize '.' (CIF's other standard null marker), does not
    notice an atom-site loop with zero rows (an empty list trivially
    contains no '?', so cif_check reports it as fine), and does not check
    that the coordinate values are actually numeric (Dans_Diffraction's own
    readstfm() never raises on garbage -- it silently returns 0.0).
    """
    if not fc.cif_check(cifvals, list(_ATOM_KEYS)):
        return False, f"missing required atom-site data ({', '.join(_ATOM_KEYS)})"

    labels = cifvals.get("_atom_site_label")
    xs = cifvals.get("_atom_site_fract_x")
    ys = cifvals.get("_atom_site_fract_y")
    zs = cifvals.get("_atom_site_fract_z")

    # A single-atom (non-loop) CIF stores these as plain strings rather
    # than one-element lists -- normalize so the row iteration below is
    # uniform either way.
    if isinstance(labels, str):
        labels, xs, ys, zs = [labels], [xs], [ys], [zs]

    if not labels:
        return False, "the atom-site loop has no rows"

    for index, (x, y, z) in enumerate(zip(xs, ys, zs), start=1):
        if not (_is_numeric_cif_value(x) and _is_numeric_cif_value(y) and _is_numeric_cif_value(z)):
            label = labels[index - 1] if index - 1 < len(labels) else "?"
            return False, (
                f"atom site {index} ('{label}') has a missing or non-numeric "
                "fractional coordinate"
            )

    return True, ""


def parse_cif_candidate(
    raw_bytes: bytes, content_digest: str, display_path: str, effective_path: str
) -> CifImportResult:
    """Validate a candidate CIF's raw bytes and build a `StructureSource`.

    `effective_path` must already contain exactly `raw_bytes` on disk (see
    `advisor.domain.cif_import.io.materialize_snapshot`) -- it is what gets
    parsed and what downstream consumers should open, not `display_path`.
    Never mutates any accepted application state.
    """
    display_name = os.path.basename(display_path) or display_path

    try:
        text = _decode(raw_bytes)
    except Exception as exc:  # pragma: no cover - decoding is best-effort
        return CifImportResult(
            status="rejected",
            message=f"Could not read '{display_name}' as text: {exc}",
            error=str(exc),
        )

    blocks = _find_data_blocks(text)
    if len(blocks) > 1:
        names = ", ".join(f"data_{name}" for name in blocks)
        return CifImportResult(
            status="rejected",
            message=(
                f"'{display_name}' contains {len(blocks)} structures ({names}). "
                "Provide a file with a single structure."
            ),
        )

    try:
        cifvals = fc.readcif(effective_path)
    except Exception as exc:
        return CifImportResult(
            status="rejected",
            message=f"Could not parse '{display_name}' as CIF: {exc}",
            error=str(exc),
        )

    if not fc.cif_check(cifvals, list(_CELL_KEYS)):
        return CifImportResult(
            status="rejected",
            message=(
                f"'{display_name}' is missing required cell parameters "
                f"({', '.join(_CELL_KEYS)})."
            ),
        )

    try:
        a, _ = fg.readstfm(cifvals["_cell_length_a"])
        b, _ = fg.readstfm(cifvals["_cell_length_b"])
        c, _ = fg.readstfm(cifvals["_cell_length_c"])
        alpha, _ = fg.readstfm(cifvals["_cell_angle_alpha"])
        beta, _ = fg.readstfm(cifvals["_cell_angle_beta"])
        gamma, _ = fg.readstfm(cifvals["_cell_angle_gamma"])
    except (TypeError, ValueError) as exc:
        return CifImportResult(
            status="rejected",
            message=f"'{display_name}' has unreadable cell parameter values: {exc}",
            error=str(exc),
        )

    cell_ok, cell_reasons = validate_cell(a, b, c, alpha, beta, gamma)
    if not cell_ok:
        return CifImportResult(
            status="rejected",
            message=f"'{display_name}' has an invalid unit cell: {'; '.join(cell_reasons)}.",
        )

    formula = _clean_optional_str(cifvals.get("_chemical_formula_sum"))
    space_group = _clean_optional_str(cifvals.get("_symmetry_space_group_name_H-M")) or \
        _clean_optional_str(cifvals.get("_space_group_IT_number"))

    atoms_ok, atoms_reason = _atoms_are_usable(cifvals)
    data_block = blocks[0] if blocks else None

    doi = _first_present(cifvals, ("_journal_paper_doi",))
    source_id = _first_present(cifvals, _SOURCE_ID_KEYS)
    temperature_k = _first_numeric(cifvals, _TEMPERATURE_KEYS)
    pressure_kpa = _first_numeric(cifvals, _PRESSURE_KEYS)

    if not atoms_ok:
        capabilities = CifCapabilityReport(
            geometry_ok=True,
            structure_factor_ok=False,
            reasons=(atoms_reason,),
            message=f"Geometry available; {atoms_reason} prevents structure-factor calculations.",
        )
        status = "ready_geometry_only"
    else:
        capabilities = CifCapabilityReport(
            geometry_ok=True,
            structure_factor_ok=True,
            reasons=(),
            message="Ready for geometry and structure factors.",
        )
        status = "ready"

    source = StructureSource(
        content_digest=content_digest,
        data_block=data_block,
        display_name=display_name,
        display_path=display_path,
        formula=formula,
        space_group=space_group,
        a=a,
        b=b,
        c=c,
        alpha=alpha,
        beta=beta,
        gamma=gamma,
        capabilities=capabilities,
        effective_path=effective_path,
        source_kind="cif",
        source_id=source_id,
        doi=doi,
        temperature_k=temperature_k,
        pressure_kpa=pressure_kpa,
    )
    return CifImportResult(status=status, message=capabilities.message, source=source)
