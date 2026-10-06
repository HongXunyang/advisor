"""ADVISOR vs BLISS (ESRF ID20) UB-matrix comparison.

`bliss_ub_test.csv` (`;`-separated) holds 36 two-reflection orientation cases
measured at ID20. Per row: energy, lattice, two reflections with their
(th, chi, phi, tth); `UB_11..UB_33` = ADVISOR's UB (computed with the Kabsch
method, before Busing-Levy existed); `u11..u33` = BLISS's UB for the same input,
as supplied by the beamline (5-9 decimals per value, mostly 8).

Findings these tests pin down (see bliss_ub_comparison_report.html):

1. Lab-frame convention. `UB_BLISS = P @ UB_ADVISOR` with
   `P = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]` -- a proper rotation of -90 deg about
   the shared vertical z axis: BLISS x = ADVISOR +y (beam), BLISS y = -ADVISOR x.
   No handedness flip, no reciprocal-basis (B matrix) difference.
2. Algorithm. BLISS uses Busing-Levy (reflection 1 exact, reflection 2 fixes
   the plane). ADVISOR's Busing-Levy mode agrees with every supplied BLISS value
   to < 1e-7; ADVISOR's Kabsch mode differs by up to ~0.6 deg, an amount
   bounded by how inconsistent the two reflections are with the lattice.

Each check is a plain function `check_*(case)` raising AssertionError, listed
in `CASE_CHECKS`/`GLOBAL_CHECKS`; the pytest tests below and
`generate_bliss_comparison_report.py` both run exactly these functions, so the
report's verdict is the test verdict.
"""
import csv
import itertools
from pathlib import Path

import numpy as np
import pytest

from advisor.domain.orientation import fit_orientation_from_diffraction_tests
from advisor.domain.orientation_types import (
    FIT_METHOD_BUSING_LEVY,
    FIT_METHOD_KABSCH,
    DiffractionMeasurement,
)
from advisor.domain.orientation_validation import compute_measurement_vectors

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "bliss_ub_test.csv"

BLISS_FROM_ADVISOR = np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]], dtype=float)
"""Rotation taking ADVISOR's lab frame to BLISS's: `UB_BLISS = P @ UB_ADVISOR`."""

# Tolerances (UB in 1/Angstrom, including 2*pi). Observed maxima on the 36 rows
# in brackets; see the report's "Tolerances" section for the reasoning.
ADVISOR_CSV_ATOL = 1e-9        # current code vs ADVISOR values in the CSV [5e-10]
BUSING_LEVY_ATOL = 1e-6        # ADVISOR Busing-Levy vs BLISS [8.7e-8; supplied values have 5-9 decimals]
KABSCH_ATOL = 0.02             # ADVISOR Kabsch vs BLISS, element-wise [1.1e-2]
KABSCH_MAX_MISORIENTATION_DEG = 1.0  # [0.56 deg]
MISORIENTATION_BOUND_SLACK_DEG = 1e-4
PERMUTATION_MARGIN = 10.0      # 2nd-best signed permutation must be this much worse than P
EXPECTED_CASES = 36

UB_COLUMNS = [f"UB_{i}{j}" for i in (1, 2, 3) for j in (1, 2, 3)]
BLISS_COLUMNS = [f"u{i}{j}" for i in (1, 2, 3) for j in (1, 2, 3)]
LATTICE_COLUMNS = {"a": "a [Å]", "b": "b [Å]", "c": "c [Å]",
                   "alpha": "α [º]", "beta": "β [º]", "gamma": "γ [º]"}


def parse_hkl(text):
    return [float(x) for x in text.strip().strip("()").split()]


