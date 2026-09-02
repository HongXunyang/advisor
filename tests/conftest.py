"""Shared fixtures for all tests."""
import numpy as np
import pytest

# =============================================================================
# Lattice Configuration Registry
# =============================================================================
BEAM_CONFIGS = {
    "energy": 930.0,
    "k_in": 2 * np.pi /  12398.42 * 930,
    "lambda_A": 12398.42 / 930.0,
}
LATTICE_CONFIGS = {
    "cubic": {
        "a": 4.0, "b": 4.0, "c": 4.0,
        "alpha": 90.0, "beta": 90.0, "gamma": 90.0,
        "a_star": 2*np.pi/4.0, "b_star": 2*np.pi/4.0, "c_star": 2*np.pi/4.0,
    },
    "tetragonal": {
        "a": 4.0, "b": 4.0, "c": 12.0,
        "alpha": 90.0, "beta": 90.0, "gamma": 90.0,
        "a_star": 2*np.pi/4.0, "b_star": 2*np.pi/4.0, "c_star": 2*np.pi/12.0,
    },
    "orthorhombic": {
        "a": 3.0, "b": 4.0, "c": 5.0,
        "alpha": 90.0, "beta": 90.0, "gamma": 90.0,
        "a_star": 2*np.pi/3.0, "b_star": 2*np.pi/4.0, "c_star": 2*np.pi/5.0,
    },
    "hexagonal": {
        "a": 4.0, "b": 4.0, "c": 6.0,
        "alpha": 90.0, "beta": 90.0, "gamma": 120.0,
    },
    "monoclinic": {
        "a": 3.0, "b": 4.0, "c": 5.0,
        "alpha": 90.0, "beta": 100.0, "gamma": 90.0,
    },
    "triclinic": {
        "a": 3.0, "b": 4.0, "c": 5.0,
        "alpha": 80.0, "beta": 85.0, "gamma": 70.0,
    },
}

# List of all available crystal types for parametrization
ALL_CRYSTAL_TYPES = list(LATTICE_CONFIGS.keys())


# =============================================================================
# Individual Lattice Fixtures (for backwards compatibility)
# =============================================================================
@pytest.fixture
def cubic_lattice_params():
    """Simple cubic lattice parameters (a=b=c, 90° angles)."""
    return LATTICE_CONFIGS["cubic"].copy()


@pytest.fixture
def tetragonal_lattice_params():
    """Tetragonal lattice parameters (a=b≠c, 90° angles)."""
    return LATTICE_CONFIGS["tetragonal"].copy()


@pytest.fixture
def orthorhombic_lattice_params():
    """Orthorhombic lattice parameters (a≠b≠c, 90° angles)."""
    return LATTICE_CONFIGS["orthorhombic"].copy()


@pytest.fixture
def hexagonal_lattice_params():
    """Hexagonal lattice parameters (a=b≠c, γ=120°)."""
    return LATTICE_CONFIGS["hexagonal"].copy()


@pytest.fixture
def monoclinic_lattice_params():
    """Monoclinic lattice parameters (a≠b≠c, β≠90°)."""
    return LATTICE_CONFIGS["monoclinic"].copy()


@pytest.fixture
def triclinic_lattice_params():
    """Triclinic lattice parameters (a≠b≠c, α≠β≠γ≠90°)."""
    return LATTICE_CONFIGS["triclinic"].copy()


# =============================================================================
# Common Fixtures
# =============================================================================
@pytest.fixture
def no_rotation_euler():
    """No lattice rotation (identity)."""
    return {
        "roll": 0.0,
        "pitch": 0.0,
        "yaw": 0.0,
    }

ev_to_lambda = 12398.42

@pytest.fixture
def standard_energy():
    """Standard X-ray energy in eV."""
    return BEAM_CONFIGS["energy"]  # eV


# =============================================================================
# Calculator Fixtures
# =============================================================================
@pytest.fixture
def calculator_params(tetragonal_lattice_params, no_rotation_euler, standard_energy):
    """Complete parameter set for initializing calculator (tetragonal by default)."""
    return {
        **tetragonal_lattice_params,
        **no_rotation_euler,
        "energy": standard_energy,
    }


@pytest.fixture
def initialized_calculator(calculator_params):
    """Pre-initialized BrillouinCalculator instance (tetragonal by default)."""
    from advisor.features.scattering_geometry.domain import BrillouinCalculator
    
    calc = BrillouinCalculator()
    calc.initialize(calculator_params)
    return calc


# =============================================================================
# UB-matrix / orientation-fitting test helpers
# =============================================================================
def consistent_diffraction_row(lattice_params, H, K, L, energy, theta=0.0, phi=0.0, chi=0.0):
    """Build a diffraction-test row dict whose tth is computed so that the
    reciprocal-vector magnitude |B.(H,K,L)| matches the observed scattering
    vector magnitude at the given energy -- i.e. a row that could plausibly
    correspond to SOME orientation, distinct from a hand-picked arbitrary
    tth that would fail the magnitude-consistency validation check.

    theta/phi/chi don't affect the vector's magnitude (only its direction),
    so they can still be chosen freely by the caller.
    """
    from advisor.domain.geometry import energy_to_k_in, get_reciprocal_space_vectors

    a_star, b_star, c_star = get_reciprocal_space_vectors(
        lattice_params["a"], lattice_params["b"], lattice_params["c"],
        lattice_params["alpha"], lattice_params["beta"], lattice_params["gamma"],
    )
    g = H * a_star + K * b_star + L * c_star
    k_in = energy_to_k_in(energy)
    ratio = np.linalg.norm(g) / (2 * k_in)
    if abs(ratio) > 1.0:
        raise ValueError(
            f"HKL=({H},{K},{L}) is not reachable at energy={energy} eV for this lattice "
            f"(|Q| required = {np.linalg.norm(g):.4f}, max reachable = {2 * k_in:.4f}); "
            "use a higher energy or smaller HKL in the test."
        )
    tth = 2 * np.degrees(np.arcsin(ratio))
    return {"H": H, "K": K, "L": L, "energy": energy, "tth": tth, "theta": theta, "phi": phi, "chi": chi}


@pytest.fixture
def make_calculator(no_rotation_euler, standard_energy):
    """
    Factory fixture to create calculators with any crystal type.
    
    Usage:
        def test_something(make_calculator):
            calc = make_calculator("cubic")
            # or with custom energy:
            calc = make_calculator("hexagonal", energy=1000.0)
            # or loop through all types:
            for crystal_type in ALL_CRYSTAL_TYPES:
                calc = make_calculator(crystal_type)
    """
    from advisor.features.scattering_geometry.domain import BrillouinCalculator
    
    def _make(lattice_type="tetragonal", energy=None, euler_angles=None):
        """
        Create an initialized calculator.
        
        Args:
            lattice_type: One of the keys in LATTICE_CONFIGS
            energy: Override the standard energy (default: 930.0 eV)
            euler_angles: Override rotation angles (default: no rotation)
        
        Returns:
            Initialized BrillouinCalculator instance
        """
        if lattice_type not in LATTICE_CONFIGS:
            raise ValueError(
                f"Unknown lattice type: {lattice_type}. "
                f"Available: {list(LATTICE_CONFIGS.keys())}"
            )
        
        params = {
            **LATTICE_CONFIGS[lattice_type],
            **(euler_angles or no_rotation_euler),
            "energy": energy if energy is not None else standard_energy,
        }
        
        calc = BrillouinCalculator()
        calc.initialize(params)
        return calc
    
    return _make
