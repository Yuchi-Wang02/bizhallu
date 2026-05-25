from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANNOTATION_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_pilot.jsonl"
DEFAULT_VALIDATION_PATH = PROJECT_ROOT / "outputs" / "span_annotations_pilot_validation.json"
DEFAULT_GENERATION_FILE = "outputs/qwen_pilot20_generations.jsonl"

REQUIRED_FIELDS = {
    "annotation_id",
    "question_id",
    "prompt_id",
    "source_generation_file",
    "annotation_version",
    "span_text",
    "span_start_char",
    "span_end_char",
    "fact_type",
    "label",
    "gold_reference",
    "reason",
    "confidence",
    "notes",
}

ALLOWED_LABELS = {
    "correct_key_fact",
    "hallucinated_key_fact",
    "unsupported_claim",
    "ambiguous_or_unverifiable",
    "ignore",
}

ALLOWED_FACT_TYPES = {
    "month",
    "date_range",
    "country",
    "product_stock_code",
    "product_name",
    "currency_amount",
    "percentage",
    "ranking",
    "comparison_direction",
    "business_definition",
    "unsupported_business_claim",
    "malformed_number",
}

ALLOWED_CONFIDENCE = {"high", "medium", "low"}
RANK_VALUE_ONLY_RE = re.compile(r"^\*{0,2}\d+(?:st|nd|rd|th)?[.)]?\*{0,2}$", re.IGNORECASE)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number} is not valid JSON: {exc}") from exc
        record["_line_number"] = line_number
        records.append(record)
    return records


