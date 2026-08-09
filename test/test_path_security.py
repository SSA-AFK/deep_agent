from pathlib import Path

import pytest

from utils.path_utils import PathBoundaryError, resolve_session_path


@pytest.mark.parametrize("filename", ["../outside.txt", "../../outside.txt", "C:/outside.txt", "/outside.txt", "%2foutside.txt", "nested/../../outside.txt"])
def test_session_paths_reject_traversal(tmp_path: Path, filename: str):
    session = tmp_path / "output" / "session_test"
    session.mkdir(parents=True)

    with pytest.raises(PathBoundaryError):
        resolve_session_path(filename, session)


def test_session_paths_allow_safe_relative_filename(tmp_path: Path):
    session = tmp_path / "output" / "session_test"
    session.mkdir(parents=True)

    assert resolve_session_path("reports/result.md", session) == session / "reports" / "result.md"
