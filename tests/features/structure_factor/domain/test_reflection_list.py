"""Tests for advisor.features.structure_factor.domain.reflection_list."""
import json
import os

import pytest

from advisor.features.structure_factor.domain.structure_factor_calculator import (
    StructureFactorCalculator,
)
from advisor.features.structure_factor.domain.reflection_list import (
    DEFAULT_EXTINCTION_REL_TOL,
    Reflection,
    ReflectionSnapshot,
    build_reflections,
    count_hkl_range,
    filter_extinct,
    filter_min_intensity,
    generate_hkl_range,
    serialize_to_csv,
    serialize_to_json,
)


class TestReflection:
    def test_f_magnitude(self):
        r = Reflection(h=1, k=0, l=0, f_real=3.0, f_imag=4.0)
        assert r.f_magnitude == 5.0

    def test_intensity_is_magnitude_squared(self):
        r = Reflection(h=1, k=0, l=0, f_real=3.0, f_imag=4.0)
        assert r.intensity == pytest.approx(r.f_magnitude ** 2)
        assert r.intensity == 25.0

    def test_zero_reflection(self):
        r = Reflection(h=0, k=0, l=0, f_real=0.0, f_imag=0.0)
        assert r.f_magnitude == 0.0
        assert r.intensity == 0.0

    def test_immutable(self):
        r = Reflection(h=1, k=0, l=0, f_real=1.0, f_imag=1.0)
        with pytest.raises(Exception):
            r.f_real = 2.0


class TestGenerateHklRange:
    def test_inclusive_bounds(self):
        points = generate_hkl_range((0, 1), (0, 0), (0, 0), exclude_origin=False)
        assert set(points) == {(0, 0, 0), (1, 0, 0)}

    def test_negative_bounds_supported(self):
        points = generate_hkl_range((-1, 1), (0, 0), (0, 0), exclude_origin=False)
        assert set(points) == {(-1, 0, 0), (0, 0, 0), (1, 0, 0)}

    def test_excludes_origin_by_default(self):
        points = generate_hkl_range((-1, 1), (-1, 1), (0, 0))
        assert (0, 0, 0) not in points

    def test_can_include_origin(self):
        points = generate_hkl_range((0, 0), (0, 0), (0, 0), exclude_origin=False)
        assert points == [(0, 0, 0)]

    def test_count_matches_product_of_ranges(self):
        points = generate_hkl_range((0, 2), (0, 3), (0, 1), exclude_origin=False)
        assert len(points) == 3 * 4 * 2

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError):
            generate_hkl_range((5, 0), (0, 0), (0, 0))

    def test_min_greater_than_max_raises_for_each_axis(self):
        with pytest.raises(ValueError):
            generate_hkl_range((0, 0), (5, 0), (0, 0))
        with pytest.raises(ValueError):
            generate_hkl_range((0, 0), (0, 0), (5, 0))

    def test_equivalent_to_old_full_cube_generator_when_origin_included(self):
        # Matches the shape of the _generate_hkl_cube helpers this consolidates:
        # nested H/K/L loops over an inclusive range, including the origin.
        def old_generate_hkl_cube(h_range, k_range, l_range):
            cube = []
            for h in range(h_range[0], h_range[1] + 1):
                for k in range(k_range[0], k_range[1] + 1):
                    for l in range(l_range[0], l_range[1] + 1):
                        cube.append([h, k, l])
            return cube

        old = old_generate_hkl_cube((0, 5), (0, 5), (0, 5))
        new = generate_hkl_range((0, 5), (0, 5), (0, 5), exclude_origin=False)
        assert [list(p) for p in new] == old


