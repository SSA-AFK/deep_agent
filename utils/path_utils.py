"""Path helpers that enforce per-session file boundaries."""

from pathlib import Path


class PathBoundaryError(ValueError):
    """Raised when an input path would escape its session directory."""


def resolve_session_path(filename: str, session_dir: str | Path) -> Path:
    """Resolve a relative filename inside ``session_dir`` or reject it."""
    if not filename or "\x00" in filename:
        raise PathBoundaryError("A non-empty filename is required.")
    normalized = filename.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized or "%2f" in normalized.lower() or "%5c" in normalized.lower():
        raise PathBoundaryError("Absolute or encoded paths are not allowed.")
    session_root = Path(session_dir).resolve()
    candidate = (session_root / normalized).resolve()
    if not candidate.is_relative_to(session_root):
        raise PathBoundaryError("The file path must remain inside the session directory.")
    return candidate


def resolve_path(filename: str, session_dir: str | None = None) -> str:
    """Backward-compatible wrapper for tools that require a session directory."""
    if session_dir is None:
        raise PathBoundaryError("A session directory is required.")
    return str(resolve_session_path(filename, session_dir))
