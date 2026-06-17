from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from public_paths import LOCAL_PATH_PATTERNS, contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"
REPORTS_DIR = PROJECT_ROOT / "reports"
RESULTS_DIR = PROJECT_ROOT / "results"
VALIDATION_PATH = REPORTS_DIR / "public_path_hygiene_validation.json"


def public_json_files() -> list[Path]:
    files: list[Path] = []
    files.extend(sorted(DOCS_DIR.rglob("*.json")))
    files.extend(sorted(REPORTS_DIR.glob("*_summary.json")))
    files.extend(sorted(REPORTS_DIR.glob("*_validation.json")))
    files.extend(sorted(RESULTS_DIR.glob("*.json")))
    return [path for path in files if path.exists() and path != VALIDATION_PATH]


def find_local_path_lines(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern in line:
                findings.append(
                    {
                        "line": line_number,
                        "pattern": pattern,
                        "excerpt": line.strip()[:180],
                    }
                )
    return findings


def main() -> None:
    failures: list[dict[str, Any]] = []
    checked_files = public_json_files()

    for path in checked_files:
        text = path.read_text(encoding="utf-8")
        if contains_local_path(text):
            failures.append(
                {
                    "name": "local_absolute_path",
                    "path": repo_path(path),
                    "findings": find_local_path_lines(path),
                }
            )

    validation = {
        "status": "public_path_hygiene_ready" if not failures else "public_path_hygiene_failed",
        "checked_file_count": len(checked_files),
        "checked_files": [repo_path(path) for path in checked_files],
        "forbidden_pattern_count": len(LOCAL_PATH_PATTERNS),
        "forbidden_pattern_groups": [
            "windows_user_absolute_path",
            "project_local_download_path",
        ],
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
