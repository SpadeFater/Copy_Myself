from __future__ import annotations

from pathlib import Path

from copy_myself.tools.filesystem import FileSystemTool


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_read_rejects_path_outside_allowed_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    result = FileSystemTool([root]).run({"action": "read", "path": outside})

    assert result.ok is False
    assert "PathOutsideRoot" in (result.error or "")


def test_list_returns_directory_entries(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "notes" / "todo.txt", "hello")

    result = FileSystemTool([root]).run({"action": "list", "path": "notes"})

    assert result.ok is True
    assert result.data["action"] == "list"
    assert result.data["entries"][0]["name"] == "todo.txt"
    assert result.data["entries"][0]["kind"] == "file"


def test_stat_returns_file_metadata_and_hash(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "a.txt", "alpha")

    result = FileSystemTool([root]).run({"action": "stat", "path": "a.txt"})

    assert result.ok is True
    assert result.data["kind"] == "file"
    assert result.data["size"] == 5
    assert len(result.data["sha256"]) == 64


def test_read_returns_text_content(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "a.txt", "alpha\nbeta\n")

    result = FileSystemTool([root]).run({"action": "read", "path": "a.txt", "limit": 5})

    assert result.ok is True
    assert result.data["content"] == "alpha"
    assert result.data["truncated"] is True