def add_failure(failures: list[dict[str, Any]], annotation_id: str, reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"annotation_id": annotation_id, "reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def relative_path_to_project(path_text: str) -> Path:
    normalized = Path(path_text.replace("/", "\\"))
    if normalized.is_absolute():
        return normalized
    return PROJECT_ROOT / normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotation-path", default=str(DEFAULT_ANNOTATION_PATH))
    parser.add_argument("--validation-path", default=str(DEFAULT_VALIDATION_PATH))
    parser.add_argument("--generation-file", default=DEFAULT_GENERATION_FILE)
    parser.add_argument("--expected-question-count", type=int, default=None)
    parser.add_argument("--expected-min-span-count", type=int, default=1)
    args = parser.parse_args()

    annotation_path = Path(args.annotation_path)
    if not annotation_path.is_absolute():
        annotation_path = PROJECT_ROOT / annotation_path
    validation_path = Path(args.validation_path)
    if not validation_path.is_absolute():
        validation_path = PROJECT_ROOT / validation_path

    failures: list[dict[str, Any]] = []
    if not annotation_path.exists():
        add_failure(failures, "GLOBAL", "missing annotation file", str(annotation_path))
        records: list[dict[str, Any]] = []
    else:
        try:
            records = load_jsonl(annotation_path)
        except ValueError as exc:
            add_failure(failures, "GLOBAL", "annotation JSONL parse failure", str(exc))
            records = []

    expected_generation_file = args.generation_file.replace("\\", "/")
    generation_path = relative_path_to_project(expected_generation_file)
    generations_by_qid: dict[str, dict[str, Any]] = {}
    if not generation_path.exists():
        add_failure(failures, "GLOBAL", "missing generation file", str(generation_path))
    else:
        generations_by_qid = {record["question_id"]: record for record in load_jsonl(generation_path)}

    seen_ids: set[str] = set()
    seen_spans: set[tuple[str, int, int, str, str]] = set()

    for record in records:
        annotation_id = str(record.get("annotation_id", f"LINE_{record.get('_line_number', 'UNKNOWN')}"))
        missing_fields = sorted(REQUIRED_FIELDS - set(record))
        if missing_fields:
            add_failure(failures, annotation_id, "missing required fields", missing_fields)
            continue

        if annotation_id in seen_ids:
            add_failure(failures, annotation_id, "duplicate annotation_id")
        seen_ids.add(annotation_id)

        qid = str(record.get("question_id", ""))
        prompt_id = str(record.get("prompt_id", ""))
        source_file = str(record.get("source_generation_file", ""))
        generation = generations_by_qid.get(qid)
        if generation is None:
            add_failure(failures, annotation_id, "question_id not found in generation file", qid)
            continue
        if prompt_id != generation.get("prompt_id"):
            add_failure(
                failures,
                annotation_id,
                "prompt_id mismatch with generation file",
                {"annotation": prompt_id, "generation": generation.get("prompt_id")},
            )
        if source_file.replace("\\", "/") != expected_generation_file:
            add_failure(failures, annotation_id, "unexpected source_generation_file", source_file)
        elif not relative_path_to_project(source_file).exists():
            add_failure(failures, annotation_id, "source_generation_file does not exist", source_file)

        if record.get("label") not in ALLOWED_LABELS:
            add_failure(failures, annotation_id, "invalid label", record.get("label"))
        if record.get("fact_type") not in ALLOWED_FACT_TYPES:
            add_failure(failures, annotation_id, "invalid fact_type", record.get("fact_type"))
        if record.get("confidence") not in ALLOWED_CONFIDENCE:
            add_failure(failures, annotation_id, "invalid confidence", record.get("confidence"))
        if not isinstance(record.get("gold_reference"), dict):
            add_failure(failures, annotation_id, "gold_reference must be an object")
        if not str(record.get("reason", "")).strip():
            add_failure(failures, annotation_id, "reason must be non-empty")
        if record.get("fact_type") == "ranking":
            span_for_rank_check = str(record.get("span_text", "")).strip()
            notes_for_rank_check = str(record.get("notes", ""))
            if RANK_VALUE_ONLY_RE.fullmatch(span_for_rank_check) and "list_rank_marker" not in notes_for_rank_check:
                add_failure(
                    failures,
                    annotation_id,
                    "ranking span is a bare rank marker without list_rank_marker note",
                    span_for_rank_check,
                )

        start = record.get("span_start_char")
        end = record.get("span_end_char")
        span_text = record.get("span_text")
        if not isinstance(start, int) or not isinstance(end, int) or isinstance(start, bool) or isinstance(end, bool):
            add_failure(failures, annotation_id, "span offsets must be integers", {"start": start, "end": end})
            continue
        generated_text = generation.get("generated_text", "")
        if start < 0 or end <= start or end > len(generated_text):
            add_failure(
                failures,
                annotation_id,
                "span offsets outside generated_text bounds",
                {"start": start, "end": end, "generated_text_length": len(generated_text)},
            )
            continue
        actual_span = generated_text[start:end]
        if actual_span != span_text:
            add_failure(
                failures,
                annotation_id,
                "span_text does not match generated_text offsets",
                {"expected": span_text, "actual": actual_span, "start": start, "end": end},
            )

        span_key = (qid, start, end, str(record.get("fact_type")), str(record.get("label")))
        if span_key in seen_spans:
            add_failure(failures, annotation_id, "duplicate span/fact_type/label record", span_key)
        seen_spans.add(span_key)

    question_ids = sorted({str(record.get("question_id")) for record in records})
    if args.expected_question_count is not None and len(question_ids) != args.expected_question_count:
        add_failure(
            failures,
            "GLOBAL",
            "unexpected annotated question count",
            {"expected": args.expected_question_count, "actual": len(question_ids), "question_ids": question_ids},
        )
    if len(records) < args.expected_min_span_count:
        add_failure(
            failures,
            "GLOBAL",
            "too few annotation spans",
            {"expected_min": args.expected_min_span_count, "actual": len(records)},
        )

    label_counts = Counter(str(record.get("label")) for record in records)
    fact_type_counts = Counter(str(record.get("fact_type")) for record in records)
    question_counts = Counter(str(record.get("question_id")) for record in records)

    report = {
        "annotation_path": str(annotation_path),
        "generation_path": str(generation_path),
        "expected_source_generation_file": expected_generation_file,
        "span_count": len(records),
        "annotated_question_count": len(question_ids),
        "annotated_question_ids": question_ids,
        "num_failures": len(failures),
        "failures": failures,
        "label_counts": dict(sorted(label_counts.items())),
        "fact_type_counts": dict(sorted(fact_type_counts.items())),
        "spans_by_question": dict(sorted(question_counts.items())),
    }
    validation_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
