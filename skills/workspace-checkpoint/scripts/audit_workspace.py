"""只读收集工作区检查点所需证据；不删除、不提交、不推送。"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

CACHE_DIRECTORIES = {"__pycache__", ".pytest_cache"}


def choose_memory_path(root: Path) -> Path:
    """沿用项目的文档体系；没有 docs 时不强行创建目录。"""
    return root / "docs" / "ai-memory.md" if (root / "docs").is_dir() else root / "AI_MEMORY.md"


def parse_git_status(text: str) -> list[dict]:
    """解析 NUL 分隔的 porcelain v1，rename 后一个条目是源路径。"""
    changes = []
    entries = iter(text.split("\0"))
    for entry in entries:
        if len(entry) < 4:
            continue
        if entry[0] in {"R", "C"}:
            next(entries, None)
        changes.append({"index": entry[0], "worktree": entry[1], "path": entry[3:]})
    return changes


def is_regenerable_cache(path: Path) -> bool:
    """只认明确的 Python 缓存，并排除正式输出和宿主配置目录。"""
    parts = [part.lower() for part in path.parts]
    if "out" in parts:
        return False
    if any(parts[index:index + 3] == ["plugin", "host", "config"]
           for index in range(len(parts) - 2)):
        return False
    return any(part in CACHE_DIRECTORIES for part in parts) or path.suffix == ".pyc"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )


def _git_output(root: Path, *args: str) -> str:
    result = _git(root, *args)
    if result.returncode != 0:
        command = "git " + " ".join(args)
        raise RuntimeError(f"{root} 执行 `{command}` 失败：{result.stderr.strip()}")
    return result.stdout


def audit_workspace(root: Path) -> dict:
    """收集只读快照；非 Git 目录降级为文件信息，不伪造 Git 状态。"""
    root = root.resolve()
    result = {
        "root": str(root),
        "git": False,
        "branch": None,
        "changes": [],
        "recent_commits": [],
        "suggested_memory_path": str(choose_memory_path(root)),
        "cache_candidates": [],
    }
    probe = _git(root, "rev-parse", "--is-inside-work-tree")
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return result

    result["git"] = True
    result["branch"] = _git_output(root, "branch", "--show-current").strip() or "(detached HEAD)"
    result["changes"] = parse_git_status(_git_output(root, "status", "--porcelain=v1", "-z"))
    log = _git(root, "log", "-10", "--format=%h%x09%ad%x09%s", "--date=short")
    if log.returncode == 0:
        result["recent_commits"] = [
            {"hash": commit_hash, "date": date, "subject": subject}
            for line in log.stdout.splitlines() if line
            for commit_hash, date, subject in [line.split("\t", 2)]
        ]
    elif _git(root, "rev-parse", "--verify", "HEAD").returncode == 0:
        raise RuntimeError(f"{root} 读取近期提交失败：{log.stderr.strip()}")
    ignored = _git_output(root, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory")
    result["cache_candidates"] = sorted({
        line.strip().rstrip("/") for line in ignored.splitlines()
        if is_regenerable_cache(Path(line.strip()))
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="只读检查工作区，为检查点提供证据")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()
    try:
        result = audit_workspace(args.root)
    except RuntimeError as exc:
        parser.exit(2, f"错误：{exc}\n")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"分支：{result['branch']}；变更：{len(result['changes'])}；记忆建议：{result['suggested_memory_path']}")
        print(f"缓存候选：{len(result['cache_candidates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
