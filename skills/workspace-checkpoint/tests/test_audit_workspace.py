from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_workspace import (  # noqa: E402
    audit_workspace,
    choose_memory_path,
    is_regenerable_cache,
    parse_git_status,
)


def test_choose_memory_path_uses_docs_when_present(tmp_path: Path):
    (tmp_path / "docs").mkdir()

    assert choose_memory_path(tmp_path) == tmp_path / "docs" / "ai-memory.md"


def test_choose_memory_path_uses_root_without_docs(tmp_path: Path):
    assert choose_memory_path(tmp_path) == tmp_path / "AI_MEMORY.md"


def test_parse_git_status_preserves_staging_and_rename_target():
    text = "M  staged.py\0 M worktree.py\0?? 未跟踪 文件.txt\0R  new.py\0old.py\0"

    assert parse_git_status(text) == [
        {"index": "M", "worktree": " ", "path": "staged.py"},
        {"index": " ", "worktree": "M", "path": "worktree.py"},
        {"index": "?", "worktree": "?", "path": "未跟踪 文件.txt"},
        {"index": "R", "worktree": " ", "path": "new.py"},
    ]


def test_parse_git_status_does_not_split_arrow_inside_rename_source():
    assert parse_git_status("R  target.py\0old -> name.py\0") == [
        {"index": "R", "worktree": " ", "path": "target.py"}
    ]


@pytest.mark.parametrize("path", [
    "py/__pycache__",
    "py/__pycache__/report.cpython-314.pyc",
    "tests/.pytest_cache",
    "py/report.pyc",
])
def test_regenerable_cache_is_explicitly_recognized(path: str):
    assert is_regenerable_cache(Path(path))


@pytest.mark.parametrize("path", [
    "out/mesh_cache",
    "out/scene_full/scene.npz",
    "out/report.pyc",
    "out/__pycache__/report.cpython-314.pyc",
    "plugin/host/Config",
    "plugin/host/Config/setting.pyc",
    "src/cache.py",
])
def test_project_data_is_not_a_cleanup_candidate(path: str):
    assert not is_regenerable_cache(Path(path))


def test_non_git_directory_returns_file_only_snapshot(tmp_path: Path):
    result = audit_workspace(tmp_path)

    assert result["git"] is False
    assert result["branch"] is None
    assert result["changes"] == []
    assert result["suggested_memory_path"] == str(tmp_path / "AI_MEMORY.md")


def test_empty_git_repository_has_no_commits(tmp_path: Path):
    import subprocess

    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)

    result = audit_workspace(tmp_path)

    assert result["git"] is True
    assert result["recent_commits"] == []
