from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_precision_review_v1.json"
CAPACITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_precision_review_report.json"
TEXT_HASH_SUFFIXES = {".csv", ".html", ".json", ".md", ".txt", ".yml", ".yaml"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    if path.suffix.lower() in TEXT_HASH_SUFFIXES:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores, kind="mergesort")
    ranked = labels[order]
    positive_count = int(ranked.sum())
    if positive_count == 0 or positive_count == len(ranked):
        return float("nan")
    precision_at_rank = np.cumsum(ranked) / (np.arange(len(ranked)) + 1)
    return float((precision_at_rank * ranked).sum() / positive_count)


def context_sizes(context_count: int, mean_spans: int) -> np.ndarray:
    multipliers = np.array([0.65, 0.85, 1.0, 1.15, 1.35])
    return np.array(
        [max(4, int(round(mean_spans * multipliers[index % len(multipliers)]))) for index in range(context_count)],
        dtype=int,
    )


def scenario_seed(base_seed: int, values: list[Any]) -> int:
    material = "|".join(str(value) for value in [base_seed, *values]).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "little")


def summarize(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "median": round(float(np.median(array)), 6),
        "p90": round(float(np.quantile(array, 0.9)), 6),
        "minimum": round(float(array.min()), 6),
        "maximum": round(float(array.max()), 6),
    }


