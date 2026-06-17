"""Validate the GitHub Pages-ready public bundle."""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
MANIFEST_PATH = DOCS_DIR / "github_pages_manifest.json"
VALIDATION_PATH = DOCS_DIR / "github_pages_validation.json"
TEXT_HASH_SUFFIXES = {".csv", ".html", ".json", ".md", ".txt", ".yml", ".yaml"}

REQUIRED_INDEX_FRAGMENTS = [
    "BizHallu GitHub Pages",
    "Open demo v2",
    "Open career package",
    "Open research one-pager",
    "Open verifier pilot",
    "Business risk lens",
    "Research one-pager",
    "Evidence-aware verifier pilot",
    "Read portfolio narrative",
    "Download interview deck",
    "Preview slides",
    "github_pages_ready",
    "q_0064",
    "q_0069",
    "0.835",
    "0.779",
    "assistant_full_review",
    "span-level",
    "business analytics and AI reliability",
    "GitHub Pages bundle",
    "BA / DS / AI Analyst",
    "Recruiter",
    "Professor",
    "Technical interviewer",
    "Business interviewer",
    "claim-evidence rows",
]

REQUIRED_PAGE_FILES = [
    "index.html",
    "portfolio_demo.html",
    "portfolio_demo_v2.html",
    "portfolio_narrative.html",
    "career_package.html",
    "business_risk_lens.html",
    "research_one_pager.html",
    "evidence_verifier_pilot.html",
    "detector_interpretation.html",
    "label_lock_report.html",
    "label_confirmation_packet.html",
    "assets/full100_draft_detector_error_review_examples.csv",
    "assets/bizhallu_demo_v2_data.json",
    "assets/bizhallu_evidence_verifier_pilot_rows.csv",
    "assets/bizhallu_evidence_verifier_pilot_rows.json",
    "assets/bizhallu_ai_reliability_deck.pptx",
    "assets/bizhallu_ai_reliability_deck_contact_sheet.png",
]

FORBIDDEN_FRAGMENTS = [
    "../site/index.html",
    "../results/",
    "./full100_detector_interpretation.html",
    "./full100_label_lock_report.html",
    "./full100_label_confirmation_packet.html",
    "./bizhallu_portfolio_demo.html",
    "./bizhallu_portfolio_demo_v2.html",
    "pending human review",
    "requires human confirmation",
    "presentation-level confirmation required",
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)


class HTMLCheckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.seen_tags = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.seen_tags += 1


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    if path.suffix.lower() in TEXT_HASH_SUFFIXES:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_html(path: Path, failures: list[dict[str, Any]]) -> None:
    parser = HTMLCheckParser()
    try:
        parser.feed(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        failures.append({"name": "html_parse", "path": repo_path(path), "reason": str(exc)})
        return
    if parser.seen_tags == 0:
        failures.append({"name": "html_parse", "path": repo_path(path), "reason": "no HTML tags parsed"})


def local_links(path: Path) -> list[str]:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.links


def is_external_link(href: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href))


def validate_local_links(path: Path, failures: list[dict[str, Any]]) -> None:
    for href in local_links(path):
        if not href or href.startswith("#") or is_external_link(href):
            continue
        target_text = href.split("#", 1)[0]
        if not target_text:
            continue
        target = (path.parent / target_text).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            failures.append(
                {
                    "name": "local_link_scope",
                    "path": repo_path(path),
                    "href": href,
                    "reason": "link resolves outside project root",
                }
            )
            continue
        if not target.exists():
            failures.append(
                {
                    "name": "local_link_exists",
                    "path": repo_path(path),
                    "href": href,
                    "resolved": repo_path(target),
                    "reason": "linked file is missing",
                }
            )


def main() -> None:
    failures: list[dict[str, Any]] = []
    manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else {}

    if manifest.get("status") != "github_pages_bundle_ready":
        failures.append(
            {
                "name": "manifest_status",
                "reason": "manifest status is not github_pages_bundle_ready",
                "actual": manifest.get("status"),
            }
        )

    for rel_path in REQUIRED_PAGE_FILES:
        path = DOCS_DIR / rel_path
        if not path.exists():
            failures.append({"name": "required_file", "path": repo_path(path), "reason": "missing"})
        elif path.suffix.lower() == ".html":
            parse_html(path, failures)
            validate_local_links(path, failures)

    index_path = DOCS_DIR / "index.html"
    if index_path.exists():
        index_html = index_path.read_text(encoding="utf-8")
        for fragment in REQUIRED_INDEX_FRAGMENTS:
            if fragment not in index_html:
                failures.append(
                    {
                        "name": "required_index_fragment",
                        "fragment": fragment,
                        "reason": "fragment missing from docs/index.html",
                    }
                )

    html_files = [DOCS_DIR / rel_path for rel_path in REQUIRED_PAGE_FILES if rel_path.endswith(".html")]
    for path in html_files:
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8")
        for fragment in FORBIDDEN_FRAGMENTS:
            if fragment in html:
                failures.append(
                    {
                        "name": "forbidden_fragment",
                        "path": repo_path(path),
                        "fragment": fragment,
                        "reason": "stale or non-public link/text remains",
                    }
                )

    for record in manifest.get("pages", []):
        dest = Path(record.get("dest", ""))
        if not dest.is_absolute():
            dest = ROOT / dest
        if dest.exists() and record.get("dest_sha256") != sha256_file(dest):
            failures.append(
                {
                    "name": "page_hash",
                    "path": repo_path(dest),
                    "reason": "page content no longer matches manifest hash",
                }
            )

    for record in manifest.get("assets", []):
        dest = Path(record.get("dest", ""))
        if not dest.is_absolute():
            dest = ROOT / dest
        if dest.exists() and record.get("dest_sha256") != sha256_file(dest):
            failures.append(
                {
                    "name": "asset_hash",
                    "path": repo_path(dest),
                    "reason": "asset content no longer matches manifest hash",
                }
            )

    for json_path in sorted(DOCS_DIR.rglob("*.json")):
        if json_path == VALIDATION_PATH:
            continue
        if contains_local_path(json_path.read_text(encoding="utf-8")):
            failures.append(
                {
                    "name": "public_json_local_path",
                    "path": repo_path(json_path),
                    "reason": "GitHub Pages JSON must use repo-relative paths",
                }
            )

    expected_manifest_values = {
        "current_stage": "github_pages_ready",
        "primary_question_ids": ["q_0064", "q_0069"],
        "question_count": 100,
        "annotated_span_count": 205,
        "locked_primary_span_count": 7,
        "best_test_auprc": 0.835073,
        "best_test_f1": 0.779412,
        "label_lock_basis": "assistant_full_review",
        "demo_v2_locked_span_count": 15,
        "career_faq_count": 10,
        "business_risk_lens_count": 4,
        "research_extension_count": 4,
        "verifier_pilot_span_count": 15,
        "verifier_pilot_contradicted_count": 7,
    }
    for key, expected in expected_manifest_values.items():
        if manifest.get(key) != expected:
            failures.append(
                {
                    "name": "manifest_value",
                    "field": key,
                    "expected": expected,
                    "actual": manifest.get(key),
                    "reason": "manifest value does not match expected public package state",
                }
            )

    validation = {
        "manifest_path": repo_path(MANIFEST_PATH),
        "ready_for_github_pages": len(failures) == 0,
        "required_file_count": len(REQUIRED_PAGE_FILES),
        "checked_html_file_count": len(html_files),
        "current_stage": manifest.get("current_stage"),
        "primary_question_ids": manifest.get("primary_question_ids"),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
