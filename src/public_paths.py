from __future__ import annotations

from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT_TEXT = str(PROJECT_ROOT).replace("\\", "/")

LOCAL_PATH_PATTERNS = [
    "C:\\Users\\",
    "C:\\\\Users\\\\",
    "C:/Users/",
    "Downloads\\p1\\bizhallu",
    "Downloads\\\\p1\\\\bizhallu",
    "Downloads/p1/bizhallu",
]


def repo_path(path: str | Path) -> str:
    """Return a repo-relative path for public reports and manifests."""
    path_obj = Path(path)
    try:
        return path_obj.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def sanitize_public_paths(value: Any) -> Any:
    """Recursively convert project-local absolute path strings to repo-relative strings."""
    if isinstance(value, dict):
        return {key: sanitize_public_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_public_paths(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_public_paths(item) for item in value]
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        if normalized == PROJECT_ROOT_TEXT:
            return "."
        root_prefix = PROJECT_ROOT_TEXT + "/"
        if normalized.startswith(root_prefix):
            return normalized[len(root_prefix) :]
        if contains_local_path(value):
            if "hf_cache/hub" in normalized:
                return "../hf_cache/hub"
            if "hf_cache" in normalized:
                return "../hf_cache"
            if normalized.endswith("/python.exe"):
                return "local_python_env/python.exe"
            return "<local_path_redacted>"
    return value


def contains_local_path(value: str) -> bool:
    return any(pattern in value for pattern in LOCAL_PATH_PATTERNS)
