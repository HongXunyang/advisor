"""Tests for advisor.features.structure_factor.domain.structure_factor_calculator."""
import os

import numpy as np
import pytest

import advisor
from advisor.features.structure_factor.domain.structure_factor_calculator import (
    StructureFactorCalculator,
    DEFAULT_HKL_LIST,
)

NACL_CIF = os.path.join(
    os.path.dirname(advisor.__file__), "resources", "data", "nacl.cif"
)


@pytest.fixture
def calculator():
    calc = StructureFactorCalculator()
    calc.initialize(cif_file_path=NACL_CIF, energy=10000.0)
    return calc


class TestInitialize:
    def test_initialize_sets_state(self, calculator):
        assert calculator.is_initialized is True
        assert calculator.energy == 10000.0
        assert calculator.cif_file_path == NACL_CIF

    def test_missing_cif_file_raises(self):
        calc = StructureFactorCalculator()
        with pytest.raises(FileNotFoundError):
            calc.initialize(cif_file_path="does_not_exist.cif", energy=10000.0)

    def test_cif_file_path_setter_raises_for_missing_file(self):
        calc = StructureFactorCalculator()
        with pytest.raises(FileNotFoundError):
            calc.cif_file_path = "does_not_exist.cif"

    def test_energy_setter_before_initialize_does_not_raise(self):
        """Setting energy before is_initialized should just store the value."""
        calc = StructureFactorCalculator()
        calc.energy = 5000.0
        assert calc.energy == 5000.0
        assert calc.is_initialized is False


class TestCalculateStructureFactors:
    def test_default_hkl_list_returns_matching_length(self, calculator):
        result = calculator.calculate_structure_factors()
        assert len(result) == len(DEFAULT_HKL_LIST)

    def test_custom_hkl_list_returns_matching_length(self, calculator):
        hkl_list = [[1, 1, 1], [2, 0, 0], [2, 2, 0]]
        result = calculator.calculate_structure_factors(hkl_input_list=hkl_list)
        assert len(result) == len(hkl_list)

    def test_results_are_finite_complex_values(self, calculator):
        result = calculator.calculate_structure_factors(hkl_input_list=[[1, 1, 1], [2, 0, 0]])
        assert np.all(np.isfinite(np.abs(result)))

    def test_energy_override_updates_calculator_energy(self, calculator):
        calculator.calculate_structure_factors(hkl_input_list=[[1, 1, 1]], energy=12000.0)
        assert calculator.energy == 12000.0

    def test_different_energies_can_change_structure_factor_magnitude(self, calculator):
        """Sanity check that energy actually feeds into the calculation (dispersion)."""
        low = calculator.calculate_structure_factors(hkl_input_list=[[1, 1, 1]], energy=2000.0)
        high = calculator.calculate_structure_factors(hkl_input_list=[[1, 1, 1]], energy=15000.0)
        assert not np.allclose(low, high)
