"""Conservative search-text normalization for the local structure library.

Deliberately not a chemical search engine: this exists solely so an
ordinary typed formula like "SiO2" matches a displayed formula like "SiO2"
rendered with Unicode subscripts ("SiO₂"). No element-order canonicalization,
no synonym table, no fuzzy matching.
"""

_SUBSCRIPT_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def normalize_search_text(text: str) -> str:
    """Casefold + map Unicode subscript digits to their ASCII equivalents.

    Applied identically to both stored searchable text and the user's query,
    so comparison is a plain substring check on normalized strings.
    """
    if not text:
        return ""
    return text.translate(_SUBSCRIPT_DIGITS).casefold()
