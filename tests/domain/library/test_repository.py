"""Pure-Python tests for `LibraryRepository` -- no Qt, injected clock and
`tmp_path` storage root per REQUIREMENT_2's "injectable storage root and
clock for deterministic tests" requirement."""

import os
import sqlite3

import pytest

from advisor.domain.library.repository import LibraryRepository
from advisor.domain.library.types import LibraryCorruptionDetected, LibraryUnavailableError


def _metadata(**overrides):
    base = {
        "formula": "Na4 Cl4", "space_group": "F m -3 m",
        "cell_a": 5.6402, "cell_b": 5.6402, "cell_c": 5.6402,
        "cell_alpha": 90.0, "cell_beta": 90.0, "cell_gamma": 90.0,
        "source_id": None, "doi": None, "temperature_k": None, "pressure_kpa": None,
        "geometry_ok": True, "structure_factor_ok": True,
        "capability_message": "Ready for geometry and structure factors.",
    }
    base.update(overrides)
    return base


class FakeClock:
    def __init__(self, start=1_000_000.0):
        self._now = start

    def __call__(self):
        return self._now

    def advance(self, seconds):
        self._now += seconds


def test_upsert_new_record_then_reimport_updates_last_used_preserves_edits(tmp_path):
    clock = FakeClock()
    repo = LibraryRepository(str(tmp_path), clock=clock)

    record = repo.upsert_accepted(
        content_hash="abc123", data_block=None,
        managed_relative_path="cif_files/ab/abc123.cif",
        original_filename="sample.cif", source_origin="import",
        metadata=_metadata(),
    )
    assert record.display_name is None
    assert record.note is None
    assert record.starred is False
    first_imported_at = record.imported_at

    repo.set_starred(record.id, True)
    repo.rename(record.id, "My sample")
    repo.set_note(record.id, "grown in-house")

    clock.advance(120)
    reimported = repo.upsert_accepted(
        content_hash="abc123", data_block=None,
        managed_relative_path="cif_files/ab/abc123.cif",
        original_filename="sample.cif", source_origin="import",
        metadata=_metadata(space_group="Updated"),
    )

    assert reimported.id == record.id
    assert reimported.starred is True
    assert reimported.display_name == "My sample"
    assert reimported.note == "grown in-house"
    assert reimported.imported_at == first_imported_at
    assert reimported.last_used_at > first_imported_at
    assert reimported.space_group == "Updated"  # extracted metadata refreshed


def test_edited_bytes_at_same_identity_are_a_distinct_record(tmp_path):
    repo = LibraryRepository(str(tmp_path))
    original = repo.upsert_accepted(
        content_hash="hash-a", data_block=None,
        managed_relative_path="cif_files/ha/hash-a.cif",
        original_filename="sample.cif", source_origin="import", metadata=_metadata(),
    )
    edited = repo.upsert_accepted(
        content_hash="hash-b", data_block=None,
        managed_relative_path="cif_files/hb/hash-b.cif",
        original_filename="sample.cif", source_origin="import", metadata=_metadata(),
    )
    assert original.id != edited.id
    assert len(repo.list_all()) == 2


def test_same_formula_different_content_are_distinct_records(tmp_path):
    repo = LibraryRepository(str(tmp_path))
    repo.upsert_accepted(
        content_hash="quartz-ambient", data_block=None,
        managed_relative_path="cif_files/qa/quartz-ambient.cif",
        original_filename="quartz_ambient.cif", source_origin="import",
        metadata=_metadata(formula="Si O2", temperature_k=298.0),
    )
    repo.upsert_accepted(
        content_hash="quartz-hp", data_block=None,
        managed_relative_path="cif_files/qh/quartz-hp.cif",
        original_filename="quartz_hp.cif", source_origin="import",
        metadata=_metadata(formula="Si O2", temperature_k=298.0, pressure_kpa=12_000_000.0),
    )
    records = repo.list_all()
    assert len(records) == 2
    assert {r.content_hash for r in records} == {"quartz-ambient", "quartz-hp"}


def test_recent_starred_all_ordering(tmp_path):
    clock = FakeClock()
    repo = LibraryRepository(str(tmp_path), clock=clock)
    ids = []
    for i in range(3):
        record = repo.upsert_accepted(
            content_hash=f"h{i}", data_block=None,
            managed_relative_path=f"cif_files/h/h{i}.cif",
            original_filename=f"f{i}.cif", source_origin="import", metadata=_metadata(),
        )
        ids.append(record.id)
        clock.advance(10)

    repo.set_starred(ids[1], True)

    recent = repo.list_recent(limit=10)
    assert [r.id for r in recent] == list(reversed(ids))  # most recently used first

    starred = repo.list_starred()
    assert [r.id for r in starred] == [ids[1]]

    all_records = repo.list_all()
    assert len(all_records) == 3


def test_recent_limit_is_a_display_limit_not_a_deletion(tmp_path):
    repo = LibraryRepository(str(tmp_path))
    for i in range(15):
        repo.upsert_accepted(
            content_hash=f"h{i}", data_block=None,
            managed_relative_path=f"cif_files/h/h{i}.cif",
            original_filename=f"f{i}.cif", source_origin="import", metadata=_metadata(),
        )
    assert len(repo.list_recent(limit=10)) == 10
    assert len(repo.list_all()) == 15


def test_remove_deletes_row_only_repository_does_not_touch_filesystem(tmp_path):
    repo = LibraryRepository(str(tmp_path))
    record = repo.upsert_accepted(
        content_hash="h1", data_block=None,
        managed_relative_path="cif_files/h/h1.cif",
        original_filename="f.cif", source_origin="import", metadata=_metadata(),
    )
    removed = repo.remove(record.id)
    assert removed.id == record.id
    assert repo.get(record.id) is None
    assert repo.remove(record.id) is None  # already gone -- no error


