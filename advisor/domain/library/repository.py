"""SQLite-backed storage for the local structure library.

Pure Python (stdlib `sqlite3` only, no PyQt) so this is fully unit-testable
with a `tmp_path` root and an injected clock -- see `CLAUDE.md`/REQUIREMENT_2's
"injectable storage root and clock for deterministic tests."

Concurrency: `journal_mode=WAL` + `busy_timeout` let two ADVISOR instances
share one `library.db` without corrupting it or losing writes. A unique index
on `(content_hash, COALESCE(data_block, ''))` -- not a plain
`UNIQUE(content_hash, data_block)` column constraint, which SQL would not
enforce for two rows that both have `data_block IS NULL` -- is the hard
backstop against a race between two processes both inserting the same new
content at once -- the loser of that race gets `sqlite3.IntegrityError` and
retries as an update, exactly as if it had seen the winner's row from the
start.

Corruption/schema recovery: a failed `PRAGMA integrity_check`, an
unrecognized `schema_version`, a missing expected table, or a filesystem
error creating the storage root all raise `LibraryUnavailableError`/
`LibraryCorruptionDetected` rather than deleting/recreating the database file
or crashing application startup -- existing records are never destroyed just
because this session couldn't make sense of them.
"""

import os
import sqlite3
import time
import uuid
from typing import Callable, List, Optional

from .types import LibraryCorruptionDetected, LibraryRecord, LibraryUnavailableError

_SCHEMA_VERSION = 1

_METADATA_COLUMNS = (
    "formula", "space_group",
    "cell_a", "cell_b", "cell_c", "cell_alpha", "cell_beta", "cell_gamma",
    "source_id", "doi", "temperature_k", "pressure_kpa",
    "geometry_ok", "structure_factor_ok", "capability_message",
)

_RECORD_COLUMNS = (
    "id", "content_hash", "data_block", "managed_relative_path", "original_filename",
    "display_name", "note", "starred", "imported_at", "last_used_at", "source_origin",
) + _METADATA_COLUMNS + ("schema_version",)


def _row_to_record(row: sqlite3.Row) -> LibraryRecord:
    return LibraryRecord(
        id=row["id"],
        content_hash=row["content_hash"],
        data_block=row["data_block"],
        managed_relative_path=row["managed_relative_path"],
        original_filename=row["original_filename"],
        display_name=row["display_name"],
        note=row["note"],
        starred=bool(row["starred"]),
        imported_at=row["imported_at"],
        last_used_at=row["last_used_at"],
        source_origin=row["source_origin"],
        formula=row["formula"],
        space_group=row["space_group"],
        cell_a=row["cell_a"], cell_b=row["cell_b"], cell_c=row["cell_c"],
        cell_alpha=row["cell_alpha"], cell_beta=row["cell_beta"], cell_gamma=row["cell_gamma"],
        source_id=row["source_id"],
        doi=row["doi"],
        temperature_k=row["temperature_k"],
        pressure_kpa=row["pressure_kpa"],
        geometry_ok=None if row["geometry_ok"] is None else bool(row["geometry_ok"]),
        structure_factor_ok=None if row["structure_factor_ok"] is None else bool(row["structure_factor_ok"]),
        capability_message=row["capability_message"],
        schema_version=row["schema_version"],
    )


