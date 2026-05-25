from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANNOTATIONS_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_pilot.jsonl"
DEFAULT_GENERATIONS_PATH = PROJECT_ROOT / "outputs" / "qwen_pilot20_generations.jsonl"
DEFAULT_TRACES_PATH = PROJECT_ROOT / "outputs" / "qwen_pilot20_token_traces.jsonl"
DEFAULT_OUTPUT_PREFIX = "pilot20_span_token_alignment"

SPECIAL_TOKEN_PREFIX = "<|"
SPECIAL_TOKEN_SUFFIX = "|>"
REPLACEMENT_CHAR = "\ufffd"
APPROX_CHAR = "\u2248"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "annotation_id",
        "question_id",
        "fact_type",
        "label",
        "span_text",
        "span_start_char",
        "span_end_char",
        "token_start_position",
        "token_end_position",
        "token_count",
        "token_text_window",
        "left_boundary_slop",
        "right_boundary_slop",
        "mean_token_logprob",
        "mean_token_nll",
        "mean_token_entropy",
        "max_token_entropy",
        "mean_top2_margin",
        "min_top2_margin",
        "mean_selected_step_energy_gap",
        "max_selected_step_energy_gap",
        "mean_spilled_energy_delta",
        "mean_spilled_energy_abs_delta",
        "max_spilled_energy_abs_delta",
        "mean_token_energy",
        "mean_marginal_energy",
        "mean_spilled_probability_mass_after_top1",
        "mean_spilled_probability_mass_after_top2",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in fieldnames})


def is_special_token(token_text: str) -> bool:
    return token_text.startswith(SPECIAL_TOKEN_PREFIX) and token_text.endswith(SPECIAL_TOKEN_SUFFIX)


def display_texts_for_alignment(token_traces: list[dict[str, Any]]) -> list[str]:
    """Normalize token texts enough to reconstruct generated_text for char alignment.

    Qwen can decode some UTF-8 byte fallback pieces as replacement characters
    when tokens are decoded one by one. In the pilot traces this appears as the
    adjacent pair " \ufffd" + "\ufffd", which decodes to " \u2248" in the full
    generated string. We keep one token for the leading space and one token for
    the approximation sign so downstream token positions remain stable.
    """

    display_texts = [str(token.get("token_text", "")) for token in token_traces]
    for index in range(len(display_texts) - 1):
        current_text = display_texts[index]
        next_text = display_texts[index + 1]
        if current_text.endswith(REPLACEMENT_CHAR) and next_text == REPLACEMENT_CHAR:
            display_texts[index] = current_text[:-1]
            display_texts[index + 1] = APPROX_CHAR
    return display_texts


