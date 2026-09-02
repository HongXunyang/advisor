"""Domain logic for the Reflection List & Calculator feature.

Pure functions and typed records for generating, filtering, and serializing
arbitrary integer HKL reflections -- independent of any displayed 2D plane
and independent of PyQt. Follows the same dependency-free style as
``plane_utils.py``.
"""

import csv
import io
import json
from dataclasses import dataclass

# Hard cap on bulk reflection generation for v1 (no background thread /
# progress reporting yet -- see structure_factor_controller.py). Roughly an
# order of magnitude above anything currently exercised in the app (the
# largest existing usage is a 216-point 6^3 cube).
MAX_BULK_REFLECTIONS = 8000

# Default extinction tolerance, relative to |F(0,0,0)| (the largest possible
# |F| for any reflection of a given structure). Empirically measured against
# a synthetic FCC test structure (4 identical atoms at the face-centering
# positions, so every mixed-parity HKL is a genuine systematic absence):
# Dans_Diffraction's true floating-point noise floor on those reflections is
# ~1e-14 to 1e-17 relative to F(000), not the 1e-10-1e-6 this comment used to
# claim. 1e-6 leaves ~8 orders of magnitude of margin above that measured
# noise floor -- comfortably robust even for much larger/noisier unit cells
# -- while being 1000x tighter than the previous 1e-3 default, so it targets
# genuine numerical zeros only, not merely weak-but-real reflections. Use
# the separate ``filter_min_intensity`` for a deliberate weak-reflection
# cutoff -- conflating the two here would silently drop real, observable
# reflections under the "extinct" label.
DEFAULT_EXTINCTION_REL_TOL = 1e-6


@dataclass(frozen=True)
class Reflection:
    """A single HKL reflection with its complex structure factor.

    ``f_magnitude`` and ``intensity`` are derived properties, not stored
    fields, so they can never drift out of sync with ``f_real``/``f_imag``.
    """

    h: int
    k: int
    l: int
    f_real: float
    f_imag: float

    @property
    def f_magnitude(self) -> float:
        return (self.f_real ** 2 + self.f_imag ** 2) ** 0.5

    @property
    def intensity(self) -> float:
        return self.f_real ** 2 + self.f_imag ** 2


@dataclass(frozen=True)
class ReflectionSnapshot:
    """An immutable record of exactly what a 2D view calculated and plotted.

    Captured once, at the moment a plane is successfully drawn, so a later
    "Export" action can read back exactly this data instead of recomputing
    through the shared, mutable ``StructureFactorCalculator`` -- which may
    since have been reinitialized (by either subtab) at a different energy,
    silently producing different numbers than what is actually on screen.

    ``reflections`` holds every calculated point, unfiltered; extinction/
    minimum-intensity filtering is applied later, against this frozen data,
    never against a fresh calculator call.
    """

    reflections: tuple
    f_000_magnitude: float
    cif_filename: str
    energy_kev: float
    scattering_type: str


def count_hkl_range(h_range, k_range, l_range, exclude_origin: bool = True) -> int:
    """Count how many points ``generate_hkl_range(...)`` would produce, without
    materializing them.

    Lets a caller reject an oversized request before paying the cost (time
    and memory) of building the full list -- with wide-enough bounds,
    materializing the Cartesian product first can itself be expensive even
    though the resulting list would just be discarded.

    Raises:
        ValueError: if any axis has min > max (same as ``generate_hkl_range``).
    """
    for name, (lo, hi) in (("H", h_range), ("K", k_range), ("L", l_range)):
        if lo > hi:
            raise ValueError(f"{name} range minimum ({lo}) is greater than maximum ({hi}).")

    count = (h_range[1] - h_range[0] + 1) * (k_range[1] - k_range[0] + 1) * (l_range[1] - l_range[0] + 1)
    origin_included = (
        h_range[0] <= 0 <= h_range[1] and k_range[0] <= 0 <= k_range[1] and l_range[0] <= 0 <= l_range[1]
    )
    if exclude_origin and origin_included:
        count -= 1
    return count