class TestCountHklRange:
    def test_matches_len_of_generate_hkl_range(self):
        for h_range, k_range, l_range, exclude_origin in [
            ((0, 5), (0, 5), (0, 5), False),
            ((-3, 3), (-3, 3), (-3, 3), True),
            ((0, 0), (0, 0), (0, 0), True),
            ((-1, 1), (2, 2), (-5, -2), True),
        ]:
            expected = len(generate_hkl_range(h_range, k_range, l_range, exclude_origin))
            assert count_hkl_range(h_range, k_range, l_range, exclude_origin) == expected

    def test_does_not_materialize_a_huge_list(self):
        # This would take a long time / a lot of memory if it actually built
        # the 201^3 list -- must return instantly via arithmetic only.
        import time
        start = time.monotonic()
        count = count_hkl_range((-100, 100), (-100, 100), (-100, 100), exclude_origin=True)
        elapsed = time.monotonic() - start
        assert count == 201 ** 3 - 1
        assert elapsed < 0.05

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError):
            count_hkl_range((5, 0), (0, 0), (0, 0))

    def test_exclude_origin_only_subtracts_when_origin_is_in_range(self):
        # Origin not in range -> exclude_origin has no effect on the count.
        assert count_hkl_range((1, 3), (1, 3), (1, 3), exclude_origin=True) == 3 ** 3
        assert count_hkl_range((1, 3), (1, 3), (1, 3), exclude_origin=False) == 3 ** 3


class TestBuildReflections:
    def test_zips_hkl_with_complex_values(self):
        hkl_list = [(1, 0, 0), (0, 1, 0)]
        f_values = [complex(3.0, 4.0), complex(1.0, -1.0)]
        reflections = build_reflections(hkl_list, f_values)
        assert reflections[0] == Reflection(h=1, k=0, l=0, f_real=3.0, f_imag=4.0)
        assert reflections[1] == Reflection(h=0, k=1, l=0, f_real=1.0, f_imag=-1.0)

    def test_mismatched_lengths_raises_instead_of_silently_truncating(self):
        with pytest.raises(ValueError):
            build_reflections([(1, 0, 0), (0, 1, 0)], [complex(1.0, 0.0)])


class TestReflectionSnapshot:
    def test_is_immutable(self):
        snap = ReflectionSnapshot(
            reflections=(Reflection(1, 0, 0, 1.0, 0.0),),
            f_000_magnitude=10.0,
            cif_filename="nacl.cif",
            energy_kev=10.0,
            scattering_type="xray dispersion",
        )
        with pytest.raises(Exception):
            snap.energy_kev = 20.0

    def test_holds_all_calculated_reflections_unfiltered(self):
        snap = ReflectionSnapshot(
            reflections=(Reflection(1, 0, 0, 1e-10, 0.0), Reflection(1, 1, 1, 50.0, 0.0)),
            f_000_magnitude=100.0,
            cif_filename="x.cif",
            energy_kev=10.0,
            scattering_type="xray dispersion",
        )
        assert len(snap.reflections) == 2


class TestFilterExtinct:
    def test_excludes_below_relative_threshold(self):
        reflections = [
            Reflection(1, 0, 0, f_real=1e-8, f_imag=0.0),  # numerically extinct
            Reflection(0, 1, 0, f_real=5.0, f_imag=0.0),   # real, weak
        ]
        result = filter_extinct(reflections, f_000_magnitude=100.0, rel_tol=1e-3)
        assert result == [reflections[1]]

    def test_boundary_is_inclusive(self):
        # threshold = 1e-3 * 100 = 0.1
        reflections = [Reflection(1, 0, 0, f_real=0.1, f_imag=0.0)]
        result = filter_extinct(reflections, f_000_magnitude=100.0, rel_tol=1e-3)
        assert result == reflections

    def test_all_kept_when_none_are_extinct(self):
        reflections = [Reflection(1, 0, 0, f_real=50.0, f_imag=0.0)]
        result = filter_extinct(reflections, f_000_magnitude=100.0, rel_tol=1e-3)
        assert result == reflections


class TestFilterMinIntensity:
    def test_independent_of_extinction_filter(self):
        reflections = [
            Reflection(1, 0, 0, f_real=1.0, f_imag=0.0),   # intensity 1
            Reflection(0, 1, 0, f_real=10.0, f_imag=0.0),  # intensity 100
        ]
        # A weak-but-nonzero reflection survives extinction filtering...
        assert filter_extinct(reflections, f_000_magnitude=1000.0, rel_tol=1e-3) == reflections
        # ...but can still be removed by a separate minimum-intensity filter.
        result = filter_min_intensity(reflections, min_intensity=50.0)
        assert result == [reflections[1]]


