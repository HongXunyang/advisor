"""Verifies the bundled "Try an example" CIF resolves independent of cwd and
produces real, finite geometry + structure-factor results -- REQUIREMENT_2:
"Check actual geometry and finite structure-factor output at a documented
suitable test energy. Do not choose a demonstration merely because parsing
succeeds."
"""

import os

import numpy as np
import pytest

from advisor.controllers.cif_import_service import CifImportService
from advisor.domain.library.bundled_examples import (
    EXAMPLES,
    find_example_by_content_hash,
    get_bundled_example,
    resource_absolute_path,
)
from advisor.domain.cif_import import io as cif_io


def test_exactly_one_example_ships():
    assert len(EXAMPLES) == 1


def test_resource_resolves_independent_of_cwd(tmp_path, monkeypatch):
    example = EXAMPLES[0]
    absolute_path = resource_absolute_path(example)
    assert os.path.isabs(absolute_path)
    assert os.path.exists(absolute_path)

    # Resolution must not depend on the process cwd.
    monkeypatch.chdir(tmp_path)
    assert resource_absolute_path(example) == absolute_path
    assert os.path.exists(resource_absolute_path(example))


def test_get_bundled_example_by_key():
    example = get_bundled_example("idealized_rock_salt")
    assert example.key == "idealized_rock_salt"
    with pytest.raises(KeyError):
        get_bundled_example("does-not-exist")


def test_example_carries_no_fabricated_provenance():
    example = EXAMPLES[0]
    assert "idealized" in example.citation.lower()
    # Must not reuse/relabel the load-bearing nacl.cif scientific fixture.
    assert "nacl.cif" not in example.resource_relpath


def test_example_never_reuses_nacl_cif_path():
    example = EXAMPLES[0]
    nacl_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "advisor", "resources", "data", "nacl.cif")
    )
    assert resource_absolute_path(example) != nacl_path


def test_find_example_by_content_hash_roundtrip():
    example = EXAMPLES[0]
    with open(resource_absolute_path(example), "rb") as handle:
        digest = cif_io.content_digest(handle.read())
    found = find_example_by_content_hash(digest)
    assert found is not None
    assert found.key == example.key


def test_find_example_by_content_hash_no_match_returns_none():
    assert find_example_by_content_hash("0" * 64) is None


def test_example_imports_ready_through_real_pipeline():
    example = EXAMPLES[0]
    service = CifImportService()
    result = service.prepare_from_path(resource_absolute_path(example))
    try:
        assert result.status == "ready"
        assert result.source.capabilities.structure_factor_ok is True
        assert result.source.formula
    finally:
        if result.source is not None:
            cif_io.cleanup_snapshot(result.source.effective_path)


def test_example_geometry_initializes_at_documented_energy():
    from advisor.features.scattering_geometry.domain import BrillouinCalculator

    example = EXAMPLES[0]
    service = CifImportService()
    result = service.prepare_from_path(resource_absolute_path(example))
    try:
        source = result.source
        calc = BrillouinCalculator()
        calc.initialize({
            "a": source.a, "b": source.b, "c": source.c,
            "alpha": source.alpha, "beta": source.beta, "gamma": source.gamma,
            "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
            "energy": example.test_energy_ev,
        })
        assert calc.is_initialized()
    finally:
        cif_io.cleanup_snapshot(result.source.effective_path)


def test_example_structure_factor_finite_and_nonzero_for_allowed_reflection():
    """(1,1,1) and (2,0,0) are F-centering-allowed (all-odd/all-even) for
    this rock-salt structure -- a real, non-extinct, finite reflection a
    user would actually see, not merely "parses without error"."""
    from advisor.features.structure_factor.domain.structure_factor_calculator import (
        StructureFactorCalculator,
    )

    example = EXAMPLES[0]
    service = CifImportService()
    result = service.prepare_from_path(resource_absolute_path(example))
    try:
        calculator = StructureFactorCalculator()
        calculator.initialize(cif_file_path=result.source.effective_path, energy=example.test_energy_ev)
        f_values = calculator.calculate_structure_factors(hkl_input_list=[[1, 1, 1], [2, 0, 0]])
        for f in f_values:
            assert np.isfinite(f)
            assert abs(f) > 1e-6
    finally:
        cif_io.cleanup_snapshot(result.source.effective_path)
