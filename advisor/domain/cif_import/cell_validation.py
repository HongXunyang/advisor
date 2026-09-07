"""Pure unit-cell validity checks.

No Qt, no Dans_Diffraction, no feature-domain imports -- reusable for CIF
import and, if useful later, manual-entry validation. Widget ranges must
never be the enforcement mechanism for validity (see REQUIREMENT_1); this is
the actual enforcement.
"""

import math
from typing import List, Tuple


def validate_cell(
    a: float, b: float, c: float, alpha: float, beta: float, gamma: float
) -> Tuple[bool, List[str]]:
    """Validate a unit cell is physically meaningful.

    Checks finite positive lengths, angles strictly in (0, 180) degrees, and
    a non-degenerate (positive, finite) cell volume via the standard
    triclinic-volume discriminant. Does not raise; returns
    (is_valid, reasons) with reasons empty when valid.
    """
    reasons: List[str] = []

    for name, value in (("a", a), ("b", b), ("c", c)):
        if value is None or not math.isfinite(value) or value <= 0:
            reasons.append(f"cell length {name} must be a finite positive number")

    for name, value in (("alpha", alpha), ("beta", beta), ("gamma", gamma)):
        if value is None or not math.isfinite(value) or not (0.0 < value < 180.0):
            reasons.append(
                f"cell angle {name} must be a finite value strictly between 0 and 180 degrees"
            )

    if reasons:
        return False, reasons

    cos_a = math.cos(math.radians(alpha))
    cos_b = math.cos(math.radians(beta))
    cos_g = math.cos(math.radians(gamma))
    discriminant = 1 - cos_a**2 - cos_b**2 - cos_g**2 + 2 * cos_a * cos_b * cos_g

    if discriminant <= 1e-10:
        reasons.append(
            "cell angles do not describe a non-degenerate unit cell (zero or negative volume)"
        )
        return False, reasons

    volume = a * b * c * math.sqrt(discriminant)
    if not math.isfinite(volume) or volume <= 0:
        reasons.append("unit cell has zero or non-finite volume")
        return False, reasons

    return True, []