def build_token_char_spans(
    question_id: str,
    generated_text: str,
    token_traces: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    display_texts = display_texts_for_alignment(token_traces)
    token_spans: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    cursor = 0

    for token, display_text in zip(token_traces, display_texts):
        token_position = int(token["position"])
        original_text = str(token.get("token_text", ""))
        special = is_special_token(original_text)
        if special:
            start = cursor
            end = cursor
            aligned_text = ""
        else:
            start = cursor
            end = cursor + len(display_text)
            actual = generated_text[start:end]
            if actual != display_text:
                failures.append(
                    {
                        "question_id": question_id,
                        "position": token_position,
                        "reason": "token_text does not match generated_text at cursor",
                        "expected_display_text": display_text,
                        "actual_text": actual,
                        "cursor": cursor,
                    }
                )
            aligned_text = display_text
            cursor = end

        token_spans.append(
            {
                **token,
                "char_start": start,
                "char_end": end,
                "aligned_text": aligned_text,
                "is_special_token": special,
            }
        )

    if cursor != len(generated_text):
        failures.append(
            {
                "question_id": question_id,
                "reason": "token reconstruction length mismatch",
                "cursor": cursor,
                "generated_text_length": len(generated_text),
            }
        )

    reconstructed_text = "".join(token["aligned_text"] for token in token_spans if not token["is_special_token"])
    if reconstructed_text != generated_text:
        failures.append(
            {
                "question_id": question_id,
                "reason": "token reconstruction text mismatch",
                "reconstructed_length": len(reconstructed_text),
                "generated_text_length": len(generated_text),
            }
        )

    return token_spans, failures


def overlapping_tokens(token_spans: list[dict[str, Any]], span_start: int, span_end: int) -> list[dict[str, Any]]:
    return [
        token
        for token in token_spans
        if not token["is_special_token"] and token["char_end"] > span_start and token["char_start"] < span_end
    ]


def summarize_scores(tokens: list[dict[str, Any]]) -> dict[str, float | None]:
    energy_fields = {
        "mean_selected_step_energy_gap": None,
        "max_selected_step_energy_gap": None,
        "mean_spilled_energy_delta": None,
        "mean_spilled_energy_abs_delta": None,
        "max_spilled_energy_abs_delta": None,
        "mean_token_energy": None,
        "mean_marginal_energy": None,
        "mean_spilled_probability_mass_after_top1": None,
        "mean_spilled_probability_mass_after_top2": None,
    }
    if not tokens:
        return {
            "mean_token_logprob": None,
            "mean_token_nll": None,
            "mean_token_entropy": None,
            "max_token_entropy": None,
            "mean_top2_margin": None,
            "min_top2_margin": None,
            **energy_fields,
        }

    logprobs = [float(token["token_logprob"]) for token in tokens]
    entropies = [float(token["token_entropy"]) for token in tokens]
    margins = [float(token["top2_margin"]) for token in tokens]
    if all("selected_step_energy_gap" in token for token in tokens):
        selected_step_energy_gaps = [float(token["selected_step_energy_gap"]) for token in tokens]
        spilled_energy_deltas = [float(token["spilled_energy_delta"]) for token in tokens]
        spilled_energy_abs_deltas = [float(token["spilled_energy_abs_delta"]) for token in tokens]
        token_energies = [float(token["token_energy"]) for token in tokens]
        marginal_energies = [float(token["marginal_energy"]) for token in tokens]
        spilled_mass_after_top1 = [float(token["spilled_probability_mass_after_top1"]) for token in tokens]
        spilled_mass_after_top2 = [float(token["spilled_probability_mass_after_top2"]) for token in tokens]
        energy_fields = {
            "mean_selected_step_energy_gap": round(mean(selected_step_energy_gaps), 6),
            "max_selected_step_energy_gap": round(max(selected_step_energy_gaps), 6),
            "mean_spilled_energy_delta": round(mean(spilled_energy_deltas), 6),
            "mean_spilled_energy_abs_delta": round(mean(spilled_energy_abs_deltas), 6),
            "max_spilled_energy_abs_delta": round(max(spilled_energy_abs_deltas), 6),
            "mean_token_energy": round(mean(token_energies), 6),
            "mean_marginal_energy": round(mean(marginal_energies), 6),
            "mean_spilled_probability_mass_after_top1": round(mean(spilled_mass_after_top1), 6),
            "mean_spilled_probability_mass_after_top2": round(mean(spilled_mass_after_top2), 6),
        }
    return {
        "mean_token_logprob": round(mean(logprobs), 6),
        "mean_token_nll": round(mean([-value for value in logprobs]), 6),
        "mean_token_entropy": round(mean(entropies), 6),
        "max_token_entropy": round(max(entropies), 6),
        "mean_top2_margin": round(mean(margins), 6),
        "min_top2_margin": round(min(margins), 6),
        **energy_fields,
    }


def build_alignment_records(
    annotations: list[dict[str, Any]],
    generations_by_qid: dict[str, dict[str, Any]],
    token_spans_by_qid: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for annotation in annotations:
        annotation_id = str(annotation["annotation_id"])
        qid = str(annotation["question_id"])
        generation = generations_by_qid.get(qid)
        if generation is None:
            failures.append({"annotation_id": annotation_id, "reason": "missing generation", "question_id": qid})
            continue

        generated_text = str(generation["generated_text"])
        span_start = int(annotation["span_start_char"])
        span_end = int(annotation["span_end_char"])
        span_text = str(annotation["span_text"])
        actual_span = generated_text[span_start:span_end]
        if actual_span != span_text:
            failures.append(
                {
                    "annotation_id": annotation_id,
                    "question_id": qid,
                    "reason": "annotation span offsets do not match generated_text",
                    "expected_span_text": span_text,
                    "actual_span_text": actual_span,
                }
            )
            continue

        tokens = overlapping_tokens(token_spans_by_qid[qid], span_start, span_end)
        if not tokens:
            failures.append({"annotation_id": annotation_id, "question_id": qid, "reason": "no overlapping tokens"})
            continue

        token_char_start = min(int(token["char_start"]) for token in tokens)
        token_char_end = max(int(token["char_end"]) for token in tokens)
        token_text_window = generated_text[token_char_start:token_char_end]
        if span_text not in token_text_window:
            failures.append(
                {
                    "annotation_id": annotation_id,
                    "question_id": qid,
                    "reason": "token window does not contain span text",
                    "span_text": span_text,
                    "token_text_window": token_text_window,
                }
            )

        token_positions = [int(token["position"]) for token in tokens]
        score_summary = summarize_scores(tokens)
        records.append(
            {
                "annotation_id": annotation_id,
                "question_id": qid,
                "prompt_id": annotation["prompt_id"],
                "fact_type": annotation["fact_type"],
                "label": annotation["label"],
                "span_text": span_text,
                "span_start_char": span_start,
                "span_end_char": span_end,
                "token_start_position": min(token_positions),
                "token_end_position": max(token_positions) + 1,
                "token_positions": token_positions,
                "token_count": len(tokens),
                "token_text_window": token_text_window,
                "token_char_start": token_char_start,
                "token_char_end": token_char_end,
                "left_boundary_slop": span_start - token_char_start,
                "right_boundary_slop": token_char_end - span_end,
                **score_summary,
            }
        )

    return records, failures


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations-path", default=str(DEFAULT_ANNOTATIONS_PATH))
    parser.add_argument("--generations-path", default=str(DEFAULT_GENERATIONS_PATH))
    parser.add_argument("--traces-path", default=str(DEFAULT_TRACES_PATH))
    parser.add_argument("--output-prefix", default=DEFAULT_OUTPUT_PREFIX)
    args = parser.parse_args()

    annotations_path = resolve_project_path(args.annotations_path)
    generations_path = resolve_project_path(args.generations_path)
    traces_path = resolve_project_path(args.traces_path)
    outputs_dir = PROJECT_ROOT / "outputs"
    alignment_jsonl_path = outputs_dir / f"{args.output_prefix}.jsonl"
    alignment_csv_path = outputs_dir / f"{args.output_prefix}.csv"
    report_path = outputs_dir / f"{args.output_prefix}_report.json"

    annotations = load_jsonl(annotations_path)
    generations = load_jsonl(generations_path)
    traces = load_jsonl(traces_path)
    generations_by_qid = {str(record["question_id"]): record for record in generations}
    traces_by_qid = {str(record["question_id"]): record for record in traces}

    failures: list[dict[str, Any]] = []
    token_spans_by_qid: dict[str, list[dict[str, Any]]] = {}
    replacement_pair_questions: set[str] = set()

    for qid, generation in generations_by_qid.items():
        trace_record = traces_by_qid.get(qid)
        if trace_record is None:
            failures.append({"question_id": qid, "reason": "missing trace record"})
            continue
        token_traces = trace_record["token_traces"]
        if any(
            str(token_traces[index].get("token_text", "")).endswith(REPLACEMENT_CHAR)
            and str(token_traces[index + 1].get("token_text", "")) == REPLACEMENT_CHAR
            for index in range(len(token_traces) - 1)
        ):
            replacement_pair_questions.add(qid)
        token_spans, token_failures = build_token_char_spans(qid, str(generation["generated_text"]), token_traces)
        token_spans_by_qid[qid] = token_spans
        failures.extend(token_failures)

    alignment_records, alignment_failures = build_alignment_records(
        annotations,
        generations_by_qid,
        token_spans_by_qid,
    )
    failures.extend(alignment_failures)

    write_jsonl(alignment_jsonl_path, alignment_records)
    write_csv(alignment_csv_path, alignment_records)

    label_counts = Counter(str(record["label"]) for record in alignment_records)
    fact_type_counts = Counter(str(record["fact_type"]) for record in alignment_records)
    token_count_values = [int(record["token_count"]) for record in alignment_records]
    left_slop_values = [int(record["left_boundary_slop"]) for record in alignment_records]
    right_slop_values = [int(record["right_boundary_slop"]) for record in alignment_records]

    report = {
        "annotations_path": str(annotations_path),
        "generations_path": str(generations_path),
        "traces_path": str(traces_path),
        "alignment_jsonl_path": str(alignment_jsonl_path),
        "alignment_csv_path": str(alignment_csv_path),
        "annotation_count": len(annotations),
        "aligned_span_count": len(alignment_records),
        "question_count": len({record["question_id"] for record in alignment_records}),
        "num_failures": len(failures),
        "failures": failures,
        "label_counts": dict(sorted(label_counts.items())),
        "fact_type_counts": dict(sorted(fact_type_counts.items())),
        "token_count_summary": {
            "min": min(token_count_values) if token_count_values else None,
            "max": max(token_count_values) if token_count_values else None,
            "mean": round(mean(token_count_values), 4) if token_count_values else None,
        },
        "boundary_slop_summary": {
            "max_left": max(left_slop_values) if left_slop_values else None,
            "max_right": max(right_slop_values) if right_slop_values else None,
            "spans_with_left_slop": sum(1 for value in left_slop_values if value > 0),
            "spans_with_right_slop": sum(1 for value in right_slop_values if value > 0),
        },
        "replacement_pair_questions": sorted(replacement_pair_questions),
        "ready_for_simple_logit_baselines": len(failures) == 0 and len(alignment_records) == len(annotations),
        "ready_for_energy_baselines": (
            len(failures) == 0
            and len(alignment_records) == len(annotations)
            and all(record.get("mean_spilled_energy_abs_delta") is not None for record in alignment_records)
        ),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