def test_preferences_default_and_persist(tmp_path):
    repo = LibraryRepository(str(tmp_path))
    assert repo.get_preference("remember_imports_enabled", "1") == "1"
    repo.set_preference("remember_imports_enabled", "0")
    assert repo.get_preference("remember_imports_enabled", "1") == "0"


def test_reopening_same_root_survives_restart(tmp_path):
    repo1 = LibraryRepository(str(tmp_path))
    record = repo1.upsert_accepted(
        content_hash="h1", data_block=None,
        managed_relative_path="cif_files/h/h1.cif",
        original_filename="f.cif", source_origin="import", metadata=_metadata(),
    )
    repo1.set_starred(record.id, True)
    repo1.close()

    repo2 = LibraryRepository(str(tmp_path))  # simulates app restart
    restored = repo2.get(record.id)
    assert restored is not None
    assert restored.starred is True


def test_corrupted_database_file_is_never_recreated(tmp_path):
    db_path = tmp_path / "library.db"
    db_path.write_bytes(b"not a sqlite database at all")

    with pytest.raises(LibraryCorruptionDetected):
        LibraryRepository(str(tmp_path))

    # The bogus file must still be exactly what it was -- never silently
    # deleted/recreated as an empty library.
    assert db_path.read_bytes() == b"not a sqlite database at all"


def test_unknown_newer_schema_version_is_not_destroyed(tmp_path):
    db_path = tmp_path / "library.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO schema_meta (key, value) VALUES ('schema_version', '999')")
    conn.commit()
    conn.close()

    with pytest.raises(LibraryCorruptionDetected):
        LibraryRepository(str(tmp_path))

    # File must be untouched, not dropped/recreated at the current version.
    conn = sqlite3.connect(str(db_path))
    version = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()[0]
    conn.close()
    assert version == "999"


def test_root_that_is_an_existing_file_does_not_crash_but_raises_actionable_error(tmp_path):
    """REVIEW.md finding #1: a storage root that's actually a file must not
    surface a raw, unhandled `FileExistsError` from `os.makedirs()`."""
    blocked_path = tmp_path / "blocked"
    blocked_path.write_text("this is a file, not a directory")

    with pytest.raises(LibraryUnavailableError):
        LibraryRepository(str(blocked_path))


def test_malformed_schema_version_text_does_not_crash_but_raises_actionable_error(tmp_path):
    """REVIEW.md finding #1: `schema_version='not-an-int'` must not surface
    a raw, unhandled `ValueError`."""
    db_path = tmp_path / "library.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO schema_meta (key, value) VALUES ('schema_version', 'not-an-int')")
    conn.commit()
    conn.close()

    with pytest.raises(LibraryCorruptionDetected):
        LibraryRepository(str(tmp_path))


def test_recognized_schema_version_without_expected_tables_is_detected(tmp_path):
    """REVIEW.md finding #1: a valid schema_version row with no `structures`
    table must be caught at open time, not surfaced later as a raw
    `sqlite3.OperationalError: no such table` from `list_all()`."""
    db_path = tmp_path / "library.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO schema_meta (key, value) VALUES ('schema_version', '1')")
    conn.commit()
    conn.close()

    with pytest.raises(LibraryCorruptionDetected):
        LibraryRepository(str(tmp_path))


def test_null_data_block_identity_is_still_rejected_by_the_database_itself(tmp_path):
    """REVIEW.md finding #5: SQL treats every NULL as distinct from every
    other NULL, so a plain `UNIQUE(content_hash, data_block)` column
    constraint does not dedupe two rows that both have `data_block IS NULL`
    (the identity of any accepted CIF with no `data_...` header at all).
    This bypasses the raw `sqlite3` connection to prove the DATABASE's own
    constraint (a COALESCE-based unique index) rejects the duplicate, not
    just the application-level find-then-insert check in `upsert_accepted`.
    """
    repo = LibraryRepository(str(tmp_path))
    repo.upsert_accepted(
        content_hash="headerless", data_block=None,
        managed_relative_path="cif_files/he/headerless.cif",
        original_filename="headerless.cif", source_origin="import", metadata=_metadata(),
    )
    with pytest.raises(sqlite3.IntegrityError):
        repo._conn.execute(
            "INSERT INTO structures "
            "(id, content_hash, data_block, managed_relative_path, original_filename, "
            "starred, imported_at, last_used_at, source_origin, schema_version) "
            "VALUES ('dup-id', 'headerless', NULL, 'cif_files/he/headerless.cif', "
            "'headerless.cif', 0, 1.0, 1.0, 'import', 1)"
        )


def test_two_repository_instances_racing_on_identical_new_content_produce_one_row(tmp_path):
    """Simulates two ADVISOR instances both importing the same new CIF at
    once: repo1 wins the insert; repo2's upsert (racing against the same
    identity) must land on the same row via the UNIQUE-constraint retry
    path, not raise or create a duplicate."""
    repo1 = LibraryRepository(str(tmp_path))
    repo2 = LibraryRepository(str(tmp_path))

    first = repo1.upsert_accepted(
        content_hash="shared", data_block=None,
        managed_relative_path="cif_files/sh/shared.cif",
        original_filename="shared.cif", source_origin="import", metadata=_metadata(),
    )
    second = repo2.upsert_accepted(
        content_hash="shared", data_block=None,
        managed_relative_path="cif_files/sh/shared.cif",
        original_filename="shared.cif", source_origin="import", metadata=_metadata(),
    )
    assert first.id == second.id
    assert len(repo1.list_all()) == 1
