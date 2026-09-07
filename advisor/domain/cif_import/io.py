"""I/O boundary for CIF import.

Reads source bytes exactly once and materializes an immutable on-disk
snapshot that other consumers (Dans_Diffraction, the unit-cell visualizer)
reopen instead of the user's original path -- so a later external edit or
removal of the original file cannot silently change subsequent calculations.
Kept outside any widget so it is trivially unit-testable and swappable.

Never writes into the user's source path or the installed package; this is
throwaway, session-local import infrastructure (temp dir), not persistent
history -- persistence is REQUIREMENT_2's concern, out of scope here.
"""

import hashlib
import os
import shutil
import tempfile


class CifReadError(Exception):
    """Raised for any problem turning a user-selected path into CIF bytes."""


def read_cif_bytes(path: str) -> bytes:
    """Read raw bytes for a candidate CIF path, rejecting non-file input.

    Raises CifReadError with an actionable message for a missing file, a
    folder, a non-`.cif` extension (case-insensitive), or an unreadable file.
    """
    if not path:
        raise CifReadError("No file selected.")
    if not os.path.exists(path):
        raise CifReadError(f"File not found: {path}")
    if os.path.isdir(path):
        raise CifReadError(f"'{path}' is a folder, not a CIF file. Please select a single .cif file.")
    if os.path.splitext(path)[1].lower() != ".cif":
        raise CifReadError(f"'{os.path.basename(path)}' is not a .cif file.")
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError as exc:
        raise CifReadError(f"Could not read '{path}': {exc}") from exc


def content_digest(raw_bytes: bytes) -> str:
    """A stable identity for CIF bytes, used to detect a no-op reselection."""
    return hashlib.sha256(raw_bytes).hexdigest()


def materialize_snapshot(raw_bytes: bytes, original_path: str) -> str:
    """Write an immutable copy of `raw_bytes` to a fresh temp file, return its path."""
    tmp_dir = tempfile.mkdtemp(prefix="advisor_cif_")
    name = os.path.basename(original_path) or "structure.cif"
    if not name.lower().endswith(".cif"):
        name += ".cif"
    snapshot_path = os.path.join(tmp_dir, name)
    with open(snapshot_path, "wb") as fh:
        fh.write(raw_bytes)
    return snapshot_path


def cleanup_snapshot(snapshot_path: str) -> None:
    """Best-effort removal of a snapshot's temp directory. Never raises."""
    if not snapshot_path:
        return
    tmp_dir = os.path.dirname(snapshot_path)
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except OSError:
        pass
