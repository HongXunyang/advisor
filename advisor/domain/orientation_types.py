#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Typed contracts for the UB-matrix orientation-fitting workflow.

These dataclasses are internal to the orientation-fitting domain code
(`orientation.py`, `orientation_validation.py`) and its one UI consumer
(`DiffractionTestDialog` / `InitWindow`). The application parameter
boundary (`AppController`/feature `set_parameters`) still receives plain
dicts, converted via `DiffractionMeasurement.to_dict()`, so downstream
consumers such as `structure_factor_tab.py` are unaffected.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

REQUIRED_MEASUREMENT_KEYS = ("H", "K", "L", "energy", "tth", "theta", "phi", "chi")


@dataclass(frozen=True)
class DiffractionMeasurement:
    """One diffraction-test row: a known HKL and the goniometer angles/energy
    at which it was measured."""

    H: float
    K: float
    L: float
    energy: float
    tth: float
    theta: float
    phi: float
    chi: float

    def to_dict(self) -> dict:
        return {
            "H": self.H, "K": self.K, "L": self.L,
            "energy": self.energy, "tth": self.tth,
            "theta": self.theta, "phi": self.phi, "chi": self.chi,
        }

    @staticmethod
    def from_dict(data: dict) -> "DiffractionMeasurement":
        """Parse a raw dict into a DiffractionMeasurement.

        Raises KeyError if a required key is missing, ValueError/TypeError
        if a value can't be converted to float. Callers should catch these
        and turn them into a not-completed OrientationFitResult rather than
        letting them propagate.
        """
        missing = [k for k in REQUIRED_MEASUREMENT_KEYS if k not in data]
        if missing:
            raise KeyError(f"missing required keys: {missing}")
        return DiffractionMeasurement(
            H=float(data["H"]), K=float(data["K"]), L=float(data["L"]),
            energy=float(data["energy"]), tth=float(data["tth"]),
            theta=float(data["theta"]), phi=float(data["phi"]), chi=float(data["chi"]),
        )

    def is_finite(self) -> bool:
        return all(
            math.isfinite(v)
            for v in (self.H, self.K, self.L, self.energy, self.tth, self.theta, self.phi, self.chi)
        )


@dataclass(frozen=True)
class OrientationFitConfig:
    """Centralized, named tolerances for identifiability validation and fit
    acceptance. All angle/vector tolerances are dimensionless (sine of the
    angle between two vectors) or in reciprocal-lattice units (r.l.u.,
    i.e. the same units as H, K, L), never a bare magic number without a
    documented unit.
    """

    # --- identifiability (advisor/domain/orientation_validation.py) ---
    min_measurements: int = 2
    hkl_zero_tolerance: float = 1e-9
    """A measurement whose (H,K,L) norm is below this is rejected as (0,0,0)."""

    energy_min: float = 1e-6
    """eV. Energies at or below this are rejected as non-physical."""

    tth_min: float = 1e-6
    tth_max: float = 180.0
    """degrees. tth must lie in (tth_min, tth_max]."""

    motor_angle_min: float = -180.0
    motor_angle_max: float = 180.0
    """degrees. theta, phi, and chi must each lie in [motor_angle_min,
    motor_angle_max] -- matches the range used for these same angles
    elsewhere in the app (e.g. scattering_geometry's angle input widgets)."""

    parallel_sin_tolerance: float = 1e-3
    """Two reciprocal (or observed) vectors are considered parallel if the
    sine of the angle between them is below this."""

    magnitude_mismatch_tolerance: float = 0.05
    """Relative tolerance on |g_i| vs |q_i| (both r.l.u.-scaled, i.e. same
    units as B). Since rotation preserves vector norm, any physically valid
    measurement must have |g_i| ~= |q_i|; a larger mismatch means the
    entered HKL is inconsistent with the entered tth/energy for that row,
    independent of orientation. 5% default tolerance to absorb typical
    imprecision in manually-entered lattice constants."""

    duplicate_tolerance: float = 1e-6
    """r.l.u.-equivalent combined distance below which two measurements are
    considered duplicates of each other."""

    # --- fit acceptance (advisor/domain/orientation.py) ---
    residual_rms_threshold: float = 1e-3
    """r.l.u. A fit is accepted (`valid=True`) only if the RMS per-measurement
    HKL residual is below this.

    Calibrated against realistic motor-angle precision, not exact synthetic
    data: rounding tth/theta/phi/chi to 0.01 degrees (typical
    display/instrument resolution) before fitting produces residual RMS
    values up to ~2e-4 r.l.u. across a range of lattices/energies/geometries
    (verified with the existing analytic angle solver -- see
    tests/domain/test_orientation.py::test_round_trip_realistic_angle_rounding).
    A genuinely inconsistent fit (wrong HKL for the given angles, or
    measurements that don't share a common orientation) lands 3-4 orders of
    magnitude higher (~0.1-1+ r.l.u.). 1e-3 sits comfortably above the former
    and well below the latter. An exact-synthetic-data threshold like the
    previous 1e-6 default would reject essentially all real, rounded
    experimental input."""


@dataclass
class OrientationFitResult:
    """Result of `fit_orientation_from_diffraction_tests`.

    `completed`, `identifiable`, and `valid` are independent flags so that
    "the algorithm ran" is never conflated with "the orientation is
    trustworthy":
      - `completed`: the calculation ran to the end without an internal
        error (malformed input, lattice-initialization failure).
      - `identifiable`: the input passed identifiability validation (enough
        independent, non-degenerate measurements).
      - `valid`: `completed and identifiable` AND the resulting residual is
        below `OrientationFitConfig.residual_rms_threshold`.

    Only a `valid=True` result should be used to update UI Euler-angle
    fields or the downstream `ub_data` parameter.
    """

    completed: bool
    identifiable: bool
    valid: bool
    message: str
    rejection_reason: Optional[str] = None

    U: Optional[np.ndarray] = None
    UB: Optional[np.ndarray] = None
    roll: Optional[float] = None
    pitch: Optional[float] = None
    yaw: Optional[float] = None

    residual_rms: Optional[float] = None
    per_measurement_residuals: Optional[list] = None
    n_measurements_used: int = 0
    condition_number: Optional[float] = None

    lattice_params: dict = field(default_factory=dict)
    measurements: list = field(default_factory=list)  # list[DiffractionMeasurement]


@dataclass
class OrientationFitSession:
    """Holds the diffraction-test rows and last fit result for one Init
    Window session, so the "Set UB Matrix" dialog can remember its state
    across close/reopen instead of resetting to blank every time.

    Cleared by `InitWindow.reset_inputs()` and by any lattice-parameter or
    CIF change (see `init_window.py`), since a fit computed against one
    lattice is meaningless against another.
    """

    measurements: list = field(default_factory=list)  # list[DiffractionMeasurement]
    last_result: Optional[OrientationFitResult] = None
    lattice_params_at_fit: Optional[dict] = None

    def is_stale_against(self, lattice_params: dict) -> bool:
        """Whether the last fit (if any) was computed against different
        lattice parameters than the ones given."""
        if self.last_result is None or self.lattice_params_at_fit is None:
            return False
        return self.lattice_params_at_fit != lattice_params

    def clear(self) -> None:
        self.measurements = []
        self.last_result = None
        self.lattice_params_at_fit = None
