from __future__ import annotations

import zipfile
from pathlib import Path

from tools.filesystem import FileSystemTool


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


def test_read_rejects_binary_files(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "image.bin").write_bytes(b"abc\x00def")

    result = FileSystemTool([root]).run({"action": "read", "path": "image.bin"})

    assert result.ok is False
    assert "BinaryFile" in (result.error or "")


def test_read_extracts_docx_text(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    document = root / "resume.docx"
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>田恒佳</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Python 后端工程师</w:t></w:r></w:p>"
        "</w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("word/document.xml", xml)

    result = FileSystemTool([root]).run({"action": "read", "path": "resume.docx"})

    assert result.ok is True
    assert result.data["action"] == "read"
    assert "田恒佳" in result.data["content"]
    assert "Python 后端工程师" in result.data["content"]


def test_search_finds_file_names(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "notes" / "project-plan.txt", "alpha")

    result = FileSystemTool([root]).run({"action": "search", "mode": "name", "query": "plan"})

    assert result.ok is True
    assert result.data["matches"][0]["path"] == "notes/project-plan.txt"


def test_search_finds_text_content(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "notes" / "a.txt", "alpha target")
    write_text(root / ".git" / "ignored.txt", "target")

    result = FileSystemTool([root]).run({"action": "search", "mode": "content", "query": "target"})

    assert result.ok is True
    assert [match["path"] for match in result.data["matches"]] == ["notes/a.txt"]


def test_write_creates_new_text_file(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    result = FileSystemTool([root]).run(
        {"action": "write", "path": "notes/a.txt", "content": "alpha", "create_parents": True}
    )

    assert result.ok is True
    assert (root / "notes" / "a.txt").read_text(encoding="utf-8") == "alpha"
    assert len(result.data["after_sha256"]) == 64


def test_write_rejects_overwrite_without_expected_hash(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = write_text(root / "a.txt", "alpha")

    result = FileSystemTool([root]).run({"action": "write", "path": "a.txt", "content": "beta"})

    assert result.ok is False
    assert "HashRequired" in (result.error or "")
    assert target.read_text(encoding="utf-8") == "alpha"


def test_write_rejects_hash_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = write_text(root / "a.txt", "alpha")

    result = FileSystemTool([root]).run(
        {"action": "write", "path": "a.txt", "content": "beta", "expected_hash": "bad"}
    )

    assert result.ok is False
    assert "HashMismatch" in (result.error or "")
    assert target.read_text(encoding="utf-8") == "alpha"


def test_write_allows_overwrite_when_hash_matches(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = write_text(root / "a.txt", "alpha")
    current_hash = FileSystemTool([root]).run({"action": "stat", "path": "a.txt"}).data["sha256"]

    result = FileSystemTool([root]).run(
        {"action": "write", "path": "a.txt", "content": "beta", "expected_hash": current_hash}
    )

    assert result.ok is True
    assert result.data["before_sha256"] == current_hash
    assert target.read_text(encoding="utf-8") == "beta"


def test_mkdir_creates_parent_chain(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    result = FileSystemTool([root]).run({"action": "mkdir", "path": "a/b", "parents": True})

    assert result.ok is True
    assert (root / "a" / "b").is_dir()


def test_write_rejects_sensitive_paths(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    result = FileSystemTool([root]).run({"action": "write", "path": ".env", "content": "TOKEN=x"})

    assert result.ok is False
    assert "SensitivePath" in (result.error or "")


def test_patch_updates_text_when_hash_matches(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "a.txt", "alpha\nbeta\n")
    current_hash = FileSystemTool([root]).run({"action": "stat", "path": "a.txt"}).data["sha256"]
    patch = """--- a/a.txt
+++ b/a.txt
@@ -1,2 +1,2 @@
 alpha
-beta
+gamma
"""

    result = FileSystemTool([root]).run(
        {"action": "patch", "path": "a.txt", "patch": patch, "expected_hash": current_hash}
    )

    assert result.ok is True
    assert (root / "a.txt").read_text(encoding="utf-8") == "alpha\ngamma\n"


def test_patch_rejects_hash_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "a.txt", "alpha\n")

    result = FileSystemTool([root]).run({"action": "patch", "path": "a.txt", "patch": "", "expected_hash": "bad"})

    assert result.ok is False
    assert "HashMismatch" in (result.error or "")


def test_copy_file_inside_workspace(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "a.txt", "alpha")

    result = FileSystemTool([root]).run({"action": "copy", "source": "a.txt", "destination": "b.txt"})

    assert result.ok is True
    assert (root / "b.txt").read_text(encoding="utf-8") == "alpha"


def test_move_file_inside_workspace(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "a.txt", "alpha")

    result = FileSystemTool([root]).run({"action": "move", "source": "a.txt", "destination": "b.txt"})

    assert result.ok is True
    assert not (root / "a.txt").exists()
    assert (root / "b.txt").read_text(encoding="utf-8") == "alpha"


def test_delete_dry_run_leaves_file_untouched(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "a.txt", "alpha")

    result = FileSystemTool([root]).run({"action": "delete", "path": "a.txt"})

    assert result.ok is True
    assert result.data["dry_run"] is True
    assert (root / "a.txt").exists()


def test_confirmed_delete_moves_file_to_trash(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / "a.txt", "alpha")

    result = FileSystemTool([root]).run({"action": "delete", "path": "a.txt", "confirm": True, "dry_run": False})

    assert result.ok is True
    assert not (root / "a.txt").exists()
    assert (root / result.data["trash_path"]).read_text(encoding="utf-8") == "alpha"


def test_delete_rejects_sensitive_paths(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_text(root / ".env", "TOKEN=x")

    result = FileSystemTool([root]).run({"action": "delete", "path": ".env", "confirm": True, "dry_run": False})

    assert result.ok is False
    assert "SensitivePath" in (result.error or "")