def load_cases(path=CSV_PATH):
    """Return (header, raw rows, cases); one case dict per CSV data row: line
    (1-based file line), energy_keV, lattice, measurements (energies in eV, as
    the fitter expects), ub_advisor, ub_bliss."""
    with open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=";"))
    header = rows[0]
    col = {name: header.index(name) for name in header if name}
    cases = []
    for line, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        energy_keV = float(row[col["E [keV]"]])
        measurements = []
        for i in (1, 2):
            h, k, l = parse_hkl(row[col[f"(h{i} k{i} l{i})"]])
            measurements.append({
                "H": h, "K": k, "L": l, "energy": energy_keV * 1000.0,
                "theta": float(row[col[f"th{i} [º]"]]), "chi": float(row[col[f"chi{i} [º]"]]),
                "phi": float(row[col[f"phi{i} [º]"]]), "tth": float(row[col[f"tth{i} [º]"]]),
            })
        cases.append({
            "line": line,
            "energy_keV": energy_keV,
            "lattice": {k: float(row[col[v]]) for k, v in LATTICE_COLUMNS.items()},
            "measurements": measurements,
            "ub_advisor": np.array([float(row[col[c]]) for c in UB_COLUMNS]).reshape(3, 3),
            "ub_bliss": np.array([float(row[col[c]]) for c in BLISS_COLUMNS]).reshape(3, 3),
        })
    return header, rows, cases


def signed_permutations():
    """All 48 signed 3x3 permutation matrices (proper and improper)."""
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            matrix = np.zeros((3, 3))
            for row, (column, sign) in enumerate(zip(perm, signs)):
                matrix[row, column] = sign
            yield matrix


def misorientation_deg(ub_a, ub_b):
    """Angle of the rotation R = ub_b @ inv(ub_a), projected to the nearest
    proper rotation (same B on both sides, so R is U_b @ U_a^T)."""
    u, _, vt = np.linalg.svd(ub_b @ np.linalg.inv(ub_a))
    rotation = u @ vt
    return float(np.degrees(np.arccos(np.clip((np.trace(rotation) - 1) / 2, -1, 1))))


def interreflection_angle_mismatch_deg(case):
    """Lattice-predicted minus measured angle between the two reflections --
    zero for perfectly consistent data; the source of Kabsch/BL differences."""
    (g1, q1), (g2, q2) = [
        compute_measurement_vectors(case["lattice"], DiffractionMeasurement.from_dict(m))
        for m in case["measurements"]
    ]

    def angle(a, b):
        return np.degrees(np.arctan2(np.linalg.norm(np.cross(a, b)), a @ b))

    return float(angle(g1, g2) - angle(q1, q2))


def fit(case, method):
    result = fit_orientation_from_diffraction_tests(case["lattice"], case["measurements"], method=method)
    assert result.valid, f"line {case['line']}: {result.message}"
    return result


# ------------------------------------------------------------------ checks
# Shared by pytest (below) and the report generator.

def check_csv_well_formed(header, raw_rows, cases):
    """36 cases, a constant column count, every value numeric -- guards
    against copy/paste glitches such as three numbers in one cell."""
    assert len(cases) == EXPECTED_CASES, f"{len(cases)} cases, expected {EXPECTED_CASES}"
    assert {len(row) for row in raw_rows} == {len(header)}, "rows have differing column counts"
    for case in cases:
        assert np.all(np.isfinite(case["ub_advisor"])) and np.all(np.isfinite(case["ub_bliss"])), \
            f"line {case['line']}: non-finite UB value"


def check_frame_rotation_is_proper(*_):
    assert np.allclose(BLISS_FROM_ADVISOR @ BLISS_FROM_ADVISOR.T, np.eye(3))
    assert abs(np.linalg.det(BLISS_FROM_ADVISOR) - 1.0) < 1e-12


def check_convention_is_unique_signed_permutation(case):
    """Searching all 48 row permutations/sign flips independently per row,
    P is the best match and every alternative is clearly worse."""
    errors = sorted(
        (float(np.abs(m @ case["ub_advisor"] - case["ub_bliss"]).max()), m.tobytes())
        for m in signed_permutations()
    )
    (best, best_matrix), (second, _) = errors[0], errors[1]
    assert best_matrix == BLISS_FROM_ADVISOR.tobytes(), "best signed permutation is not P"
    assert second > PERMUTATION_MARGIN * best, f"runner-up only {second / best:.1f}x worse than P"


