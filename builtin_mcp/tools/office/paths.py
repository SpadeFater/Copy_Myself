from __future__ import annotations

from pathlib import Path


def normalize_roots(roots: list[Path] | None) -> list[Path]:
    resolved = [Path(root).resolve() for root in (roots or [])]
    return resolved or [Path.cwd().resolve()]


def resolve_allowed_path(raw_path: object, roots: list[Path]) -> Path:
    path = Path(raw_path) if raw_path is not None else Path(".")
    if str(path).startswith(("\\\\", "//")):
        raise ValueError(f"PathOutsideRoot: {path}")
    if not path.is_absolute():
        path = roots[0] / path
    resolved = path.resolve()
    if not any(resolved == root or root in resolved.parents for root in roots):
        raise ValueError(f"PathOutsideRoot: {resolved}")
    return resolved
