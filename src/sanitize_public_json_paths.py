from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from public_paths import repo_path, sanitize_public_paths
from validate_public_path_hygiene import public_json_files


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    changed: list[str] = []

    for path in public_json_files():
        original = load_json(path)
        sanitized = sanitize_public_paths(original)
        if sanitized != original:
            path.write_text(json.dumps(sanitized, indent=2, ensure_ascii=True), encoding="utf-8")
            changed.append(repo_path(path))

    result = {
        "status": "public_json_paths_sanitized",
        "changed_file_count": len(changed),
        "changed_files": changed,
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