def generate_hkl_range(h_range, k_range, l_range, exclude_origin: bool = True) -> list:
    """Generate all integer (H, K, L) triples within the given inclusive bounds.

    Args:
        h_range: (min, max) inclusive bounds for H.
        k_range: (min, max) inclusive bounds for K.
        l_range: (min, max) inclusive bounds for L.
        exclude_origin: if True (default), omit (0, 0, 0) from the result.
            Callers that want a full reference cube (e.g. for a 3D scatter)
            should pass ``exclude_origin=False``.

    Returns:
        list of (h, k, l) int tuples.

    Raises:
        ValueError: if any axis has min > max.
    """
    for name, (lo, hi) in (("H", h_range), ("K", k_range), ("L", l_range)):
        if lo > hi:
            raise ValueError(f"{name} range minimum ({lo}) is greater than maximum ({hi}).")

    points = []
    for h in range(h_range[0], h_range[1] + 1):
        for k in range(k_range[0], k_range[1] + 1):
            for l in range(l_range[0], l_range[1] + 1):
                if exclude_origin and h == 0 and k == 0 and l == 0:
                    continue
                points.append((h, k, l))
    return points


def build_reflections(hkl_list, f_values) -> list:
    """Zip HKL indices with raw complex structure-factor values into typed records.

    Raises:
        ValueError: if the two inputs have different lengths. ``zip`` alone
            would silently truncate to the shorter one, which -- since
            callers report "generated" counts from ``len(hkl_list)`` -- could
            otherwise produce a mismatched generated/filtered count without
            any indication anything went wrong.
    """
    hkl_list = list(hkl_list)
    f_values = list(f_values)
    if len(hkl_list) != len(f_values):
        raise ValueError(
            f"hkl_list has {len(hkl_list)} points but f_values has {len(f_values)} -- "
            "these must be the same length."
        )
    reflections = []
    for (h, k, l), f in zip(hkl_list, f_values):
        reflections.append(
            Reflection(h=int(h), k=int(k), l=int(l), f_real=float(f.real), f_imag=float(f.imag))
        )
    return reflections


def filter_extinct(reflections, f_000_magnitude: float, rel_tol: float = DEFAULT_EXTINCTION_REL_TOL) -> list:
    """Exclude reflections whose |F| is numerically zero relative to |F(0,0,0)|.

    ``f_000_magnitude`` (the forward-scattering structure factor's
    magnitude) equals the total unit-cell electron count and is the largest
    possible |F| for any reflection of a given structure, so anchoring the
    tolerance to it scales naturally per CIF rather than using a fixed
    absolute number.
    """
    threshold = rel_tol * f_000_magnitude
    return [r for r in reflections if r.f_magnitude >= threshold]


def filter_min_intensity(reflections, min_intensity: float) -> list:
    """Exclude reflections below an explicit minimum calculated intensity.

    Kept separate from ``filter_extinct`` -- "numerically zero" and "weak
    but non-zero" are different concepts and must not be conflated.
    """
    return [r for r in reflections if r.intensity >= min_intensity]


def serialize_to_csv(reflections, metadata: dict) -> str:
    """Serialize reflections to a CSV string.

    Columns: h,k,l,f_real,f_imag,f_magnitude,intensity,energy_kev. Full
    float precision (str-formatted, not rounded display strings) so the
    export can reproduce and analyze the results exactly.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["h", "k", "l", "f_real", "f_imag", "f_magnitude", "intensity", "energy_kev"])
    energy_kev = metadata.get("energy_kev")
    for r in reflections:
        writer.writerow([r.h, r.k, r.l, r.f_real, r.f_imag, r.f_magnitude, r.intensity, energy_kev])
    return buffer.getvalue()


def serialize_to_json(reflections, metadata: dict) -> str:
    """Serialize reflections and metadata to a structured JSON string.

    Complex values are serialized as separate f_real/f_imag numeric fields,
    never a language-specific complex-number string.
    """
    payload = {
        "metadata": dict(metadata),
        "reflections": [
            {
                "h": r.h,
                "k": r.k,
                "l": r.l,
                "f_real": r.f_real,
                "f_imag": r.f_imag,
                "f_magnitude": r.f_magnitude,
                "intensity": r.intensity,
            }
            for r in reflections
        ],
    }
    return json.dumps(payload, indent=2)
