from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CONFIG_DIR = PROJECT_ROOT / "configs"

REPORT_PATH = RESULTS_DIR / "full100_preflight_report.json"
VALIDATION_PATH = RESULTS_DIR / "full100_preflight_validation.json"
FULL100_RUN_REPORT_PATH = OUTPUT_DIR / "qwen_full100_report.json"
FULL100_RUN_VALIDATION_PATH = OUTPUT_DIR / "qwen_full100_validation.json"
FULL100_REVIEW_REPORT_PATH = OUTPUT_DIR / "full100_review_report.json"
FULL100_REVIEW_VALIDATION_PATH = OUTPUT_DIR / "full100_review_validation.json"
FULL100_QUEUE_REPORT_PATH = OUTPUT_DIR / "full100_annotation_queue_report.json"
FULL100_QUEUE_VALIDATION_PATH = OUTPUT_DIR / "full100_annotation_queue_validation.json"
FULL100_SEED_REPORT_PATH = OUTPUT_DIR / "full100_annotation_seed_report.json"
FULL100_SEED_VALIDATION_PATH = OUTPUT_DIR / "full100_annotation_seed_validation.json"
FULL100_DRAFT_REPORT_PATH = OUTPUT_DIR / "full100_annotation_draft_report.json"
FULL100_DRAFT_VALIDATION_PATH = OUTPUT_DIR / "full100_annotation_draft_validation.json"
FULL100_CONSISTENCY_AUDIT_REPORT_PATH = OUTPUT_DIR / "full100_annotation_consistency_audit_report.json"
FULL100_ALIGNMENT_REPORT_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment_report.json"
FULL100_ALIGNMENT_VALIDATION_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment_validation.json"
FULL100_AUDIT_NOTE_REVIEW_REPORT_PATH = OUTPUT_DIR / "full100_audit_note_review_report.json"
FULL100_AUDIT_NOTE_REVIEW_VALIDATION_PATH = OUTPUT_DIR / "full100_audit_note_review_validation.json"
FULL100_DETECTOR_SCORES_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_scores_report.json"
FULL100_DETECTOR_SCORES_VALIDATION_PATH = RESULTS_DIR / "full100_draft_detector_scores_validation.json"
FULL100_SIMPLE_SPLIT_METRICS_PATH = RESULTS_DIR / "full100_draft_simple_split_metrics.csv"
FULL100_SIMPLE_SPLIT_REPORT_PATH = RESULTS_DIR / "full100_draft_simple_split_report.json"
FULL100_SIMPLE_SPLIT_VALIDATION_PATH = RESULTS_DIR / "full100_draft_simple_split_validation.json"
FULL100_ENERGY_SPLIT_METRICS_PATH = RESULTS_DIR / "full100_draft_energy_split_metrics.csv"
FULL100_ENERGY_SPLIT_REPORT_PATH = RESULTS_DIR / "full100_draft_energy_split_report.json"
FULL100_ENERGY_SPLIT_VALIDATION_PATH = RESULTS_DIR / "full100_draft_energy_split_validation.json"
FULL100_FAMILY_COMPARISON_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison_report.json"
FULL100_FAMILY_COMPARISON_VALIDATION_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison_validation.json"
FULL100_ERROR_REVIEW_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_error_review_report.json"
FULL100_ERROR_REVIEW_VALIDATION_PATH = RESULTS_DIR / "full100_draft_detector_error_review_validation.json"
FULL100_INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"
FULL100_INTERPRETATION_VALIDATION_PATH = REPORTS_DIR / "full100_detector_interpretation_validation.json"
FULL100_LABEL_CONFIRMATION_PACKET_SUMMARY_PATH = REPORTS_DIR / "full100_label_confirmation_packet_summary.json"
FULL100_LABEL_CONFIRMATION_PACKET_VALIDATION_PATH = REPORTS_DIR / "full100_label_confirmation_packet_validation.json"
FULL100_LABEL_CONFIRMATION_REVIEW_NOTES_SUMMARY_PATH = (
    REPORTS_DIR / "full100_label_confirmation_review_notes_summary.json"
)
FULL100_LABEL_CONFIRMATION_REVIEW_NOTES_VALIDATION_PATH = (
    REPORTS_DIR / "full100_label_confirmation_review_notes_validation.json"
)
FULL100_LABEL_LOCK_SUMMARY_PATH = REPORTS_DIR / "full100_label_lock_summary.json"
FULL100_LABEL_LOCK_VALIDATION_PATH = REPORTS_DIR / "full100_label_lock_validation.json"
PORTFOLIO_DEMO_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_summary.json"
PORTFOLIO_DEMO_VALIDATION_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_validation.json"
PORTFOLIO_NARRATIVE_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_summary.json"
PORTFOLIO_NARRATIVE_VALIDATION_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_validation.json"
GITHUB_PAGES_MANIFEST_PATH = DOCS_DIR / "github_pages_manifest.json"
GITHUB_PAGES_VALIDATION_PATH = DOCS_DIR / "github_pages_validation.json"


