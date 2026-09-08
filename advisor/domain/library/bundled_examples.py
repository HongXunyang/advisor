"""Bundled "Try an example" CIF(s) shipped with ADVISOR.

Resource resolution uses `os.path.dirname(advisor.__file__)` -- the same
pattern already used by `change_structure_icon()`
(`advisor/ui/dialogs/change_structure_dialog.py`) -- which resolves relative
to the *installed* package, not the process working directory, so this works
identically from a repo checkout, an installed wheel, or any other cwd.

Exactly one example ships today (a second is explicitly optional per
REQUIREMENT_2.md and would add UI complexity); `EXAMPLES` is a tuple so a
second entry is purely additive data, not a code change.

`advisor/resources/data/nacl.cif` is deliberately NOT reused here: its own
`_publ_section_title` is "Structural refinements of high-pressure phases in
germanium dioxide" (DOI 10.1107/S0108768103021761) even though its
`_chemical_formula_sum` says sodium chloride, and its cell length
(2.8600(3) A) is implausible for real ambient NaCl (~5.64 A) -- almost
certainly a mislabeled/mismatched COD harvest artifact, and separately
load-bearing for many existing calculator tests. The example below is
instead an explicitly idealized teaching structure with documented,
non-fabricated values.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BundledExample:
    key: str
    resource_relpath: str
    display_name: str
    citation: str
    test_energy_ev: float
    test_energy_label: str


EXAMPLES = (
    BundledExample(
        key="idealized_rock_salt",
        resource_relpath=os.path.join("library_examples", "idealized_rock_salt.cif"),
        display_name="Idealized rock salt (NaCl-type)",
        citation=(
            "Idealized illustrative structure, not a specific experimental "
            "deposit. Uses the commonly cited ambient rock-salt lattice "
            "constant (a ≈ 5.6402 Å) with the standard Fm-3m "
            "(No. 225) atomic arrangement (4 Na + 4 Cl per conventional "
            "cell)."
        ),
        test_energy_ev=8048.0,
        test_energy_label="Cu Kα1 (≈ 8.05 keV)",
    ),
)


def get_bundled_example(key: str) -> BundledExample:
    for example in EXAMPLES:
        if example.key == key:
            return example
    raise KeyError(f"Unknown bundled example: {key!r}")


def resource_absolute_path(example: BundledExample) -> str:
    import advisor

    return os.path.join(os.path.dirname(advisor.__file__), "resources", example.resource_relpath)


def find_example_by_content_hash(content_hash: str):
    """Identify which bundled example (if any) a saved library record came
    from, by comparing its stored content hash against each bundled
    resource's own hash -- cheap since these files are tiny and few, and
    avoids needing to store a bundled-example key in the library schema."""
    import hashlib

    for example in EXAMPLES:
        try:
            with open(resource_absolute_path(example), "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
        except OSError:
            continue
        if digest == content_hash:
            return example
    return None