class LibraryRepository:
    """One connection to one `<root_dir>/library.db`."""

    def __init__(self, root_dir: str, clock: Callable[[], float] = time.time):
        self._root_dir = root_dir
        self._clock = clock

        try:
            os.makedirs(root_dir, exist_ok=True)
        except OSError as exc:
            raise LibraryUnavailableError(
                f"Could not create the local structure library folder at '{root_dir}': {exc}"
            ) from exc

        db_path = os.path.join(root_dir, "library.db")
        conn = None
        try:
            conn = sqlite3.connect(db_path, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            self._conn = conn
            self._ensure_schema()
        except LibraryUnavailableError:
            if conn is not None:
                conn.close()
            raise
        except (sqlite3.Error, ValueError, OSError) as exc:
            if conn is not None:
                conn.close()
            raise LibraryCorruptionDetected(
                f"Your local structure library ({os.path.basename(db_path)}) could not be "
                f"opened: {exc}. Existing saved structures are safe but unavailable this session."
            ) from exc

    def close(self):
        self._conn.close()

    # -- schema -----------------------------------------------------------

    def _ensure_schema(self):
        conn = self._conn
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()

        if row is None:
            self._create_tables()
            conn.execute(
                "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?)",
                (str(_SCHEMA_VERSION),),
            )
            return

        version = int(row["value"])
        if version > _SCHEMA_VERSION:
            raise LibraryCorruptionDetected(
                f"This library was created by a newer version of ADVISOR "
                f"(schema version {version}, this version supports up to "
                f"{_SCHEMA_VERSION}). It has not been modified."
            )
        # No migrations exist yet below the current version -- this is
        # where a `MIGRATIONS[version:]` sequence would run in the future.

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise LibraryCorruptionDetected(
                f"The local structure library failed an integrity check ({integrity})."
            )

        # A recognized, up-to-date schema_version alone doesn't prove the
        # expected tables actually exist (e.g. a hand-edited or partially
        # migrated database could carry a valid version marker with nothing
        # else in it) -- `PRAGMA integrity_check` above only checks internal
        # consistency of whatever pages exist, not that the schema this code
        # expects is present. Verify explicitly rather than letting a later
        # `list_all()`/etc. fail with a raw, unhandled `sqlite3.OperationalError`.
        existing_tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        missing = {"structures", "preferences"} - existing_tables
        if missing:
            raise LibraryCorruptionDetected(
                f"The local structure library is missing expected data "
                f"({', '.join(sorted(missing))}) despite a recognized schema version."
            )

    def _create_tables(self):
        conn = self._conn
        conn.execute(
            "CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS structures (
                id TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                data_block TEXT,
                managed_relative_path TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                display_name TEXT,
                note TEXT,
                starred INTEGER NOT NULL DEFAULT 0,
                imported_at REAL NOT NULL,
                last_used_at REAL NOT NULL,
                source_origin TEXT NOT NULL DEFAULT 'import',
                formula TEXT,
                space_group TEXT,
                cell_a REAL, cell_b REAL, cell_c REAL,
                cell_alpha REAL, cell_beta REAL, cell_gamma REAL,
                source_id TEXT,
                doi TEXT,
                temperature_k REAL,
                pressure_kpa REAL,
                geometry_ok INTEGER,
                structure_factor_ok INTEGER,
                capability_message TEXT,
                schema_version INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        # A plain `UNIQUE(content_hash, data_block)` table constraint does
        # NOT dedupe two rows that both have `data_block IS NULL` -- SQL
        # treats every NULL as distinct from every other NULL for uniqueness
        # purposes. `data_block` is NULL for any accepted CIF that has no
        # `data_...` header at all (the importer tolerates this), so two
        # concurrent imports of the same headerless content could otherwise
        # both insert successfully. COALESCE-ing NULL to '' inside a unique
        # INDEX (rather than a column constraint) makes the identity check
        # NULL-safe at the database level, not just in application code.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_structures_identity "
            "ON structures(content_hash, COALESCE(data_block, ''))"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_structures_last_used ON structures(last_used_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_structures_starred ON structures(starred)"
        )

    # -- preferences --------------------------------------------------------

    def get_preference(self, key: str, default: str) -> str:
        row = self._conn.execute(
            "SELECT value FROM preferences WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row is not None else default

    def set_preference(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO preferences (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    # -- structures ---------------------------------------------------------

    def get(self, record_id: str) -> Optional[LibraryRecord]:
        row = self._conn.execute(
            "SELECT * FROM structures WHERE id=?", (record_id,)
        ).fetchone()
        return _row_to_record(row) if row is not None else None

    def find_by_identity(self, content_hash: str, data_block: Optional[str]) -> Optional[LibraryRecord]:
        row = self._conn.execute(
            "SELECT * FROM structures WHERE content_hash=? AND data_block IS ?",
            (content_hash, data_block),
        ).fetchone()
        return _row_to_record(row) if row is not None else None

    def list_recent(self, limit: int = 10) -> List[LibraryRecord]:
        rows = self._conn.execute(
            "SELECT * FROM structures ORDER BY last_used_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def list_starred(self) -> List[LibraryRecord]:
        rows = self._conn.execute(
            "SELECT * FROM structures WHERE starred=1 ORDER BY last_used_at DESC"
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def list_all(self) -> List[LibraryRecord]:
        rows = self._conn.execute(
            "SELECT * FROM structures ORDER BY last_used_at DESC"
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def upsert_accepted(
        self,
        *,
        content_hash: str,
        data_block: Optional[str],
        managed_relative_path: str,
        original_filename: str,
        source_origin: str,
        metadata: dict,
    ) -> LibraryRecord:
        """Insert a new record, or refresh `last_used_at` + extracted
        metadata on an existing one -- never touches `display_name`/`note`/
        `starred`/`original_filename` on an existing record.
        """
        metadata_values = tuple(metadata.get(col) for col in _METADATA_COLUMNS)
        now = self._clock()
        conn = self._conn

        for attempt in range(2):
            existing = self.find_by_identity(content_hash, data_block)
            if existing is not None:
                conn.execute(
                    f"""UPDATE structures SET last_used_at=?,
                        {", ".join(f"{col}=?" for col in _METADATA_COLUMNS)}
                        WHERE id=?""",
                    (now, *metadata_values, existing.id),
                )
                return self.get(existing.id)

            record_id = uuid.uuid4().hex
            try:
                conn.execute(
                    f"""INSERT INTO structures
                        (id, content_hash, data_block, managed_relative_path,
                         original_filename, display_name, note, starred,
                         imported_at, last_used_at, source_origin,
                         {", ".join(_METADATA_COLUMNS)}, schema_version)
                        VALUES (?, ?, ?, ?, ?, NULL, NULL, 0, ?, ?, ?, {", ".join("?" for _ in _METADATA_COLUMNS)}, ?)""",
                    (
                        record_id, content_hash, data_block, managed_relative_path,
                        original_filename, now, now, source_origin,
                        *metadata_values, _SCHEMA_VERSION,
                    ),
                )
                return self.get(record_id)
            except sqlite3.IntegrityError:
                # Lost a race with another connection's concurrent insert of
                # the same (content_hash, data_block) -- retry as an update.
                if attempt == 0:
                    continue
                raise
        raise AssertionError("unreachable")  # pragma: no cover

    def set_starred(self, record_id: str, starred: bool) -> None:
        self._conn.execute(
            "UPDATE structures SET starred=? WHERE id=?", (1 if starred else 0, record_id)
        )

    def rename(self, record_id: str, display_name: Optional[str]) -> None:
        self._conn.execute(
            "UPDATE structures SET display_name=? WHERE id=?",
            (display_name or None, record_id),
        )

    def set_note(self, record_id: str, note: Optional[str]) -> None:
        self._conn.execute(
            "UPDATE structures SET note=? WHERE id=?", (note or None, record_id)
        )

    def remove(self, record_id: str) -> Optional[LibraryRecord]:
        record = self.get(record_id)
        if record is not None:
            self._conn.execute("DELETE FROM structures WHERE id=?", (record_id,))
        return record
