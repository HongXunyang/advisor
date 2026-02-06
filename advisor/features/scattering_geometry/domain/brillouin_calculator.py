#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
from scipy.optimize import fsolve

from advisor.domain import angle_to_matrix
from advisor.domain.core import Lab

from .core import (_calculate_angles_factory, _calculate_angles_tth_fixed,
                   _calculate_hkl)


def is_feasible(theta, tth):
    """Check if the given theta is feasible. criteria: theta>0 and theta<tth
    """
    theta = np.array(theta)
    tth = np.array(tth)
    return (theta > 0) & (theta < tth)

class BrillouinCalculator:
    """Interface for the Brillouin zone calculator.

    This class handles all the calculations required for the Brillouin zone
    calculator tab. It's a pure Python implementation without PyQt dependencies.
    """

    def __init__(self):
        """Initialize the calculator."""
        self._initialized = False

        # Physical constants
        self.hPlanck = 6.62607015e-34  # Planck's constant [J·s]
        self.c_light = 299792458  # Speed of light [m/s]
        self.e = 1.602176634e-19  # Elementary charge [C]
        self.ev_to_lambda = 12398.42 # eV to Angstrom

        # Initialize sample
        self.lab = Lab()
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0

        # X-ray energy and derived quantities
        self.energy = 930  # eV
        self.lambda_A = None  # wavelength in Angstroms
        self.k_in = None  # wavevector magnitude

        # Reciprocal lattice vectors (calculated during initialization)
        self.reciprocal_lattice = None
        self.visualizer = None

    def initialize(
        self,
        params: dict,
    ):
        """Initialize with lattice parameters.

        Args:
            a, b, c (float): Lattice constants in Angstroms
            alpha, beta, gamma (float): Lattice angles in degrees
            energy (float): X-ray energy in eV
            yaw, pitch, roll (float): lattice rotation in degrees
            theta, phi, chi (float): sample rotation in degrees

        Returns:
            bool: True if initialization was successful
        """
        roll = params.get("roll", 0.0)
        pitch = params.get("pitch", 0.0)
        yaw = params.get("yaw", 0.0)
        a, b, c = params.get("a", 4), params.get("b", 4), params.get("c", 12)
        alpha, beta, gamma = (
            params.get("alpha", 90.0),
            params.get("beta", 90.0),
            params.get("gamma", 90.0),
        )
        # the default sample rotation position
        theta, phi, chi = 0.0, 0.0, 0.0
        try:
            # Store parameters
            self.energy = params["energy"]

            # Initialize sample
            self.lab.initialize(
                a,
                b,
                c,
                alpha,
                beta,
                gamma,
                roll,
                pitch,
                yaw,
                theta,
                phi,
                chi,
            )
            # Calculate wavelength and wavevector
            self.lambda_A = self.ev_to_lambda / self.energy
            self.k_in = 2 * np.pi / self.lambda_A

            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing calculator: {str(e)}")
            return False

    def change_energy(self, energy):
        """Change the energy of the X-ray source, in eV"""
        self.energy = energy
        self.lambda_A = self.ev_to_lambda / self.energy
        self.k_in = 2 * np.pi / self.lambda_A
        return True
    
    def reorient_sample(self, roll, pitch, yaw):
        """Reorient the sample with respect to the lab"""
        self.lab.reorient(roll, pitch, yaw)
        return True

    def _sample_to_lab_conversion(self, a_vec, b_vec, c_vec):
        """Convert vectors from sample coordinate system to lab coordinate system."""
        # For now, just return the same vectors
        # This should be implemented based on the actual coordinate system conversion
        return a_vec, b_vec, c_vec

    def get_k_magnitude(self, tth):
        return 2.0 * self.k_in * np.sin(np.radians(tth / 2.0))

    def calculate_hkl(self, tth, theta, phi, chi):
        """Calculate HKL from scattering angles.

        Args:
            tth (float): Scattering angle in degrees
            theta (float): Sample theta rotation in degrees
            phi (float): Sample phi rotation in degrees
            chi (float): Sample chi rotation in degrees

        """
        if not self.is_initialized():
            raise ValueError("Calculator not initialized")

        a_vec_lab, b_vec_lab, c_vec_lab = self.lab.get_real_space_vectors()
        return _calculate_hkl(
            self.k_in, tth, theta, phi, chi, a_vec_lab, b_vec_lab, c_vec_lab
        )

    def calculate_angles(
        self,
        H,
        K,
        L,
        fixed_angle,
        fixed_angle_name="chi",
    ):
        """Calculate scattering angles from HKL indices.

        Returns up to two solutions if they exist.

        Args:
            H, K, L (float): HKL indices
            fixed_angle (float): Value of the fixed angle in degrees
            fixed_angle_name (str): Name of the fixed angle ('chi' or 'phi')

        Returns:
            dict: Dictionary containing:
                - tth (list): Scattering angles in degrees
                - theta (list): Sample theta rotation values in degrees
                - phi (list): Sample phi rotation values in degrees
                - chi (list): Sample chi rotation values in degrees
                - H, K, L (float): Input HKL indices
                - number_of_solutions (int): Number of distinct solutions found
                - feasible (list): Boolean list indicating if each solution is feasible
                - success (bool): Whether calculation succeeded
                - error (str or None): Error message if any
        """

        if not self.is_initialized():
            raise ValueError("Calculator not initialized")

        calculate_angles = _calculate_angles_factory(fixed_angle_name)
        a, b, c, alpha, beta, gamma = self.lab.get_lattice_parameters()
        roll, pitch, yaw = self.lab.get_lattice_angles()
        try:
            result = calculate_angles(
                self.k_in,
                H,
                K,
                L,
                a,
                b,
                c,
                alpha,
                beta,
                gamma,
                roll,
                pitch,
                yaw,
                fixed_angle,
            )
        except Exception as e:
            return {
                "success": False,
                "error": "No solution found; The Q point is possibly not reachable at this energy and/or scattering angle tth. System message:" + str(e),
            }
        
        # Extract lists from result
        tth_list = result["tth"]
        theta_list = result["theta"]
        phi_list = result["phi"]
        chi_list = result["chi"]
        num_solutions = result["number_of_solutions"]
        
        # Calculate feasibility for each solution
        feasible_list = [is_feasible(theta_list[i], tth_list[i]) for i in range(len(theta_list))]
        
        return {
            "tth": tth_list,
            "theta": theta_list,
            "phi": phi_list,
            "chi": chi_list,
            "H": H,
            "K": K,
            "L": L,
            "number_of_solutions": num_solutions,
            "success": True,
            "error": None,
            "feasible": feasible_list,
        }

    def calculate_angles_tth_fixed(
        self,
        tth,
        H=0.15,
        K=0.1,
        L=None,
        fixed_angle_name="chi",
        fixed_angle=0.0,
    ):
        """Calculate scattering angles with fixed tth.

        Returns up to two solutions if they exist.

        Args:
            tth (float): Fixed scattering angle in degrees
            H, K, L (float): HKL indices (one should be None to be solved)
            fixed_angle_name (str): Name of the fixed angle ('chi' or 'phi')
            fixed_angle (float): Value of the fixed angle in degrees

        Returns:
            dict: Dictionary containing lists of solutions and metadata
        """
        a, b, c, alpha, beta, gamma = self.lab.get_lattice_parameters()
        roll, pitch, yaw = self.lab.get_lattice_angles()

        try:
            result = _calculate_angles_tth_fixed(
                self.k_in,
                tth,
                a,
                b,
                c,
                alpha,
                beta,
                gamma,
                roll,
                pitch,
                yaw,
                H,
                K,
                L,
                fixed_angle_name,
                fixed_angle,
            )
            
            # Extract data from result
            tth_list = result["tth"]
            theta_list = result["theta"]
            phi_list = result["phi"]
            chi_list = result["chi"]
            momentum = result["momentum"]
            num_solutions = result["number_of_solutions"]
            
            # Update the solved HKL component
            H_result = momentum if H is None else H
            K_result = momentum if K is None else K
            L_result = momentum if L is None else L
            
        except Exception as e:
            return {
                "success": False,
                "error": "No solution found; The Q point is possibly not reachable at this energy and/or scattering angle tth. System message:" + str(e),
            }

        # Calculate feasibility for each solution
        feasible_list = [is_feasible(theta_list[i], tth_list[i]) for i in range(len(theta_list))]

        return {
            "tth": tth_list,
            "theta": theta_list,
            "phi": phi_list,
            "chi": chi_list,
            "H": H_result,
            "K": K_result,
            "L": L_result,
            "number_of_solutions": num_solutions,
            "success": True,
            "error": None,
            "feasible": feasible_list,
        }

    def calculate_angles_tth_fixed_scan(
        self,
        tth,
        start_points,
        end_points,
        num_points,
        deactivated_index,
        fixed_angle_name="chi",
        fixed_angle=0.0,
    ):
        """Calculate scattering angles for a range of HKL values with fixed tth.

        Each HKL point may have up to 2 solutions. Results are flattened into lists
        with solution_group indicating which original HKL point each solution belongs to.

        Args:
            tth (float): Fixed scattering angle in degrees
            start_points (tuple): Starting HKL values (the deactivated index will be ignored)
            end_points (tuple): Ending HKL values (the deactivated index will be ignored)
            num_points (int): Number of points to calculate
            deactivated_index (str): Which index is deactivated ('H', 'K', or 'L')
            fixed_angle_name (str): Name of the fixed angle ('chi' or 'phi')
            fixed_angle (float): Value of the fixed angle in degrees

        Returns:
            dict: Dictionary containing lists of all calculated values
        """
        if not self.is_initialized():
            return {"success": False, "error": "Calculator not initialized"}

        if num_points < 2:
            return {"success": False, "error": "Number of points must be at least 2"}

        # Ensure we have valid inputs
        if deactivated_index not in ["H", "K", "L"]:
            return {
                "success": False,
                "error": f"Invalid deactivated index: {deactivated_index}",
            }

        if fixed_angle_name not in ["chi", "phi"]:
            return {
                "success": False,
                "error": f"Invalid fixed angle name: {fixed_angle_name}",
            }

        start_h, start_k, start_l = start_points
        end_h, end_k, end_l = end_points

        # Generate the list of points
        h_values = (
            np.linspace(start_h, end_h, num_points)
            if deactivated_index != "H"
            else [None] * num_points
        )
        k_values = (
            np.linspace(start_k, end_k, num_points)
            if deactivated_index != "K"
            else [None] * num_points
        )
        l_values = (
            np.linspace(start_l, end_l, num_points)
            if deactivated_index != "L"
            else [None] * num_points
        )

        # Initialize result lists - flattened to include all solutions
        all_tth = []
        all_theta = []
        all_phi = []
        all_chi = []
        all_h = []
        all_k = []
        all_l = []
        all_feasible = []
        all_solution_group = []  # Track which HKL point each solution belongs to
        all_solution_index = []  # Track if it's solution 1 or 2 within the group

        # Calculate for each point
        for i in range(num_points):
            h = h_values[i]
            k = k_values[i]
            l = l_values[i]

            try:
                result = self.calculate_angles_tth_fixed(
                    tth=tth,
                    H=h,
                    K=k,
                    L=l,
                    fixed_angle_name=fixed_angle_name,
                    fixed_angle=fixed_angle,
                )

                if not result.get("success", False):
                    # Skip points that fail to calculate but don't fail completely
                    continue
                
                # Each calculation returns lists of solutions
                num_solutions = result.get("number_of_solutions", 1)
                for sol_idx in range(num_solutions):
                    all_tth.append(result["tth"][sol_idx])
                    all_theta.append(result["theta"][sol_idx])
                    all_phi.append(result["phi"][sol_idx])
                    all_chi.append(result["chi"][sol_idx])
                    all_h.append(result["H"])
                    all_k.append(result["K"])
                    all_l.append(result["L"])
                    all_feasible.append(result["feasible"][sol_idx])
                    all_solution_group.append(i)  # Which HKL point
                    all_solution_index.append(sol_idx + 1)  # Solution 1 or 2
                    
            except Exception as e:
                # Log the error but continue with other points
                print(f"Error calculating point {(h, k, l)}: {str(e)}")
                continue

        # Check if we have any results
        if not all_tth:
            return {
                "success": False,
                "error": "No valid solutions found for any point in the scan",
            }
        return {
            "tth": all_tth,
            "theta": all_theta,
            "phi": all_phi,
            "chi": all_chi,
            "H": all_h,
            "K": all_k,
            "L": all_l,
            "deactivated_index": deactivated_index,
            "solution_group": all_solution_group,
            "solution_index": all_solution_index,
            "success": True,
            "error": None,
            "feasible": all_feasible,
        }
    
    
    def is_initialized(self):
        """Check if the calculator is initialized.

        Returns:
            bool: True if the calculator is initialized
        """
        return self._initialized

    def get_lattice_parameters(self):
        """Get the current lattice parameters.

        Returns:
            dict: Dictionary containing lattice parameters
        """
        a, b, c, alpha, beta, gamma = self.lab.get_lattice_parameters()
        return {
            "a": a,
            "b": b,
            "c": c,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
        }


    def get_max_hkl_values(self, tth):
        """Get the maximum HKL values, valid only for orthorhombic crystals.

        Returns:
            tuple: Maximum HKL values
        """
        if not self.is_initialized():
            raise ValueError("Calculator not initialized")
        a, b, c, alpha, beta, gamma = self.lab.get_lattice_parameters()
        k_magnitude = self.get_k_magnitude(tth)
        h_max = k_magnitude / (2 * np.pi / a)
        k_max = k_magnitude / (2 * np.pi / b)
        l_max = k_magnitude / (2 * np.pi / c)
        if alpha != 90.0 or beta != 90.0 or gamma != 90.0:
            success = False 
            message = "The crystal is not orthorhombic,\nthe accesible area is just approximate."
        else: 
            success = True
            message = None
        return {
            "h_max": h_max,
            "k_max": k_max,
            "l_max": l_max,
            "success": success,
            "message": message,
        }
        

    def get_real_space_vectors(self):
        """Get the real space vectors.

        Args:
            frame (str): "sample" or "lab"
        """
        return self.lab.get_real_space_vectors()
