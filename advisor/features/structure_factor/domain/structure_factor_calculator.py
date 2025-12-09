"""This is a module responsible for calculating the structure factor of a given crystal
structure.

CONVENTION:
- energy input is in eV

"""

import Dans_Diffraction as dif
import numpy as np
import os

DEFAULT_HKL_LIST = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
    [1, 1, 0],
    [1, 0, 1],
    [0, 1, 1],
    [1, 1, 1],
    [2, 0, 0],
    [0, 2, 0],
    [0, 0, 2],
    [2, 1, 0],
    [1, 2, 0],
    [2, 2, 0],
]
SCATTERING_TYPE = "xray dispersion"
METHOD = "x-ray"


class StructureFactorCalculator:
    def __init__(self):
        self.calculator = None
        self._cif_file_path = None
        self._energy = None  # in eV
        self._is_initialized = False

    @property
    def cif_file_path(self):
        return self._cif_file_path

    @cif_file_path.setter
    def cif_file_path(self, cif_file_path: str):
        # check if the file exists
        if not os.path.exists(cif_file_path):
            raise FileNotFoundError(f"File {cif_file_path} does not exist.")
        self._cif_file_path = cif_file_path

    @property
    def is_initialized(self):
        return self._is_initialized

    @is_initialized.setter
    def is_initialized(self, is_initialized: bool):
        self._is_initialized = is_initialized

    @property
    def energy(self):
        """Energy in eV"""
        return self._energy

    @energy.setter
    def energy(self, energy: float):
        """Energy in eV"""
        self._energy = energy
        if self.is_initialized:
            self.calculator.Scatter.setup_scatter(
                scattering_type=METHOD, energy_kev=self.energy / 1000
            )

    def initialize(self, cif_file_path: str, energy: float):
        self.cif_file_path = cif_file_path
        self.energy = energy
        self.calculator = dif.Crystal(self.cif_file_path)
        self.calculator.Scatter.setup_scatter(
            scattering_type=METHOD, energy_kev=self.energy / 1000
        )
        self.is_initialized = True

    def calculate_structure_factors(
        self,
        hkl_input_list: list[list[int]] = None,
        energy: float = None,
    ):
        if energy is not None:
            # reset the energy
            self.energy = energy
        if hkl_input_list is None:
            hkl_input_list = DEFAULT_HKL_LIST
            result = self.calculator.Scatter.structure_factor(
                hkl=hkl_input_list, scattering_type=SCATTERING_TYPE
            )
        else:
            result = self.calculator.Scatter.structure_factor(
                hkl=hkl_input_list, scattering_type=SCATTERING_TYPE
            )

        return result


if __name__ == "__main__":
    calculator = StructureFactorCalculator()
    calculator.initialize(cif_file_path="data/nacl.cif", energy=10000)
    result = calculator.calculate_structure_factors()
    for hkl, F_hkl in zip(DEFAULT_HKL_LIST, result):
        print(f"hkl = {hkl}, |F| = {np.abs(F_hkl)}")