CHECKS = [
    {
        "name": "gold_questions_validated",
        "path": PROCESSED_DIR / "business_questions_gold_validation.json",
        "expected_num_failures": 0,
    },
    {
        "name": "prompts_validated",
        "path": OUTPUT_DIR / "qwen_input_prompts_validation.json",
        "expected_num_failures": 0,
    },
    {
        "name": "full100_config_validated",
        "path": OUTPUT_DIR / "full100_config_validation.json",
        "expected_num_failures": 0,
    },
    {
        "name": "energy_trace_readiness_validated",
        "path": RESULTS_DIR / "energy_trace_readiness_validation.json",
        "expected_num_failures": 0,
    },
    {
        "name": "pilot20_energy_trace_validated",
        "path": OUTPUT_DIR / "qwen_pilot20_energy_validation.json",
        "expected_num_failures": 0,
    },
    {
        "name": "pilot20_energy_baselines_validated",
        "path": RESULTS_DIR / "pilot20_energy_baseline_validation.json",
        "expected_num_failures": 0,
    },
    {
        "name": "detector_readiness_validated",
        "path": RESULTS_DIR / "pilot20_detector_readiness_validation.json",
        "expected_num_failures": 0,
    },
    {
        "name": "split_eval_smoke_validated",
        "path": RESULTS_DIR / "split_eval_smoke_validation.json",
        "expected_num_failures": 0,
    },
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_validation_file(check: dict[str, Any]) -> dict[str, Any]:
    path = Path(check["path"])
    if not path.exists():
        return {
            "name": check["name"],
            "path": str(path),
            "passed": False,
            "reason": "missing file",
        }
    data = load_json(path)
    expected = check["expected_num_failures"]
    actual = data.get("num_failures")
    return {
        "name": check["name"],
        "path": str(path),
        "passed": actual == expected,
        "num_failures": actual,
        "expected_num_failures": expected,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    checks = [check_validation_file(check) for check in CHECKS]

    detector_config_path = CONFIG_DIR / "detector_baseline_suite.json"
    full100_config_path = CONFIG_DIR / "full100_questions.json"
    split_guard_path = RESULTS_DIR / "pilot20_train_only_split_guard_report.json"
    detector_summary_path = RESULTS_DIR / "pilot20_detector_readiness_summary.json"
    full100_generation_run = FULL100_RUN_VALIDATION_PATH.exists()
    full100_run_report = load_json(FULL100_RUN_REPORT_PATH) if FULL100_RUN_REPORT_PATH.exists() else {}
    full100_run_validation = load_json(FULL100_RUN_VALIDATION_PATH) if FULL100_RUN_VALIDATION_PATH.exists() else {}
    full100_review_report = load_json(FULL100_REVIEW_REPORT_PATH) if FULL100_REVIEW_REPORT_PATH.exists() else {}
    full100_review_validation = load_json(FULL100_REVIEW_VALIDATION_PATH) if FULL100_REVIEW_VALIDATION_PATH.exists() else {}
    full100_review_ready = (
        full100_review_validation.get("num_failures") == 0
        and full100_review_validation.get("record_count") == 100
        and full100_review_validation.get("jsonl_record_count") == 100
    )
    full100_queue_report = load_json(FULL100_QUEUE_REPORT_PATH) if FULL100_QUEUE_REPORT_PATH.exists() else {}
    full100_queue_validation = load_json(FULL100_QUEUE_VALIDATION_PATH) if FULL100_QUEUE_VALIDATION_PATH.exists() else {}
    full100_annotation_queue_ready = (
        full100_queue_validation.get("num_failures") == 0
        and full100_queue_validation.get("record_count") == 100
        and full100_queue_validation.get("initial_batch_count") == 35
    )
    full100_seed_report = load_json(FULL100_SEED_REPORT_PATH) if FULL100_SEED_REPORT_PATH.exists() else {}
    full100_seed_validation = load_json(FULL100_SEED_VALIDATION_PATH) if FULL100_SEED_VALIDATION_PATH.exists() else {}
    full100_annotation_seed_ready = (
        full100_seed_validation.get("num_failures") == 0
        and full100_seed_validation.get("annotated_question_count") == 5
        and full100_seed_validation.get("span_count") == 18
    )
    full100_draft_report = load_json(FULL100_DRAFT_REPORT_PATH) if FULL100_DRAFT_REPORT_PATH.exists() else {}
    full100_draft_validation = load_json(FULL100_DRAFT_VALIDATION_PATH) if FULL100_DRAFT_VALIDATION_PATH.exists() else {}
    full100_annotation_draft_ready = (
        full100_draft_validation.get("num_failures") == 0
        and full100_draft_validation.get("annotated_question_count") == 35
        and full100_draft_validation.get("span_count") == 205
    )
    full100_consistency_audit_report = (
        load_json(FULL100_CONSISTENCY_AUDIT_REPORT_PATH) if FULL100_CONSISTENCY_AUDIT_REPORT_PATH.exists() else {}
    )
    full100_consistency_audit_ready = (
        full100_consistency_audit_report.get("ready_for_alignment") is True
        and full100_consistency_audit_report.get("num_failures") == 0
        and full100_consistency_audit_report.get("annotated_question_count") == 35
        and full100_consistency_audit_report.get("span_count") == 205
    )
    full100_alignment_report = load_json(FULL100_ALIGNMENT_REPORT_PATH) if FULL100_ALIGNMENT_REPORT_PATH.exists() else {}
    full100_alignment_validation = (
        load_json(FULL100_ALIGNMENT_VALIDATION_PATH) if FULL100_ALIGNMENT_VALIDATION_PATH.exists() else {}
    )
    full100_span_token_alignment_ready = (
        full100_alignment_validation.get("num_failures") == 0
        and full100_alignment_validation.get("ready_for_scoring_prep") is True
        and full100_alignment_validation.get("span_count") == 205
        and full100_alignment_validation.get("question_count") == 35
        and full100_alignment_report.get("ready_for_simple_logit_baselines") is True
        and full100_alignment_report.get("ready_for_energy_baselines") is True
    )
    full100_audit_note_review_report = (
        load_json(FULL100_AUDIT_NOTE_REVIEW_REPORT_PATH) if FULL100_AUDIT_NOTE_REVIEW_REPORT_PATH.exists() else {}
    )
    full100_audit_note_review_validation = (
        load_json(FULL100_AUDIT_NOTE_REVIEW_VALIDATION_PATH)
        if FULL100_AUDIT_NOTE_REVIEW_VALIDATION_PATH.exists()
        else {}
    )
    full100_audit_note_review_ready = (
        full100_audit_note_review_validation.get("num_failures") == 0
        and full100_audit_note_review_validation.get("review_notes_resolved") is True
        and full100_audit_note_review_report.get("reviewed_question_count") == 4
        and full100_audit_note_review_report.get("label_change_count") == 1
    )
    full100_detector_scores_report = (
        load_json(FULL100_DETECTOR_SCORES_REPORT_PATH) if FULL100_DETECTOR_SCORES_REPORT_PATH.exists() else {}
    )
    full100_detector_scores_validation = (
        load_json(FULL100_DETECTOR_SCORES_VALIDATION_PATH) if FULL100_DETECTOR_SCORES_VALIDATION_PATH.exists() else {}
    )
    full100_detector_scores_ready = (
        full100_detector_scores_validation.get("num_failures") == 0
        and full100_detector_scores_validation.get("ready_for_split_safe_metrics") is True
        and full100_detector_scores_validation.get("row_count") == 205
        and full100_detector_scores_validation.get("question_count") == 35
        and full100_detector_scores_validation.get("metrics_reported") is False
        and full100_detector_scores_report.get("ready_for_score_validation") is True
        and full100_detector_scores_report.get("metrics_reported") is False
    )
    full100_simple_split_report = (
        load_json(FULL100_SIMPLE_SPLIT_REPORT_PATH) if FULL100_SIMPLE_SPLIT_REPORT_PATH.exists() else {}
    )
    full100_simple_split_validation = (
        load_json(FULL100_SIMPLE_SPLIT_VALIDATION_PATH) if FULL100_SIMPLE_SPLIT_VALIDATION_PATH.exists() else {}
    )
    full100_simple_split_metrics_ready = (
        FULL100_SIMPLE_SPLIT_METRICS_PATH.exists()
        and full100_simple_split_validation.get("num_failures") == 0
        and full100_simple_split_validation.get("metric_row_count") == 10
        and full100_simple_split_validation.get("baseline_count") == 5
        and full100_simple_split_report.get("baseline_family") == "simple"
        and full100_simple_split_report.get("ready_for_split_metrics") is True
        and full100_simple_split_report.get("row_count") == 205
        and full100_simple_split_report.get("dev_row_count") == 102
        and full100_simple_split_report.get("test_row_count") == 103
    )
    full100_energy_split_report = (
        load_json(FULL100_ENERGY_SPLIT_REPORT_PATH) if FULL100_ENERGY_SPLIT_REPORT_PATH.exists() else {}
    )
    full100_energy_split_validation = (
        load_json(FULL100_ENERGY_SPLIT_VALIDATION_PATH) if FULL100_ENERGY_SPLIT_VALIDATION_PATH.exists() else {}
    )
    full100_energy_split_metrics_ready = (
        FULL100_ENERGY_SPLIT_METRICS_PATH.exists()
        and full100_energy_split_validation.get("num_failures") == 0
        and full100_energy_split_validation.get("metric_row_count") == 14
        and full100_energy_split_validation.get("baseline_count") == 7
        and full100_energy_split_report.get("baseline_family") == "energy"
        and full100_energy_split_report.get("ready_for_split_metrics") is True
        and full100_energy_split_report.get("row_count") == 205
        and full100_energy_split_report.get("dev_row_count") == 102
        and full100_energy_split_report.get("test_row_count") == 103
    )
    full100_family_comparison_report = (
        load_json(FULL100_FAMILY_COMPARISON_REPORT_PATH) if FULL100_FAMILY_COMPARISON_REPORT_PATH.exists() else {}
    )
    full100_family_comparison_validation = (
        load_json(FULL100_FAMILY_COMPARISON_VALIDATION_PATH) if FULL100_FAMILY_COMPARISON_VALIDATION_PATH.exists() else {}
    )
    full100_family_comparison_ready = (
        full100_family_comparison_validation.get("num_failures") == 0
        and full100_family_comparison_validation.get("row_count") == 12
        and full100_family_comparison_validation.get("summary_row_count") == 2
        and full100_family_comparison_validation.get("ready_for_interpretation_review") is True
        and full100_family_comparison_report.get("ready_for_interpretation_review") is True
        and full100_family_comparison_report.get("comparison_row_count") == 12
        and full100_family_comparison_report.get("summary_row_count") == 2
    )
    full100_error_review_report = load_json(FULL100_ERROR_REVIEW_REPORT_PATH) if FULL100_ERROR_REVIEW_REPORT_PATH.exists() else {}
    full100_error_review_validation = (
        load_json(FULL100_ERROR_REVIEW_VALIDATION_PATH) if FULL100_ERROR_REVIEW_VALIDATION_PATH.exists() else {}
    )
    full100_error_review_ready = (
        full100_error_review_validation.get("num_failures") == 0
        and full100_error_review_validation.get("ready_for_error_pattern_review") is True
        and full100_error_review_validation.get("selected_baseline_count") == 2
        and full100_error_review_validation.get("error_row_count") == full100_error_review_report.get("error_row_count")
        and full100_error_review_report.get("review_scope") == "heldout_test_split_only"
        and full100_error_review_report.get("ready_for_error_pattern_review") is True
    )
    full100_interpretation_summary = (
        load_json(FULL100_INTERPRETATION_SUMMARY_PATH) if FULL100_INTERPRETATION_SUMMARY_PATH.exists() else {}
    )
    full100_interpretation_validation = (
        load_json(FULL100_INTERPRETATION_VALIDATION_PATH) if FULL100_INTERPRETATION_VALIDATION_PATH.exists() else {}
    )
    full100_interpretation_ready = (
        full100_interpretation_validation.get("num_failures") == 0
        and full100_interpretation_validation.get("ready_for_presentation_label_confirmation") is True
        and full100_interpretation_summary.get("status") == "report_ready_draft"
        and full100_interpretation_summary.get("error_row_count") == full100_error_review_report.get("error_row_count")
    )
    full100_label_confirmation_packet_summary = (
        load_json(FULL100_LABEL_CONFIRMATION_PACKET_SUMMARY_PATH)
        if FULL100_LABEL_CONFIRMATION_PACKET_SUMMARY_PATH.exists()
        else {}
    )
    full100_label_confirmation_packet_validation = (
        load_json(FULL100_LABEL_CONFIRMATION_PACKET_VALIDATION_PATH)
        if FULL100_LABEL_CONFIRMATION_PACKET_VALIDATION_PATH.exists()
        else {}
    )
    full100_label_confirmation_packet_ready = (
        full100_label_confirmation_packet_validation.get("num_failures") == 0
        and full100_label_confirmation_packet_validation.get("ready_for_human_confirmation") is True
        and full100_label_confirmation_packet_validation.get("labels_locked") is False
        and full100_label_confirmation_packet_summary.get("status") == "confirmation_packet_ready_not_locked"
        and full100_label_confirmation_packet_summary.get("selected_annotation_count") == 15
        and full100_label_confirmation_packet_summary.get("source_error_example_row_count") == 20
        and full100_label_confirmation_packet_summary.get("human_confirmation_required") is True
    )
    full100_label_confirmation_review_notes_summary = (
        load_json(FULL100_LABEL_CONFIRMATION_REVIEW_NOTES_SUMMARY_PATH)
        if FULL100_LABEL_CONFIRMATION_REVIEW_NOTES_SUMMARY_PATH.exists()
        else {}
    )
    full100_label_confirmation_review_notes_validation = (
        load_json(FULL100_LABEL_CONFIRMATION_REVIEW_NOTES_VALIDATION_PATH)
        if FULL100_LABEL_CONFIRMATION_REVIEW_NOTES_VALIDATION_PATH.exists()
        else {}
    )
    full100_label_confirmation_review_notes_ready = (
        full100_label_confirmation_review_notes_validation.get("num_failures") == 0
        and full100_label_confirmation_review_notes_validation.get("assistant_review_complete") is True
        and full100_label_confirmation_review_notes_validation.get("human_confirmation_required") is True
        and full100_label_confirmation_review_notes_validation.get("labels_locked") is False
        and full100_label_confirmation_review_notes_summary.get("status") == "assistant_review_complete_not_human_locked"
        and full100_label_confirmation_review_notes_summary.get("selected_annotation_count") == 15
        and full100_label_confirmation_review_notes_summary.get("source_fix_required_count") == 0
        and full100_label_confirmation_review_notes_summary.get("human_confirmation_required") is True
        and full100_label_confirmation_review_notes_summary.get("labels_locked") is False
    )
    full100_label_lock_summary = (
        load_json(FULL100_LABEL_LOCK_SUMMARY_PATH) if FULL100_LABEL_LOCK_SUMMARY_PATH.exists() else {}
    )
    full100_label_lock_validation = (
        load_json(FULL100_LABEL_LOCK_VALIDATION_PATH) if FULL100_LABEL_LOCK_VALIDATION_PATH.exists() else {}
    )
    full100_label_lock_ready = (
        full100_label_lock_validation.get("num_failures") == 0
        and full100_label_lock_validation.get("labels_locked") is True
        and full100_label_lock_validation.get("ready_for_portfolio_packaging") is True
        and full100_label_lock_validation.get("lock_basis") == "assistant_full_review"
        and full100_label_lock_validation.get("selected_annotation_count") == 15
        and full100_label_lock_summary.get("status") == "presentation_labels_locked"
        and full100_label_lock_summary.get("review_status") == "locked_after_assistant_full_review"
        and full100_label_lock_summary.get("labels_locked") is True
        and full100_label_lock_summary.get("human_confirmation_required") is False
        and full100_label_lock_summary.get("source_fix_required_count") == 0
        and full100_label_lock_summary.get("locked_label_count") == 15
    )
    portfolio_demo_summary = load_json(PORTFOLIO_DEMO_SUMMARY_PATH) if PORTFOLIO_DEMO_SUMMARY_PATH.exists() else {}
    portfolio_demo_validation = (
        load_json(PORTFOLIO_DEMO_VALIDATION_PATH) if PORTFOLIO_DEMO_VALIDATION_PATH.exists() else {}
    )
    portfolio_demo_ready = (
        portfolio_demo_validation.get("num_failures") == 0
        and portfolio_demo_validation.get("ready_for_portfolio_demo") is True
        and portfolio_demo_validation.get("case_count") == 2
        and portfolio_demo_validation.get("locked_primary_span_count") == 7
        and portfolio_demo_summary.get("status") == "portfolio_demo_ready"
        and portfolio_demo_summary.get("primary_question_ids") == ["q_0064", "q_0069"]
        and portfolio_demo_summary.get("label_lock_status") == "presentation_labels_locked"
        and portfolio_demo_summary.get("label_lock_basis") == "assistant_full_review"
        and portfolio_demo_summary.get("labels_locked") is True
    )
    portfolio_narrative_summary = (
        load_json(PORTFOLIO_NARRATIVE_SUMMARY_PATH) if PORTFOLIO_NARRATIVE_SUMMARY_PATH.exists() else {}
    )
    portfolio_narrative_validation = (
        load_json(PORTFOLIO_NARRATIVE_VALIDATION_PATH) if PORTFOLIO_NARRATIVE_VALIDATION_PATH.exists() else {}
    )
    portfolio_narrative_ready = (
        portfolio_narrative_validation.get("num_failures") == 0
        and portfolio_narrative_validation.get("ready_for_portfolio_narrative") is True
        and portfolio_narrative_summary.get("status") == "portfolio_narrative_ready"
        and portfolio_narrative_summary.get("primary_question_ids") == ["q_0064", "q_0069"]
        and portfolio_narrative_summary.get("question_count") == 100
        and portfolio_narrative_summary.get("annotated_span_count") == 205
        and portfolio_narrative_summary.get("best_test_auprc") == 0.835073
        and portfolio_narrative_summary.get("best_test_f1") == 0.779412
        and portfolio_narrative_summary.get("label_lock_basis") == "assistant_full_review"
        and portfolio_narrative_summary.get("labels_locked") is True
    )
    github_pages_manifest = load_json(GITHUB_PAGES_MANIFEST_PATH) if GITHUB_PAGES_MANIFEST_PATH.exists() else {}
    github_pages_validation = load_json(GITHUB_PAGES_VALIDATION_PATH) if GITHUB_PAGES_VALIDATION_PATH.exists() else {}
    github_pages_ready = (
        github_pages_validation.get("num_failures") == 0
        and github_pages_validation.get("ready_for_github_pages") is True
        and github_pages_manifest.get("status") == "github_pages_bundle_ready"
        and github_pages_manifest.get("current_stage") == "github_pages_ready"
        and github_pages_manifest.get("primary_question_ids") == ["q_0064", "q_0069"]
        and github_pages_manifest.get("question_count") == 100
        and github_pages_manifest.get("annotated_span_count") == 205
        and github_pages_manifest.get("locked_primary_span_count") == 7
        and github_pages_manifest.get("best_test_auprc") == 0.835073
        and github_pages_manifest.get("best_test_f1") == 0.779412
        and github_pages_manifest.get("label_lock_basis") == "assistant_full_review"
    )

    failures: list[dict[str, Any]] = []
    for check in checks:
        if not check["passed"]:
            failures.append({"name": check["name"], "reason": "validation check failed", "detail": check})

    if not detector_config_path.exists():
        failures.append({"name": "detector_baseline_suite", "reason": "missing detector baseline suite config"})
        detector_config = {}
    else:
        detector_config = load_json(detector_config_path)

    if not full100_config_path.exists():
        failures.append({"name": "full100_config", "reason": "missing full100 config"})
        full100_config = {}
    else:
        full100_config = load_json(full100_config_path)

    if not split_guard_path.exists():
        failures.append({"name": "train_only_split_guard", "reason": "missing train-only guard report"})
        split_guard = {}
    else:
        split_guard = load_json(split_guard_path)
        expected_guard = (
            split_guard.get("ready_for_split_metrics") is False
            and split_guard.get("split_counts") == {"train": 135}
            and split_guard.get("num_failures") == 2
        )
        if not expected_guard:
            failures.append(
                {
                    "name": "train_only_split_guard",
                    "reason": "guard did not reject train-only pilot scores as expected",
                    "detail": split_guard,
                }
            )

    if not detector_summary_path.exists():
        failures.append({"name": "detector_readiness_summary", "reason": "missing detector readiness summary"})
        detector_summary = {}
    else:
        detector_summary = load_json(detector_summary_path)
        readiness = detector_summary.get("readiness", {})
        required_flags = {
            "trace_capture_ready": True,
            "span_alignment_ready": True,
            "energy_adapter_operational": True,
            "split_evaluation_ready": True,
            "full100_config_ready": True,
            "full100_generation_run": full100_generation_run,
        }
        for flag, expected in required_flags.items():
            if readiness.get(flag) is not expected:
                failures.append(
                    {
                        "name": "detector_readiness_summary",
                        "reason": f"unexpected readiness flag {flag}",
                        "expected": expected,
                        "actual": readiness.get(flag),
                    }
                )

    full100_validation = load_json(OUTPUT_DIR / "full100_config_validation.json") if (OUTPUT_DIR / "full100_config_validation.json").exists() else {}
    split_eval_smoke = load_json(RESULTS_DIR / "split_eval_smoke_report.json") if (RESULTS_DIR / "split_eval_smoke_report.json").exists() else {}
    detector_families = detector_config.get("families", {})

    if full100_generation_run:
        if full100_run_validation.get("num_failures") != 0:
            failures.append(
                {
                    "name": "full100_generation_validation",
                    "reason": "full100 generation validation has failures",
                    "detail": full100_run_validation.get("failures"),
                }
            )
        if full100_run_validation.get("record_count") != 100 or full100_run_validation.get("trace_count") != 100:
            failures.append(
                {
                    "name": "full100_generation_validation",
                    "reason": "unexpected full100 record or trace count",
                    "record_count": full100_run_validation.get("record_count"),
                    "trace_count": full100_run_validation.get("trace_count"),
                }
            )
        if full100_run_report.get("record_count") not in {None, 100}:
            failures.append(
                {
                    "name": "full100_generation_report",
                    "reason": "unexpected full100 report record count",
                    "record_count": full100_run_report.get("record_count"),
                }
            )
    if FULL100_REVIEW_VALIDATION_PATH.exists() and not full100_review_ready:
        failures.append(
            {
                "name": "full100_review_validation",
                "reason": "full100 review validation is not clean",
                "detail": full100_review_validation,
            }
        )
    if FULL100_QUEUE_VALIDATION_PATH.exists() and not full100_annotation_queue_ready:
        failures.append(
            {
                "name": "full100_annotation_queue_validation",
                "reason": "full100 annotation queue validation is not clean",
                "detail": full100_queue_validation,
            }
        )
    if FULL100_SEED_VALIDATION_PATH.exists() and not full100_annotation_seed_ready:
        failures.append(
            {
                "name": "full100_annotation_seed_validation",
                "reason": "full100 annotation seed validation is not clean",
                "detail": full100_seed_validation,
            }
        )
    if FULL100_DRAFT_VALIDATION_PATH.exists() and not full100_annotation_draft_ready:
        failures.append(
            {
                "name": "full100_annotation_draft_validation",
                "reason": "full100 annotation draft validation is not clean",
                "detail": full100_draft_validation,
            }
        )
    if full100_annotation_draft_ready and not FULL100_CONSISTENCY_AUDIT_REPORT_PATH.exists():
        failures.append(
            {
                "name": "full100_annotation_consistency_audit",
                "reason": "missing consistency audit for the 35-question draft",
            }
        )
    if FULL100_CONSISTENCY_AUDIT_REPORT_PATH.exists() and not full100_consistency_audit_ready:
        failures.append(
            {
                "name": "full100_annotation_consistency_audit",
                "reason": "full100 annotation consistency audit is not ready for alignment",
                "detail": full100_consistency_audit_report,
            }
        )
    if full100_consistency_audit_ready and not FULL100_ALIGNMENT_VALIDATION_PATH.exists():
        failures.append(
            {
                "name": "full100_span_token_alignment",
                "reason": "missing full100 draft span-token alignment validation",
            }
        )
    if FULL100_ALIGNMENT_VALIDATION_PATH.exists() and not full100_span_token_alignment_ready:
        failures.append(
            {
                "name": "full100_span_token_alignment",
                "reason": "full100 draft span-token alignment is not ready",
                "detail": full100_alignment_validation,
            }
        )
    if full100_span_token_alignment_ready and not FULL100_AUDIT_NOTE_REVIEW_VALIDATION_PATH.exists():
        failures.append(
            {
                "name": "full100_audit_note_review",
                "reason": "missing audit-note review validation",
            }
        )
    if FULL100_AUDIT_NOTE_REVIEW_VALIDATION_PATH.exists() and not full100_audit_note_review_ready:
        failures.append(
            {
                "name": "full100_audit_note_review",
                "reason": "full100 audit-note review is not resolved",
                "detail": full100_audit_note_review_validation,
            }
        )
    if full100_audit_note_review_ready and not FULL100_DETECTOR_SCORES_VALIDATION_PATH.exists():
        failures.append(
            {
                "name": "full100_detector_scores",
                "reason": "missing full100 draft detector score-file validation",
            }
        )
    if FULL100_DETECTOR_SCORES_VALIDATION_PATH.exists() and not full100_detector_scores_ready:
        failures.append(
            {
                "name": "full100_detector_scores",
                "reason": "full100 draft detector score files are not ready",
                "detail": full100_detector_scores_validation,
            }
        )
    if full100_detector_scores_ready and not FULL100_SIMPLE_SPLIT_VALIDATION_PATH.exists():
        failures.append(
            {
                "name": "full100_simple_split_metrics",
                "reason": "missing full100 simple split-metric validation",
            }
        )
    if FULL100_SIMPLE_SPLIT_VALIDATION_PATH.exists() and not full100_simple_split_metrics_ready:
        failures.append(
            {
                "name": "full100_simple_split_metrics",
                "reason": "full100 simple split metrics are not ready",
                "detail": full100_simple_split_validation,
            }
        )
    if full100_simple_split_metrics_ready and not FULL100_ENERGY_SPLIT_VALIDATION_PATH.exists():
        failures.append(
            {
                "name": "full100_energy_split_metrics",
                "reason": "missing full100 energy split-metric validation",
            }
        )
    if FULL100_ENERGY_SPLIT_VALIDATION_PATH.exists() and not full100_energy_split_metrics_ready:
        failures.append(
            {
                "name": "full100_energy_split_metrics",
                "reason": "full100 energy split metrics are not ready",
                "detail": full100_energy_split_validation,
            }
        )
    if full100_energy_split_metrics_ready and not FULL100_FAMILY_COMPARISON_VALIDATION_PATH.exists():
        failures.append(
            {
                "name": "full100_detector_family_comparison",
                "reason": "missing full100 detector family comparison validation",
            }
        )
    if FULL100_FAMILY_COMPARISON_VALIDATION_PATH.exists() and not full100_family_comparison_ready:
        failures.append(
            {
                "name": "full100_detector_family_comparison",
                "reason": "full100 detector family comparison is not ready",
                "detail": full100_family_comparison_validation,
            }
        )
    if full100_family_comparison_ready and not FULL100_ERROR_REVIEW_VALIDATION_PATH.exists():
        failures.append(
            {
                "name": "full100_detector_error_review",
                "reason": "missing full100 detector error-review validation",
            }
        )
    if FULL100_ERROR_REVIEW_VALIDATION_PATH.exists() and not full100_error_review_ready:
        failures.append(
            {
                "name": "full100_detector_error_review",
                "reason": "full100 detector error review is not ready",
                "detail": full100_error_review_validation,
            }
        )
    if full100_error_review_ready and not FULL100_INTERPRETATION_VALIDATION_PATH.exists():
        failures.append(
            {
                "name": "full100_detector_interpretation",
                "reason": "missing full100 detector interpretation validation",
            }
        )
    if FULL100_INTERPRETATION_VALIDATION_PATH.exists() and not full100_interpretation_ready:
        failures.append(
            {
                "name": "full100_detector_interpretation",
                "reason": "full100 detector interpretation is not ready",
                "detail": full100_interpretation_validation,
            }
        )
    if full100_interpretation_ready and not FULL100_LABEL_CONFIRMATION_PACKET_VALIDATION_PATH.exists():
        failures.append(
            {
                "name": "full100_label_confirmation_packet",
                "reason": "missing full100 label-confirmation packet validation",
            }
        )
    if FULL100_LABEL_CONFIRMATION_PACKET_VALIDATION_PATH.exists() and not full100_label_confirmation_packet_ready:
        failures.append(
            {
                "name": "full100_label_confirmation_packet",
                "reason": "full100 label-confirmation packet is not ready",
                "detail": full100_label_confirmation_packet_validation,
            }
        )
    if (
        FULL100_LABEL_CONFIRMATION_REVIEW_NOTES_VALIDATION_PATH.exists()
        and not full100_label_confirmation_review_notes_ready
    ):
        failures.append(
            {
                "name": "full100_label_confirmation_review_notes",
                "reason": "full100 label-confirmation review notes are not ready",
                "detail": full100_label_confirmation_review_notes_validation,
            }
        )
    if FULL100_LABEL_LOCK_VALIDATION_PATH.exists() and not full100_label_lock_ready:
        failures.append(
            {
                "name": "full100_label_lock",
                "reason": "full100 label lock package is not ready",
                "detail": full100_label_lock_validation,
            }
        )
    if PORTFOLIO_DEMO_VALIDATION_PATH.exists() and not portfolio_demo_ready:
        failures.append(
            {
                "name": "portfolio_demo",
                "reason": "portfolio demo package is not ready",
                "detail": portfolio_demo_validation,
            }
        )
    if PORTFOLIO_NARRATIVE_VALIDATION_PATH.exists() and not portfolio_narrative_ready:
        failures.append(
            {
                "name": "portfolio_narrative",
                "reason": "portfolio narrative package is not ready",
                "detail": portfolio_narrative_validation,
            }
        )
    if GITHUB_PAGES_VALIDATION_PATH.exists() and not github_pages_ready:
        failures.append(
            {
                "name": "github_pages_bundle",
                "reason": "GitHub Pages bundle is not ready",
                "detail": github_pages_validation,
            }
        )

    if github_pages_ready:
        remaining_after_full100_generation = [
            "Keep docs/index.html as the GitHub Pages entry point and reports/ as the experiment-native report archive.",
            "Use the linked 10-slide interview deck for concise portfolio walkthroughs.",
            "Keep large raw data, model traces, model weights, and external baseline repositories out of the public commit.",
        ]
    elif portfolio_narrative_ready:
        remaining_after_full100_generation = [
            "Decide whether the next deliverable should be a slide deck or a small interactive app.",
            "Use the narrative page as the source of truth for resume, LinkedIn, and interview wording.",
            "Keep claims span-level and avoid implying whole-answer correctness.",
        ]
    elif portfolio_demo_ready:
        remaining_after_full100_generation = [
            "Polish the final written portfolio narrative around q_0064 and q_0069.",
            "Decide whether to build a short slide deck or a small interactive app from the static demo.",
            "Keep claims span-level and avoid implying whole-answer correctness.",
        ]
    elif full100_label_lock_ready:
        remaining_after_full100_generation = [
            "Build the final portfolio/demo page around q_0064 and q_0069.",
            "Package label-lock, detector interpretation, and selected examples into a public-facing narrative.",
            "Keep full-answer correctness separate from span-level detector claims.",
        ]
    elif full100_label_confirmation_review_notes_ready:
        remaining_after_full100_generation = [
            "Use the review notes to choose final portfolio examples, prioritizing q_0064 and q_0069.",
            "Build the assistant-reviewed label lock package before publishing final public claims.",
            "Package the detector interpretation, confirmation packet, and review notes into a portfolio/demo page.",
        ]
    elif full100_label_confirmation_packet_ready:
        remaining_after_full100_generation = [
            "Build presentation-level review notes for the 15 selected confirmation items.",
            "Manually review the 15 selected confirmation items and update any source annotation if needed.",
            "After human confirmation, decide whether to lock the draft held-out labels for portfolio use.",
            "Package the detector interpretation and confirmation packet into the portfolio/demo narrative.",
        ]
    elif full100_interpretation_ready:
        remaining_after_full100_generation = [
            "Confirm presentation-level labels for the 35 held-out high-priority questions.",
            "Package the detector interpretation page into the portfolio/demo narrative.",
            "Decide whether to add a small interactive demo before freezing public claims.",
        ]
    elif full100_error_review_ready:
        remaining_after_full100_generation = [
            "Write a report-ready interpretation summary that separates AUPRC ranking, F1 tradeoffs, and all-positive-like energy controls.",
            "Keep public/report claims draft until the reviewed labels are confirmed for presentation.",
        ]
    elif full100_family_comparison_ready:
        remaining_after_full100_generation = [
            "Build a full100 detector error review for the best simple and energy baselines.",
            "Inspect false positives and false negatives before writing detector-family claims.",
            "Keep public/report claims draft until the reviewed labels are confirmed for presentation.",
        ]
    elif full100_energy_split_metrics_ready:
        remaining_after_full100_generation = [
            "Build simple-vs-energy detector family comparison artifacts.",
            "Inspect all-positive-like energy thresholds before interpreting energy results.",
            "Keep public/report claims draft until the reviewed labels are confirmed for presentation.",
        ]
    elif full100_simple_split_metrics_ready:
        remaining_after_full100_generation = [
            "Run split-safe energy-suite detector evaluation from the validated full100 score file.",
            "Validate energy metric outputs before comparing simple and energy families.",
            "Compare simple vs energy test metrics and inspect error examples before writing public claims.",
            "Keep public/report claims draft until the reviewed labels are confirmed for presentation.",
        ]
    elif full100_detector_scores_ready:
        remaining_after_full100_generation = [
            "Run split-safe detector evaluation with thresholds selected on dev and reported on held-out test.",
            "Validate split-safe metric outputs before interpreting any detector result.",
            "Keep public/report claims draft until the reviewed labels are confirmed for presentation.",
        ]
    elif full100_audit_note_review_ready:
        remaining_after_full100_generation = [
            "Build full100 detector score files from the aligned spans without reporting final metrics yet.",
            "Validate score files by split before running split-safe metrics.",
            "Run split-safe detector evaluation with thresholds selected on dev and reported on test.",
            "Keep public/report claims draft until the reviewed labels are confirmed for presentation.",
        ]
    elif full100_span_token_alignment_ready:
        remaining_after_full100_generation = [
            "Review the 4 consistency-audit notes before treating draft labels as final.",
            "Build full100 detector score files from the aligned spans without reporting final metrics yet.",
            "Run split-safe detector evaluation only after label-review notes are resolved.",
            "Select thresholds on dev and report held-out test metrics.",
        ]
    elif full100_consistency_audit_ready:
        remaining_after_full100_generation = [
            "Build full100 span-token alignment for the 205 draft spans.",
            "Use the consistency-audit review notes when doing the final human label review.",
            "Score full100 spans only after alignment and label review are complete.",
            "Run split-safe detector evaluation with thresholds selected on dev and reported on test.",
        ]
    elif full100_annotation_draft_ready:
        remaining_after_full100_generation = [
            "Run the 35-question draft consistency audit before span-token alignment.",
            "Build full100 span-token alignment for the annotated dev/test spans.",
            "Score full100 spans only after the 35-question draft labels are reviewed.",
            "Run split-safe detector evaluation with thresholds selected on dev and reported on test.",
        ]
    elif full100_annotation_seed_ready:
        remaining_after_full100_generation = [
            "Use the policy-reviewed 5-question seed as the template for scaling.",
            "Extend span annotation to the remaining heldout high-priority rows.",
            "Score full100 spans only after dev/test span labels are complete.",
            "Run split-safe detector evaluation with thresholds selected on dev and reported on test.",
        ]
    elif full100_annotation_queue_ready:
        remaining_after_full100_generation = [
            "Annotate full100 spans from the heldout high-priority annotation batch.",
            "Score full100 spans with simple and energy baseline families.",
            "Run split-safe detector evaluation with thresholds selected on dev and reported on test.",
        ]
    elif full100_review_ready:
        remaining_after_full100_generation = [
            "Build full100 annotation queue from the validated review table.",
            "Score full100 spans with simple and energy baseline families.",
            "Run split-safe detector evaluation with thresholds selected on dev and reported on test.",
        ]
    else:
        remaining_after_full100_generation = [
            "Build full100 review and annotation artifacts.",
            "Score full100 spans with simple and energy baseline families.",
            "Run split-safe detector evaluation with thresholds selected on dev and reported on test.",
        ]

    if github_pages_ready:
        current_stage = "github_pages_ready"
    elif portfolio_narrative_ready:
        current_stage = "portfolio_narrative_ready"
    elif portfolio_demo_ready:
        current_stage = "portfolio_demo_ready"
    elif full100_label_lock_ready:
        current_stage = "presentation_labels_locked"
    elif full100_label_confirmation_review_notes_ready:
        current_stage = "presentation_label_review_notes_ready"
    elif full100_label_confirmation_packet_ready:
        current_stage = "presentation_label_confirmation_packet_ready"
    else:
        current_stage = "preflight_incomplete"
    ready_for_current_stage = len(failures) == 0 and (
        github_pages_ready
        or portfolio_narrative_ready
        or portfolio_demo_ready
        or full100_label_lock_ready
        or full100_label_confirmation_review_notes_ready
        or full100_label_confirmation_packet_ready
    )
    legacy_ready_to_run_full100_generation = len(failures) == 0

    report = {
        "current_stage": current_stage,
        "ready_for_current_stage": ready_for_current_stage,
        "checks": checks,
        "detector_baseline_suite_path": str(detector_config_path),
        "detector_families": {name: len(items) for name, items in sorted(detector_families.items())},
        "full100_config_path": str(full100_config_path),
        "full100_question_count": len(full100_config.get("question_ids", [])),
        "full100_split_counts": full100_validation.get("split_counts"),
        "full100_generation_command": full100_config.get("generation_command"),
        "split_eval_smoke": {
            "path": str(RESULTS_DIR / "split_eval_smoke_report.json"),
            "ready_for_split_metrics": split_eval_smoke.get("ready_for_split_metrics"),
            "dev_row_count": split_eval_smoke.get("dev_row_count"),
            "test_row_count": split_eval_smoke.get("test_row_count"),
        },
        "full100_generation": {
            "run": full100_generation_run,
            "report_path": str(FULL100_RUN_REPORT_PATH),
            "validation_path": str(FULL100_RUN_VALIDATION_PATH),
            "validation_num_failures": full100_run_validation.get("num_failures"),
            "record_count": full100_run_validation.get("record_count"),
            "trace_count": full100_run_validation.get("trace_count"),
            "total_generated_tokens": full100_run_report.get("total_generated_tokens"),
            "total_elapsed_seconds": full100_run_report.get("total_elapsed_seconds"),
        },
        "full100_review": {
            "ready": full100_review_ready,
            "report_path": str(FULL100_REVIEW_REPORT_PATH),
            "validation_path": str(FULL100_REVIEW_VALIDATION_PATH),
            "validation_num_failures": full100_review_validation.get("num_failures"),
            "record_count": full100_review_validation.get("record_count"),
            "jsonl_record_count": full100_review_validation.get("jsonl_record_count"),
            "sample_record_count": full100_review_validation.get("sample_record_count"),
            "auto_status_counts": full100_review_report.get("auto_status_counts"),
            "annotation_priority_counts": full100_review_report.get("annotation_priority_counts"),
        },
        "full100_annotation_queue": {
            "ready": full100_annotation_queue_ready,
            "report_path": str(FULL100_QUEUE_REPORT_PATH),
            "validation_path": str(FULL100_QUEUE_VALIDATION_PATH),
            "validation_num_failures": full100_queue_validation.get("num_failures"),
            "record_count": full100_queue_validation.get("record_count"),
            "initial_batch_count": full100_queue_validation.get("initial_batch_count"),
            "phase_counts": full100_queue_validation.get("phase_counts"),
            "initial_batch_split_counts": full100_queue_validation.get("initial_batch_split_counts"),
            "target_annotation_file": full100_queue_report.get("target_annotation_file"),
        },
        "full100_annotation_seed": {
            "ready": full100_annotation_seed_ready,
            "report_path": str(FULL100_SEED_REPORT_PATH),
            "validation_path": str(FULL100_SEED_VALIDATION_PATH),
            "validation_num_failures": full100_seed_validation.get("num_failures"),
            "annotated_question_count": full100_seed_validation.get("annotated_question_count"),
            "span_count": full100_seed_validation.get("span_count"),
            "label_counts": full100_seed_validation.get("label_counts"),
            "fact_type_counts": full100_seed_validation.get("fact_type_counts"),
            "status": full100_seed_report.get("status"),
        },
        "full100_annotation_draft": {
            "ready": full100_annotation_draft_ready,
            "report_path": str(FULL100_DRAFT_REPORT_PATH),
            "validation_path": str(FULL100_DRAFT_VALIDATION_PATH),
            "validation_num_failures": full100_draft_validation.get("num_failures"),
            "annotated_question_count": full100_draft_validation.get("annotated_question_count"),
            "span_count": full100_draft_validation.get("span_count"),
            "label_counts": full100_draft_validation.get("label_counts"),
            "fact_type_counts": full100_draft_validation.get("fact_type_counts"),
            "split_counts": full100_draft_report.get("split_counts"),
            "question_type_counts": full100_draft_report.get("question_type_counts"),
            "status": full100_draft_report.get("status"),
        },
        "full100_annotation_consistency_audit": {
            "ready": full100_consistency_audit_ready,
            "report_path": str(FULL100_CONSISTENCY_AUDIT_REPORT_PATH),
            "status": full100_consistency_audit_report.get("status"),
            "ready_for_alignment": full100_consistency_audit_report.get("ready_for_alignment"),
            "num_failures": full100_consistency_audit_report.get("num_failures"),
            "num_warnings": full100_consistency_audit_report.get("num_warnings"),
            "next_allowed_step": full100_consistency_audit_report.get("next_allowed_step"),
        },
        "full100_span_token_alignment": {
            "ready": full100_span_token_alignment_ready,
            "report_path": str(FULL100_ALIGNMENT_REPORT_PATH),
            "validation_path": str(FULL100_ALIGNMENT_VALIDATION_PATH),
            "validation_num_failures": full100_alignment_validation.get("num_failures"),
            "span_count": full100_alignment_validation.get("span_count"),
            "question_count": full100_alignment_validation.get("question_count"),
            "split_counts": full100_alignment_validation.get("split_counts"),
            "ready_for_scoring_prep": full100_alignment_validation.get("ready_for_scoring_prep"),
            "metrics_reported": full100_alignment_validation.get("metrics_reported"),
            "token_count_summary": full100_alignment_validation.get("token_count_summary"),
            "boundary_slop_summary": full100_alignment_validation.get("boundary_slop_summary"),
        },
        "full100_audit_note_review": {
            "ready": full100_audit_note_review_ready,
            "report_path": str(FULL100_AUDIT_NOTE_REVIEW_REPORT_PATH),
            "validation_path": str(FULL100_AUDIT_NOTE_REVIEW_VALIDATION_PATH),
            "validation_num_failures": full100_audit_note_review_validation.get("num_failures"),
            "reviewed_question_count": full100_audit_note_review_report.get("reviewed_question_count"),
            "reviewed_question_ids": full100_audit_note_review_report.get("reviewed_question_ids"),
            "label_change_count": full100_audit_note_review_report.get("label_change_count"),
            "remaining_warning_qids_after_review": full100_audit_note_review_report.get("remaining_warning_qids_after_review"),
            "human_confirmation_recommended_before_public_metrics": full100_audit_note_review_report.get(
                "human_confirmation_recommended_before_public_metrics"
            ),
            "metrics_reported": full100_audit_note_review_report.get("metrics_reported"),
        },
        "full100_detector_scores": {
            "ready": full100_detector_scores_ready,
            "scores_path": full100_detector_scores_report.get("scores_path"),
            "by_split_path": full100_detector_scores_report.get("by_split_path"),
            "report_path": str(FULL100_DETECTOR_SCORES_REPORT_PATH),
            "validation_path": str(FULL100_DETECTOR_SCORES_VALIDATION_PATH),
            "validation_num_failures": full100_detector_scores_validation.get("num_failures"),
            "row_count": full100_detector_scores_validation.get("row_count"),
            "question_count": full100_detector_scores_validation.get("question_count"),
            "split_counts": full100_detector_scores_validation.get("split_counts"),
            "binary_counts_by_split": full100_detector_scores_validation.get("binary_counts_by_split"),
            "baseline_score_field_count": full100_detector_scores_validation.get("baseline_score_field_count"),
            "ready_for_split_safe_metrics": full100_detector_scores_validation.get("ready_for_split_safe_metrics"),
            "metrics_reported": full100_detector_scores_validation.get("metrics_reported"),
        },
        "full100_simple_split_metrics": {
            "ready": full100_simple_split_metrics_ready,
            "metrics_path": str(FULL100_SIMPLE_SPLIT_METRICS_PATH),
            "report_path": str(FULL100_SIMPLE_SPLIT_REPORT_PATH),
            "validation_path": str(FULL100_SIMPLE_SPLIT_VALIDATION_PATH),
            "validation_num_failures": full100_simple_split_validation.get("num_failures"),
            "baseline_family": full100_simple_split_report.get("baseline_family"),
            "baseline_count": full100_simple_split_validation.get("baseline_count"),
            "metric_row_count": full100_simple_split_validation.get("metric_row_count"),
            "row_count": full100_simple_split_report.get("row_count"),
            "dev_row_count": full100_simple_split_report.get("dev_row_count"),
            "test_row_count": full100_simple_split_report.get("test_row_count"),
            "best_test_by_auprc": full100_simple_split_report.get("best_test_by_auprc"),
            "best_test_by_f1": full100_simple_split_report.get("best_test_by_f1"),
        },
        "full100_energy_split_metrics": {
            "ready": full100_energy_split_metrics_ready,
            "metrics_path": str(FULL100_ENERGY_SPLIT_METRICS_PATH),
            "report_path": str(FULL100_ENERGY_SPLIT_REPORT_PATH),
            "validation_path": str(FULL100_ENERGY_SPLIT_VALIDATION_PATH),
            "validation_num_failures": full100_energy_split_validation.get("num_failures"),
            "baseline_family": full100_energy_split_report.get("baseline_family"),
            "baseline_count": full100_energy_split_validation.get("baseline_count"),
            "metric_row_count": full100_energy_split_validation.get("metric_row_count"),
            "row_count": full100_energy_split_report.get("row_count"),
            "dev_row_count": full100_energy_split_report.get("dev_row_count"),
            "test_row_count": full100_energy_split_report.get("test_row_count"),
            "best_test_by_auprc": full100_energy_split_report.get("best_test_by_auprc"),
            "best_test_by_f1": full100_energy_split_report.get("best_test_by_f1"),
        },
        "full100_detector_family_comparison": {
            "ready": full100_family_comparison_ready,
            "report_path": str(FULL100_FAMILY_COMPARISON_REPORT_PATH),
            "validation_path": str(FULL100_FAMILY_COMPARISON_VALIDATION_PATH),
            "validation_num_failures": full100_family_comparison_validation.get("num_failures"),
            "comparison_row_count": full100_family_comparison_validation.get("row_count"),
            "summary_row_count": full100_family_comparison_validation.get("summary_row_count"),
            "family_counts": full100_family_comparison_validation.get("family_counts"),
            "all_positive_like_count": full100_family_comparison_validation.get("all_positive_like_count"),
            "best_overall_by_test_auprc": full100_family_comparison_report.get("best_overall_by_test_auprc"),
            "best_overall_by_test_f1": full100_family_comparison_report.get("best_overall_by_test_f1"),
            "energy_minus_simple_best_auprc_delta": full100_family_comparison_report.get(
                "energy_minus_simple_best_auprc_delta"
            ),
            "energy_minus_simple_best_f1_delta": full100_family_comparison_report.get("energy_minus_simple_best_f1_delta"),
            "pure_adjacent_step_energy_best_by_test_auprc": full100_family_comparison_report.get(
                "pure_adjacent_step_energy_best_by_test_auprc"
            ),
        },
        "full100_detector_error_review": {
            "ready": full100_error_review_ready,
            "report_path": str(FULL100_ERROR_REVIEW_REPORT_PATH),
            "validation_path": str(FULL100_ERROR_REVIEW_VALIDATION_PATH),
            "validation_num_failures": full100_error_review_validation.get("num_failures"),
            "review_scope": full100_error_review_report.get("review_scope"),
            "selected_baseline_count": full100_error_review_validation.get("selected_baseline_count"),
            "error_row_count": full100_error_review_validation.get("error_row_count"),
            "by_baseline_counts": full100_error_review_validation.get("by_baseline_counts"),
            "top_fact_type_error_counts": full100_error_review_report.get("top_fact_type_error_counts"),
            "top_question_type_error_counts": full100_error_review_report.get("top_question_type_error_counts"),
            "ready_for_error_pattern_review": full100_error_review_validation.get("ready_for_error_pattern_review"),
        },
        "full100_detector_interpretation": {
            "ready": full100_interpretation_ready,
            "summary_path": str(FULL100_INTERPRETATION_SUMMARY_PATH),
            "validation_path": str(FULL100_INTERPRETATION_VALIDATION_PATH),
            "validation_num_failures": full100_interpretation_validation.get("num_failures"),
            "status": full100_interpretation_summary.get("status"),
            "best_overall_by_test_auprc": full100_interpretation_summary.get("best_overall_by_test_auprc"),
            "best_overall_by_test_f1": full100_interpretation_summary.get("best_overall_by_test_f1"),
            "error_row_count": full100_interpretation_summary.get("error_row_count"),
            "ready_for_presentation_label_confirmation": full100_interpretation_validation.get(
                "ready_for_presentation_label_confirmation"
            ),
        },
        "full100_label_confirmation_packet": {
            "ready": full100_label_confirmation_packet_ready,
            "summary_path": str(FULL100_LABEL_CONFIRMATION_PACKET_SUMMARY_PATH),
            "validation_path": str(FULL100_LABEL_CONFIRMATION_PACKET_VALIDATION_PATH),
            "validation_num_failures": full100_label_confirmation_packet_validation.get("num_failures"),
            "status": full100_label_confirmation_packet_summary.get("status"),
            "selected_annotation_count": full100_label_confirmation_packet_summary.get("selected_annotation_count"),
            "selected_question_count": full100_label_confirmation_packet_summary.get("selected_question_count"),
            "source_error_example_row_count": full100_label_confirmation_packet_summary.get(
                "source_error_example_row_count"
            ),
            "ready_for_human_confirmation": full100_label_confirmation_packet_validation.get(
                "ready_for_human_confirmation"
            ),
            "labels_locked": full100_label_confirmation_packet_validation.get("labels_locked"),
        },
        "full100_label_confirmation_review_notes": {
            "ready": full100_label_confirmation_review_notes_ready,
            "summary_path": str(FULL100_LABEL_CONFIRMATION_REVIEW_NOTES_SUMMARY_PATH),
            "validation_path": str(FULL100_LABEL_CONFIRMATION_REVIEW_NOTES_VALIDATION_PATH),
            "validation_num_failures": full100_label_confirmation_review_notes_validation.get("num_failures"),
            "status": full100_label_confirmation_review_notes_summary.get("status"),
            "selected_annotation_count": full100_label_confirmation_review_notes_summary.get(
                "selected_annotation_count"
            ),
            "selected_question_count": full100_label_confirmation_review_notes_summary.get("selected_question_count"),
            "source_fix_required_count": full100_label_confirmation_review_notes_summary.get(
                "source_fix_required_count"
            ),
            "presentation_use_counts": full100_label_confirmation_review_notes_summary.get(
                "presentation_use_counts"
            ),
            "demo_priority_counts": full100_label_confirmation_review_notes_summary.get("demo_priority_counts"),
            "assistant_review_complete": full100_label_confirmation_review_notes_validation.get(
                "assistant_review_complete"
            ),
            "human_confirmation_required": full100_label_confirmation_review_notes_validation.get(
                "human_confirmation_required"
            ),
            "labels_locked": full100_label_confirmation_review_notes_validation.get("labels_locked"),
        },
        "full100_label_lock": {
            "ready": full100_label_lock_ready,
            "summary_path": str(FULL100_LABEL_LOCK_SUMMARY_PATH),
            "validation_path": str(FULL100_LABEL_LOCK_VALIDATION_PATH),
            "validation_num_failures": full100_label_lock_validation.get("num_failures"),
            "status": full100_label_lock_summary.get("status"),
            "review_status": full100_label_lock_summary.get("review_status"),
            "lock_basis": full100_label_lock_summary.get("lock_basis"),
            "selected_annotation_count": full100_label_lock_summary.get("selected_annotation_count"),
            "selected_question_count": full100_label_lock_summary.get("selected_question_count"),
            "locked_label_count": full100_label_lock_summary.get("locked_label_count"),
            "source_fix_required_count": full100_label_lock_summary.get("source_fix_required_count"),
            "by_publish_use": full100_label_lock_summary.get("by_publish_use"),
            "primary_demo_question_ids": full100_label_lock_summary.get("primary_demo_question_ids"),
            "labels_locked": full100_label_lock_validation.get("labels_locked"),
            "ready_for_portfolio_packaging": full100_label_lock_validation.get("ready_for_portfolio_packaging"),
        },
        "portfolio_demo": {
            "ready": portfolio_demo_ready,
            "summary_path": str(PORTFOLIO_DEMO_SUMMARY_PATH),
            "validation_path": str(PORTFOLIO_DEMO_VALIDATION_PATH),
            "validation_num_failures": portfolio_demo_validation.get("num_failures"),
            "status": portfolio_demo_summary.get("status"),
            "case_count": portfolio_demo_summary.get("case_count"),
            "primary_question_ids": portfolio_demo_summary.get("primary_question_ids"),
            "locked_primary_span_count": portfolio_demo_summary.get("locked_primary_span_count"),
            "best_test_auprc": portfolio_demo_summary.get("best_test_auprc"),
            "best_test_f1": portfolio_demo_summary.get("best_test_f1"),
            "label_lock_basis": portfolio_demo_summary.get("label_lock_basis"),
            "ready_for_portfolio_demo": portfolio_demo_validation.get("ready_for_portfolio_demo"),
        },
        "portfolio_narrative": {
            "ready": portfolio_narrative_ready,
            "summary_path": str(PORTFOLIO_NARRATIVE_SUMMARY_PATH),
            "validation_path": str(PORTFOLIO_NARRATIVE_VALIDATION_PATH),
            "validation_num_failures": portfolio_narrative_validation.get("num_failures"),
            "status": portfolio_narrative_summary.get("status"),
            "primary_question_ids": portfolio_narrative_summary.get("primary_question_ids"),
            "question_count": portfolio_narrative_summary.get("question_count"),
            "annotated_span_count": portfolio_narrative_summary.get("annotated_span_count"),
            "best_test_auprc": portfolio_narrative_summary.get("best_test_auprc"),
            "best_test_f1": portfolio_narrative_summary.get("best_test_f1"),
            "resume_bullet_count": portfolio_narrative_summary.get("resume_bullet_count"),
            "slide_count": portfolio_narrative_summary.get("slide_count"),
            "ready_for_portfolio_narrative": portfolio_narrative_validation.get("ready_for_portfolio_narrative"),
        },
        "github_pages_bundle": {
            "ready": github_pages_ready,
            "manifest_path": str(GITHUB_PAGES_MANIFEST_PATH),
            "validation_path": str(GITHUB_PAGES_VALIDATION_PATH),
            "validation_num_failures": github_pages_validation.get("num_failures"),
            "status": github_pages_manifest.get("status"),
            "ready_for_github_pages": github_pages_validation.get("ready_for_github_pages"),
            "primary_question_ids": github_pages_manifest.get("primary_question_ids"),
            "question_count": github_pages_manifest.get("question_count"),
            "annotated_span_count": github_pages_manifest.get("annotated_span_count"),
            "best_test_auprc": github_pages_manifest.get("best_test_auprc"),
            "best_test_f1": github_pages_manifest.get("best_test_f1"),
        },
        "train_only_split_guard": {
            "path": str(split_guard_path),
            "ready_for_split_metrics": split_guard.get("ready_for_split_metrics"),
            "split_counts": split_guard.get("split_counts"),
            "expected_rejection": True,
        },
        "legacy_ready_to_run_full100_generation": legacy_ready_to_run_full100_generation,
        "ready_to_run_full100_generation": legacy_ready_to_run_full100_generation,
        "full100_generation_run": full100_generation_run,
        "remaining_after_full100_generation": remaining_after_full100_generation,
        "num_failures": len(failures),
        "failures": failures,
    }
    validation = {
        "report_path": str(REPORT_PATH),
        "current_stage": current_stage,
        "ready_for_current_stage": ready_for_current_stage,
        "num_failures": len(failures),
        "failures": failures,
        "legacy_ready_to_run_full100_generation": legacy_ready_to_run_full100_generation,
        "ready_to_run_full100_generation": legacy_ready_to_run_full100_generation,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
