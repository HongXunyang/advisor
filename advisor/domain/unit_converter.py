import numpy as np
from typing import Union, Optional


class UnitConverter:
    """
    A class for converting between different units commonly used in X-ray spectroscopy.
    """

    def __init__(self):
        # Fundamental constants
        self.angstrom_to_ev_constant = 12398.425
        self.ev_to_phz_constant = 0.2418
        self.ev_to_momentum_constant = 0.080656  # in A^-1

    def ev_to_angstrom(
        self, energy: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        """
        Convert X-ray energy from eV to wavelength in Angstrom.

        Args:
            energy: Energy in eV

        Returns:
            Wavelength in Angstrom
        """
        return self.angstrom_to_ev_constant / energy

    def angstrom_to_ev(
        self, wavelength: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        """
        Convert X-ray wavelength from Angstrom to energy in eV.

        Args:
            wavelength: Wavelength in Angstrom

        Returns:
            Energy in eV
        """
        return self.angstrom_to_ev_constant / wavelength

    def ev_to_phz(self, energy: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Convert X-ray energy from eV to frequency in PHz.

        Args:
            energy: Energy in eV

        Returns:
            Frequency in PHz
        """
        return energy * self.ev_to_phz_constant

    def phz_to_ev(
        self, frequency: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        """
        Convert X-ray frequency from PHz to energy in eV.

        Args:
            frequency: Frequency in PHz

        Returns:
            Energy in eV
        """
        return frequency / self.ev_to_phz_constant

    def ev_to_momentum(
        self, energy: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        """
        Convert X-ray energy from eV to momentum in Å^-1.

        Args:
            energy: Energy in eV

        Returns:
            Momentum in Å^-1
        """
        return energy * self.ev_to_momentum_constant
