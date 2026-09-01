from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "confirmation_online_retail_ii"
ZIP_PATH = RAW_DIR / "online_retail_ii.zip"
XLSX_PATH = RAW_DIR / "online_retail_II.xlsx"
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_acquisition_report.json"

SOURCE_PAGE_URL = "https://archive.ics.uci.edu/dataset/502/online+retail"
DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/502/online%2Bretail%2Bii.zip"
EXPECTED_MEMBER_NAME = "online_retail_II.xlsx"
USER_AGENT = "BizHallu-Data-Audit/1.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_previous_report() -> dict[str, Any]:
    if not REPORT_PATH.exists():
        return {}
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def download_zip(target: Path) -> dict[str, Any]:
    part_path = target.with_suffix(target.suffix + ".part")
    if part_path.exists():
        part_path.unlink()

    request = urllib.request.Request(DOWNLOAD_URL, headers={"User-Agent": USER_AGENT})
    started_at = datetime.now(timezone.utc)
    with urllib.request.urlopen(request, timeout=120) as response, part_path.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
        headers = {
            "content_type": response.headers.get("Content-Type"),
            "content_length": response.headers.get("Content-Length"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "server": response.headers.get("Server"),
        }
        resolved_url = response.geturl()
        http_status = response.status

    if not part_path.exists() or part_path.stat().st_size == 0:
        raise RuntimeError("The official download produced an empty temporary file.")
    if not zipfile.is_zipfile(part_path):
        raise RuntimeError("The official download is not a valid ZIP archive.")

    part_path.replace(target)
    return {
        "download_started_at_utc": started_at.isoformat(),
        "download_completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "resolved_url": resolved_url,
        "http_status": http_status,
        "headers": headers,
    }


def inspect_archive(zip_path: Path) -> zipfile.ZipInfo:
    with zipfile.ZipFile(zip_path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"ZIP CRC validation failed for {bad_member!r}.")
        workbook_members = [
            item for item in archive.infolist() if not item.is_dir() and item.filename.lower().endswith(".xlsx")
        ]
        if len(workbook_members) != 1:
            raise RuntimeError(
                f"Expected exactly one XLSX member, found {[item.filename for item in workbook_members]!r}."
            )
        member = workbook_members[0]
        if Path(member.filename).name != EXPECTED_MEMBER_NAME:
            raise RuntimeError(
                f"Expected XLSX member {EXPECTED_MEMBER_NAME!r}, found {member.filename!r}."
            )
        return member


def is_git_ignored(path: Path) -> bool:
    relative_path = path.relative_to(PROJECT_ROOT).as_posix()
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative_path],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode == 0


def extract_workbook(zip_path: Path, member: zipfile.ZipInfo, target: Path) -> None:
    part_path = target.with_suffix(target.suffix + ".part")
    if part_path.exists():
        part_path.unlink()
    with zipfile.ZipFile(zip_path) as archive, archive.open(member) as source, part_path.open("wb") as output:
        shutil.copyfileobj(source, output, length=1024 * 1024)
    if part_path.stat().st_size != member.file_size:
        raise RuntimeError(
            f"Extracted XLSX size {part_path.stat().st_size} does not match ZIP member size {member.file_size}."
        )
    if not zipfile.is_zipfile(part_path):
        raise RuntimeError("The extracted XLSX is not a valid Office Open XML container.")
    part_path.replace(target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire and verify UCI Online Retail II for Confirmation Set v1.")
    parser.add_argument("--force", action="store_true", help="Redownload the official ZIP even when it exists.")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    previous = load_previous_report()

    download_performed = args.force or not ZIP_PATH.exists()
    if download_performed:
        response_metadata = download_zip(ZIP_PATH)
    else:
        previous_response = previous.get("http_response", {})
        response_metadata = {
            "download_started_at_utc": previous.get("retrieved_at_utc"),
            "download_completed_at_utc": previous.get("retrieved_at_utc"),
            "resolved_url": previous_response.get("resolved_url", DOWNLOAD_URL),
            "http_status": previous_response.get("http_status", 200),
            "headers": previous_response.get("headers", {}),
        }

    member = inspect_archive(ZIP_PATH)
    if args.force or not XLSX_PATH.exists() or XLSX_PATH.stat().st_size != member.file_size:
        extract_workbook(ZIP_PATH, member, XLSX_PATH)

    zip_sha256 = sha256_file(ZIP_PATH)
    xlsx_sha256 = sha256_file(XLSX_PATH)
    retrieved_at = response_metadata["download_completed_at_utc"]
    if not retrieved_at:
        retrieved_at = datetime.fromtimestamp(ZIP_PATH.stat().st_mtime, timezone.utc).isoformat()

    report = {
        "status": "official_acquisition_and_hash_verified",
        "study_name": "Confirmation Set v1",
        "candidate_id": "uci_online_retail_ii_prior_period",
        "source_page_url": SOURCE_PAGE_URL,
        "official_download_url": DOWNLOAD_URL,
        "doi": "10.24432/C5CG6D",
        "license": "CC BY 4.0",
        "retrieved_at_utc": retrieved_at,
        "acquisition_mode": previous.get("acquisition_mode", "downloaded_from_official_source"),
        "http_response": {
            "resolved_url": response_metadata["resolved_url"],
            "http_status": response_metadata["http_status"],
            "headers": response_metadata["headers"],
        },
        "raw_artifacts": {
            "zip": {
                "path": repo_path(ZIP_PATH),
                "size_bytes": ZIP_PATH.stat().st_size,
                "sha256": zip_sha256,
            },
            "xlsx": {
                "path": repo_path(XLSX_PATH),
                "size_bytes": XLSX_PATH.stat().st_size,
                "sha256": xlsx_sha256,
            },
        },
        "archive_member": {
            "name": member.filename,
            "uncompressed_size_bytes": member.file_size,
            "compressed_size_bytes": member.compress_size,
            "crc32_hex": f"{member.CRC:08x}",
        },
        "checks": {
            "official_host": urllib.parse.urlparse(DOWNLOAD_URL).hostname == "archive.ics.uci.edu",
            "zip_nonempty": ZIP_PATH.stat().st_size > 0,
            "zip_crc_passed": True,
            "single_expected_xlsx_member": True,
            "xlsx_size_matches_zip_member": XLSX_PATH.stat().st_size == member.file_size,
            "xlsx_container_valid": zipfile.is_zipfile(XLSX_PATH),
            "raw_paths_under_gitignored_tree": is_git_ignored(ZIP_PATH) and is_git_ignored(XLSX_PATH),
        },
        "local_only_raw_data": True,
        "context_manifest_created": False,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "no_new_results": True,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(
        json.dumps(
            {
                **report,
                "runtime": {"download_performed_this_run": download_performed},
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