def check_csv_advisor_values_reproduced_by_kabsch(case):
    np.testing.assert_allclose(fit(case, FIT_METHOD_KABSCH).UB, case["ub_advisor"], rtol=0, atol=ADVISOR_CSV_ATOL)


def check_busing_levy_matches_bliss(case):
    ub = BLISS_FROM_ADVISOR @ fit(case, FIT_METHOD_BUSING_LEVY).UB
    np.testing.assert_allclose(ub, case["ub_bliss"], rtol=0, atol=BUSING_LEVY_ATOL)


def check_kabsch_close_to_bliss_and_gap_explained(case):
    ub = BLISS_FROM_ADVISOR @ fit(case, FIT_METHOD_KABSCH).UB
    np.testing.assert_allclose(ub, case["ub_bliss"], rtol=0, atol=KABSCH_ATOL)
    misorientation = misorientation_deg(ub, case["ub_bliss"])
    assert misorientation <= KABSCH_MAX_MISORIENTATION_DEG, f"misorientation {misorientation:.3f} deg"
    # Both methods agree exactly on consistent data, so the gap can be no
    # larger than the inconsistency between the two reflections.
    mismatch = abs(interreflection_angle_mismatch_deg(case))
    assert misorientation <= mismatch + MISORIENTATION_BOUND_SLACK_DEG, \
        f"misorientation {misorientation:.4f} deg exceeds reflection-angle mismatch {mismatch:.4f} deg"


GLOBAL_CHECKS = (check_csv_well_formed, check_frame_rotation_is_proper)
CASE_CHECKS = (
    check_convention_is_unique_signed_permutation,
    check_csv_advisor_values_reproduced_by_kabsch,
    check_busing_levy_matches_bliss,
    check_kabsch_close_to_bliss_and_gap_explained,
)


def run_all_checks(header, raw_rows, cases):
    """Run every check; return a list of (check name, line or None, error
    message or None). Used by the report generator."""
    outcomes = []
    for check in GLOBAL_CHECKS:
        outcomes.append((check.__name__, None, _run(check, header, raw_rows, cases)))
    for check in CASE_CHECKS:
        for case in cases:
            outcomes.append((check.__name__, case["line"], _run(check, case)))
    return outcomes


def _run(check, *args):
    try:
        check(*args)
    except AssertionError as exc:
        return str(exc).strip().splitlines()[0] if str(exc).strip() else "assertion failed"
    return None


# ------------------------------------------------------------------ pytest

HEADER, RAW_ROWS, CASES = load_cases()
case_params = pytest.mark.parametrize("case", CASES, ids=[f"line{c['line']}" for c in CASES])


@pytest.mark.parametrize("check", GLOBAL_CHECKS, ids=lambda c: c.__name__)
def test_global(check):
    check(HEADER, RAW_ROWS, CASES)


@pytest.mark.parametrize("check", CASE_CHECKS, ids=lambda c: c.__name__)
@case_params
def test_case(check, case):
    check(case)


def test_report_runner_detects_a_perturbed_reference():
    """The report's verdict comes from run_all_checks; a BLISS value pushed
    beyond tolerance must show up there as a failure, not as an all-pass."""
    perturbed = [dict(c, ub_bliss=c["ub_bliss"].copy()) for c in CASES]
    perturbed[0]["ub_bliss"][0, 0] += 0.002
    failures = [o for o in run_all_checks(HEADER, RAW_ROWS, perturbed) if o[2] is not None]
    assert ("check_busing_levy_matches_bliss", CASES[0]["line"]) in {(name, line) for name, line, _ in failures}
    assert all(line == CASES[0]["line"] for _, line, _ in failures)
