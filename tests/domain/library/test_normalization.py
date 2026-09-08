from advisor.domain.library.normalization import normalize_search_text


def test_subscript_digits_normalize_to_ascii():
    assert normalize_search_text("SiO₂") == normalize_search_text("SiO2")


def test_case_insensitive():
    assert normalize_search_text("Quartz") == normalize_search_text("quartz")


def test_typed_formula_matches_subscript_display_formula():
    query = normalize_search_text("SiO2")
    haystack = normalize_search_text("Formula: SiO₂, ambient")
    assert query in haystack


def test_empty_string_normalizes_to_empty():
    assert normalize_search_text("") == ""
    assert normalize_search_text(None) == ""
