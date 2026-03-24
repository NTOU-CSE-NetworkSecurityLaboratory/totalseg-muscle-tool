from __future__ import annotations

import re
from pathlib import Path

_VERSION_PATTERN = re.compile(r'^version\s*=\s*"([^"]+)"\s*$', re.MULTILINE)


def resolve_python_base_dir(base_dir: str | Path | None = None) -> Path:
    if base_dir is not None:
        return Path(base_dir).resolve()
    return Path(__file__).resolve().parents[1]


def read_local_app_version(base_dir: str | Path | None = None) -> str:
    python_dir = resolve_python_base_dir(base_dir)
    pyproject_path = python_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return "unknown"

    match = _VERSION_PATTERN.search(pyproject_path.read_text(encoding="utf-8"))
    if match is None:
        return "unknown"
    return match.group(1).strip()