class TestSerializeToCsv:
    def test_header_and_columns(self):
        reflections = [Reflection(1, 2, 3, f_real=1.5, f_imag=-2.5)]
        csv_text = serialize_to_csv(reflections, {"energy_kev": 10.0})
        lines = csv_text.strip().splitlines()
        assert lines[0] == "h,k,l,f_real,f_imag,f_magnitude,intensity,energy_kev"
        row = lines[1].split(",")
        assert row[0:3] == ["1", "2", "3"]
        assert row[-1] == "10.0"

    def test_full_precision_not_rounded(self):
        reflections = [Reflection(0, 0, 0, f_real=1.0 / 3.0, f_imag=0.0)]
        csv_text = serialize_to_csv(reflections, {})
        assert "0.3333333333333333" in csv_text


FCC_TEST_CIF = os.path.join(os.path.dirname(__file__), "fixtures", "fcc_test.cif")


class TestFilterExtinctAgainstRealFCenteredStructure:
    """DEFAULT_EXTINCTION_REL_TOL, validated against a genuine systematic
    absence rather than only synthetic numbers.

    fcc_test.cif places 4 identical atoms at the face-centering positions,
    so every mixed-parity HKL is a true F-centering systematic absence
    (|F| limited only by floating-point noise), and every all-even/all-odd
    HKL is a real, strong allowed reflection.
    """

    @pytest.fixture
    def calculator(self):
        calc = StructureFactorCalculator()
        calc.initialize(cif_file_path=FCC_TEST_CIF, energy=10000.0)
        return calc

    def test_default_tolerance_separates_absences_from_allowed_reflections(self, calculator):
        f_000 = abs(calculator.calculate_structure_factors([[0, 0, 0]])[0])

        mixed_parity = [(1, 0, 0), (3, 0, 0), (1, 1, 0), (2, 1, 0)]  # systematic absences
        allowed = [(1, 1, 1), (2, 0, 0), (2, 2, 0), (3, 1, 1)]       # real reflections

        f_values = calculator.calculate_structure_factors(
            [list(h) for h in mixed_parity + allowed]
        )
        reflections = build_reflections(mixed_parity + allowed, f_values)

        filtered = filter_extinct(reflections, f_000, rel_tol=DEFAULT_EXTINCTION_REL_TOL)
        filtered_hkls = {(r.h, r.k, r.l) for r in filtered}

        assert filtered_hkls == set(allowed)
        for hkl in mixed_parity:
            assert hkl not in filtered_hkls

    def test_true_extinctions_are_many_orders_of_magnitude_below_default_threshold(self, calculator):
        """Confirms the default has large margin above real numerical noise,
        not just above hand-picked synthetic test values."""
        f_000 = abs(calculator.calculate_structure_factors([[0, 0, 0]])[0])
        f_100 = abs(calculator.calculate_structure_factors([[1, 0, 0]])[0])
        assert f_100 / f_000 < DEFAULT_EXTINCTION_REL_TOL / 100


class TestSerializeToJson:
    def test_schema_shape(self):
        reflections = [Reflection(1, 1, 1, f_real=2.0, f_imag=1.0)]
        metadata = {"cif_filename": "nacl.cif", "energy_kev": 10.0}
        payload = json.loads(serialize_to_json(reflections, metadata))
        assert payload["metadata"] == metadata
        assert len(payload["reflections"]) == 1
        entry = payload["reflections"][0]
        assert entry["h"] == 1 and entry["k"] == 1 and entry["l"] == 1
        assert entry["f_real"] == 2.0
        assert entry["f_imag"] == 1.0
        assert entry["f_magnitude"] == pytest.approx((2.0 ** 2 + 1.0 ** 2) ** 0.5)
        assert entry["intensity"] == pytest.approx(5.0)

    def test_complex_serialized_as_separate_fields_not_a_string(self):
        reflections = [Reflection(0, 0, 0, f_real=1.0, f_imag=2.0)]
        payload = json.loads(serialize_to_json(reflections, {}))
        entry = payload["reflections"][0]
        assert isinstance(entry["f_real"], float)
        assert isinstance(entry["f_imag"], float)
