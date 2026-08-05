"""Tests for advisor.domain.unit_converter.UnitConverter."""
import numpy as np
import pytest

from advisor.domain import UnitConverter


@pytest.fixture
def converter():
    return UnitConverter()


class TestEvAngstromRoundTrip:
    @pytest.mark.parametrize("energy_ev", [100.0, 930.0, 8000.0, 12398.425])
    def test_round_trip(self, converter, energy_ev):
        wavelength = converter.ev_to_angstrom(energy_ev)
        recovered = converter.angstrom_to_ev(wavelength)
        assert recovered == pytest.approx(energy_ev)

    def test_known_value_cu_kalpha(self, converter):
        """8047.8 eV is close to the Cu K-alpha edge (~1.54 A)."""
        wavelength = converter.ev_to_angstrom(8047.8)
        assert wavelength == pytest.approx(1.5406, abs=1e-3)

    def test_vectorized_input(self, converter):
        energies = np.array([100.0, 930.0, 8000.0])
        wavelengths = converter.ev_to_angstrom(energies)
        assert wavelengths == pytest.approx(converter.angstrom_to_ev_constant / energies)


class TestEvPhzRoundTrip:
    @pytest.mark.parametrize("energy_ev", [1.0, 930.0, 5000.0])
    def test_round_trip(self, converter, energy_ev):
        freq = converter.ev_to_phz(energy_ev)
        recovered = converter.phz_to_ev(freq)
        assert recovered == pytest.approx(energy_ev)

    def test_ev_to_phz_is_linear(self, converter):
        assert converter.ev_to_phz(1000.0) == pytest.approx(
            2 * converter.ev_to_phz(500.0)
        )


class TestEvToMomentum:
    def test_zero_energy_gives_zero_momentum(self, converter):
        assert converter.ev_to_momentum(0.0) == pytest.approx(0.0)

    def test_scales_linearly_with_energy(self, converter):
        assert converter.ev_to_momentum(1000.0) == pytest.approx(
            2 * converter.ev_to_momentum(500.0)
        )

    def test_vectorized_input(self, converter):
        energies = np.array([100.0, 200.0, 300.0])
        momenta = converter.ev_to_momentum(energies)
        assert momenta == pytest.approx(energies * converter.ev_to_momentum_constant)
