"""Domain logic for structure factor feature."""

from .structure_factor_calculator import StructureFactorCalculator
from .plane_utils import generate_hkl_points_on_plane, check_accessibility
from .reflection_list import (
    Reflection,
    ReflectionSnapshot,
    generate_hkl_range,
    count_hkl_range,
    build_reflections,
    filter_extinct,
    filter_min_intensity,
    serialize_to_csv,
    serialize_to_json,
    MAX_BULK_REFLECTIONS,
    DEFAULT_EXTINCTION_REL_TOL,
)

__all__ = [
    "StructureFactorCalculator",
    "generate_hkl_points_on_plane",
    "check_accessibility",
    "Reflection",
    "ReflectionSnapshot",
    "generate_hkl_range",
    "count_hkl_range",
    "build_reflections",
    "filter_extinct",
    "filter_min_intensity",
    "serialize_to_csv",
    "serialize_to_json",
    "MAX_BULK_REFLECTIONS",
    "DEFAULT_EXTINCTION_REL_TOL",
]