def run_scenario(
    config: dict[str, Any],
    context_count: int,
    scenario_type: str,
    scenario_id: str,
    prevalence: float,
    mean_spans: int,
    label_icc: float,
    score_separation: float,
) -> dict[str, Any]:
    monte_carlo = config["monte_carlo"]
    score_model = config["synthetic_data_model"]
    outer_replicates = int(monte_carlo["outer_dataset_replicates_per_scenario"])
    bootstrap_replicates = int(monte_carlo["cluster_bootstrap_replicates_per_dataset"])
    minimum_valid_bootstraps = int(np.ceil(bootstrap_replicates * 0.9))
    sizes = context_sizes(context_count, mean_spans)
    rng = np.random.default_rng(
        scenario_seed(
            int(monte_carlo["base_seed"]),
            [context_count, scenario_type, scenario_id, prevalence, mean_spans, label_icc, score_separation],
        )
    )

    beta_scale = (1.0 / label_icc) - 1.0
    alpha = prevalence * beta_scale
    beta = (1.0 - prevalence) * beta_scale
    shared_weight = float(score_model["shared_score_noise_weight"])
    detector_weight = float(score_model["detector_specific_noise_weight"])
    context_shift_sd = float(score_model["context_score_shift_sd"])
    paired_increment = float(score_model["paired_detector_separation_increment"])

    auprc_half_widths: list[float] = []
    paired_difference_half_widths: list[float] = []
    invalid_outer_replicates = 0
    invalid_bootstrap_replicates = 0

    for _ in range(outer_replicates):
        context_prevalence = rng.beta(alpha, beta, size=context_count)
        clusters: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        for cluster_prevalence, cluster_size in zip(context_prevalence, sizes, strict=True):
            labels = rng.binomial(1, cluster_prevalence, size=int(cluster_size))
            shared_noise = rng.normal(size=int(cluster_size)) * shared_weight
            detector_a_noise = rng.normal(size=int(cluster_size)) * detector_weight
            detector_b_noise = rng.normal(size=int(cluster_size)) * detector_weight
            context_shift = rng.normal() * context_shift_sd
            detector_a = score_separation * labels + shared_noise + detector_a_noise + context_shift
            detector_b = (
                (score_separation + paired_increment) * labels
                + shared_noise
                + detector_b_noise
                + context_shift
            )
            clusters.append((labels, detector_a, detector_b))

        all_labels = np.concatenate([cluster[0] for cluster in clusters])
        all_a = np.concatenate([cluster[1] for cluster in clusters])
        if not np.isfinite(average_precision(all_labels, all_a)):
            invalid_outer_replicates += 1
            continue

        bootstrap_auprc: list[float] = []
        bootstrap_difference: list[float] = []
        for _ in range(bootstrap_replicates):
            selected = rng.integers(0, context_count, size=context_count)
            labels = np.concatenate([clusters[index][0] for index in selected])
            detector_a = np.concatenate([clusters[index][1] for index in selected])
            detector_b = np.concatenate([clusters[index][2] for index in selected])
            auprc_a = average_precision(labels, detector_a)
            auprc_b = average_precision(labels, detector_b)
            if np.isfinite(auprc_a) and np.isfinite(auprc_b):
                bootstrap_auprc.append(auprc_a)
                bootstrap_difference.append(auprc_b - auprc_a)
            else:
                invalid_bootstrap_replicates += 1

        if len(bootstrap_auprc) < minimum_valid_bootstraps:
            invalid_outer_replicates += 1
            continue
        auprc_lower, auprc_upper = np.quantile(bootstrap_auprc, [0.025, 0.975])
        difference_lower, difference_upper = np.quantile(bootstrap_difference, [0.025, 0.975])
        auprc_half_widths.append(float((auprc_upper - auprc_lower) / 2.0))
        paired_difference_half_widths.append(float((difference_upper - difference_lower) / 2.0))

    valid_outer_replicates = len(auprc_half_widths)
    minimum_valid_outer = int(
        np.ceil(outer_replicates * float(monte_carlo["minimum_valid_outer_replicate_fraction"]))
    )
    if valid_outer_replicates < minimum_valid_outer:
        raise RuntimeError(
            f"Scenario {scenario_id} at n={context_count} retained only "
            f"{valid_outer_replicates}/{outer_replicates} valid outer replicates."
        )

    auprc_summary = summarize(auprc_half_widths)
    paired_summary = summarize(paired_difference_half_widths)
    policy = config["decision_policy"]
    preferred = bool(
        auprc_summary["median"] <= policy["preferred_scenario_max_median_auprc_half_width"]
        and paired_summary["median"]
        <= policy["preferred_scenario_max_median_paired_difference_half_width"]
    )
    return {
        "scenario_type": scenario_type,
        "scenario_id": scenario_id,
        "confirmation_context_count": context_count,
        "scenario": {
            "class_prevalence": prevalence,
            "mean_spans_per_context": mean_spans,
            "label_icc": label_icc,
            "internal_score_separation": score_separation,
        },
        "simulated_span_count_range": {
            "minimum_context_size": int(sizes.min()),
            "maximum_context_size": int(sizes.max()),
            "total_spans": int(sizes.sum()),
        },
        "valid_outer_replicates": valid_outer_replicates,
        "invalid_outer_replicates": invalid_outer_replicates,
        "invalid_bootstrap_replicates": invalid_bootstrap_replicates,
        "auprc_interval_half_width": auprc_summary,
        "paired_auprc_difference_interval_half_width": paired_summary,
        "preferred_precision": preferred,
    }


def central_scenarios(config: dict[str, Any]) -> list[dict[str, Any]]:
    grid = config["central_scenario_grid"]
    scenarios = []
    for index, values in enumerate(
        itertools.product(
            grid["class_prevalence"],
            grid["mean_spans_per_context"],
            grid["label_icc"],
            grid["internal_score_separation"],
        ),
        start=1,
    ):
        prevalence, spans, icc, separation = values
        scenarios.append(
            {
                "scenario_id": f"central_{index:02d}",
                "class_prevalence": prevalence,
                "mean_spans_per_context": spans,
                "label_icc": icc,
                "internal_score_separation": separation,
            }
        )
    if len(scenarios) != grid["expected_scenario_count"]:
        raise RuntimeError("Central scenario count does not match the frozen config.")
    return scenarios


def candidate_summary(config: dict[str, Any], context_count: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    fixed = config["fixed_design"]
    policy = config["decision_policy"]
    family_count = int(fixed["question_family_count"])
    pilot = int(fixed["protocol_pilot_context_count"])
    development = int(fixed["development_context_count"])
    total_contexts = pilot + development + context_count
    reserve = int(fixed["observed_source_period_capacity"]) - total_contexts
    central = [row for row in rows if row["scenario_type"] == "central"]
    stress = [row for row in rows if row["scenario_type"] == "stress"]
    preferred_count = sum(row["preferred_precision"] for row in central)
    preferred_share = preferred_count / len(central)
    per_family = context_count // family_count if context_count % family_count == 0 else None
    structural_pass = bool(
        context_count >= policy["minimum_confirmation_context_count"]
        and per_family is not None
        and per_family >= policy["minimum_confirmation_contexts_per_family"]
        and total_contexts <= policy["maximum_total_context_count"]
        and reserve >= policy["minimum_source_period_reserve"]
    )
    worst_central_auprc = max(row["auprc_interval_half_width"]["median"] for row in central)
    worst_central_difference = max(
        row["paired_auprc_difference_interval_half_width"]["median"] for row in central
    )
    precision_pass = bool(
        preferred_share >= policy["minimum_preferred_central_scenario_share"]
        and worst_central_auprc <= policy["maximum_worst_central_median_auprc_half_width"]
        and worst_central_difference
        <= policy["maximum_worst_central_median_paired_difference_half_width"]
    )
    return {
        "confirmation_context_count": context_count,
        "confirmation_contexts_per_family": per_family,
        "total_context_count_including_pilot": total_contexts,
        "source_period_reserve": reserve,
        "structural_pass": structural_pass,
        "central_scenario_count": len(central),
        "central_preferred_scenario_count": preferred_count,
        "central_preferred_scenario_share": round(preferred_share, 6),
        "central_median_of_median_auprc_half_widths": round(
            float(np.median([row["auprc_interval_half_width"]["median"] for row in central])), 6
        ),
        "central_worst_median_auprc_half_width": round(worst_central_auprc, 6),
        "central_median_of_median_paired_difference_half_widths": round(
            float(
                np.median(
                    [row["paired_auprc_difference_interval_half_width"]["median"] for row in central]
                )
            ),
            6,
        ),
        "central_worst_median_paired_difference_half_width": round(
            worst_central_difference, 6
        ),
        "stress_scenario_count": len(stress),
        "stress_preferred_scenario_count": sum(row["preferred_precision"] for row in stress),
        "stress_worst_median_auprc_half_width": round(
            max(row["auprc_interval_half_width"]["median"] for row in stress), 6
        ),
        "stress_worst_median_paired_difference_half_width": round(
            max(row["paired_auprc_difference_interval_half_width"]["median"] for row in stress), 6
        ),
        "precision_pass": precision_pass,
        "candidate_pass": structural_pass and precision_pass,
    }


def main() -> None:
    for path in [CONFIG_PATH, CAPACITY_PATH]:
        if not path.exists():
            raise FileNotFoundError(f"Missing precision-review prerequisite: {repo_path(path)}")
    config = load_json(CONFIG_PATH)
    capacity = load_json(CAPACITY_PATH)
    if capacity.get("context_manifest_created") is not False:
        raise RuntimeError("Precision review requires no existing context manifest.")
    if capacity.get("source_capacity", {}).get("observed_complete_period_count") != config[
        "fixed_design"
    ]["observed_source_period_capacity"]:
        raise RuntimeError("Source-period capacity does not match the frozen precision-review config.")

    central = central_scenarios(config)
    stress = config["stress_scenarios"]
    all_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for context_count in config["candidate_confirmation_context_counts"]:
        candidate_rows = []
        for scenario in central:
            candidate_rows.append(
                run_scenario(
                    config,
                    context_count,
                    "central",
                    scenario["scenario_id"],
                    scenario["class_prevalence"],
                    scenario["mean_spans_per_context"],
                    scenario["label_icc"],
                    scenario["internal_score_separation"],
                )
            )
        for scenario in stress:
            candidate_rows.append(
                run_scenario(
                    config,
                    context_count,
                    "stress",
                    scenario["scenario_id"],
                    scenario["class_prevalence"],
                    scenario["mean_spans_per_context"],
                    scenario["label_icc"],
                    scenario["internal_score_separation"],
                )
            )
        all_rows.extend(candidate_rows)
        summaries.append(candidate_summary(config, context_count, candidate_rows))

    passing = [row for row in summaries if row["candidate_pass"]]
    selected = min(passing, key=lambda row: row["confirmation_context_count"]) if passing else None
    selected_count = selected["confirmation_context_count"] if selected else None
    for row in summaries:
        row["selected"] = row["confirmation_context_count"] == selected_count

    fixed = config["fixed_design"]
    questions_per_context = int(fixed["questions_per_context"])
    if selected is None:
        decision = {
            "status": "no_candidate_passed",
            "context_manifest_authorized": False,
            "next_action": config["decision_policy"]["failure_rule"],
        }
        status = "outcome_blind_precision_review_blocked"
    else:
        confirmation_contexts = int(selected["confirmation_context_count"])
        pilot_contexts = int(fixed["protocol_pilot_context_count"])
        development_contexts = int(fixed["development_context_count"])
        decision = {
            "status": "increase_confirmation_contexts_before_manifest",
            "previous_confirmation_context_count": 15,
            "selected_confirmation_context_count": confirmation_contexts,
            "selected_confirmation_contexts_per_family": selected[
                "confirmation_contexts_per_family"
            ],
            "protocol_pilot_context_count": pilot_contexts,
            "development_context_count": development_contexts,
            "total_context_count": pilot_contexts + development_contexts + confirmation_contexts,
            "protocol_pilot_question_count": pilot_contexts * questions_per_context,
            "development_question_count": development_contexts * questions_per_context,
            "confirmation_question_count": confirmation_contexts * questions_per_context,
            "total_question_count": (
                pilot_contexts + development_contexts + confirmation_contexts
            )
            * questions_per_context,
            "source_period_reserve": selected["source_period_reserve"],
            "precision_review_complete": True,
            "context_manifest_authorized": False,
            "next_action": "Re-prove aggregate source capacity for the increased count, then freeze only the deterministic context manifest and seeded split in a separate audited step.",
        }
        status = "outcome_blind_precision_review_complete"

    payload = {
        "schema_version": "1.0",
        "status": status,
        "project": "BizHallu",
        "study_name": "Confirmation Set v1",
        "scope": "synthetic outcome-blind context-count precision sensitivity analysis",
        "config": {
            "path": repo_path(CONFIG_PATH),
            "sha256": sha256_file(CONFIG_PATH),
        },
        "source_capacity_input": {
            "path": repo_path(CAPACITY_PATH),
            "observed_complete_period_count": capacity["source_capacity"][
                "observed_complete_period_count"
            ],
            "context_manifest_created": capacity["context_manifest_created"],
        },
        "simulation_only": True,
        "confirmation_data_accessed": False,
        "historical_detector_performance_used_for_calibration": False,
        "new_empirical_metrics_created": False,
        "scenario_row_count": len(all_rows),
        "candidate_summaries": summaries,
        "scenario_results": all_rows,
        "planning_decision": decision,
        "interpretation": {
            "primary": "The original 15-context confirmation target is too fragile across the frozen central scenarios. The selected count is a planning increase, not evidence that either detector family performs well.",
            "stress": "No candidate is expected to make every low-density, extreme-prevalence, high-ICC stress scenario precise. Those scenarios remain explicit claim limits.",
            "cluster_limit": "The selected design remains below 30 independent confirmation contexts, so cluster-bootstrap intervals require caution and subgroup results remain descriptive.",
            "metric_limit": "All reported values are simulated interval half-width summaries. They are not observed AUPRC, F1, prevalence, or detector-comparison results.",
        },
        "artifact_boundaries": {
            "context_manifest_created": False,
            "split_assignment_created": False,
            "questions_created": False,
            "prompts_created": False,
            "model_run_executed": False,
            "annotations_created": False,
            "detector_scores_created": False,
            "confirmation_metrics_reported": False,
        },
    }
    REPORT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"status": status, "planning_decision": decision}, indent=2))
    if selected is None:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
