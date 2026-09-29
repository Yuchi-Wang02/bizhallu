"""Jev evidence-binding battery v1 for BizHallu (standard library only).

Poses each pre-identified business-fact span as typed questions to a
non-generative decision model (TypeSafe Jev) over the same evidence table the
generator saw, and compares the returned probabilities with a deterministic,
label-blind evidence checker and with the stored token-time uncertainty signals.

Subcommands (all offline unless stated):

  build     Build one state per span from committed artifacts plus the local
            generation file; write outputs/jev_battery_v1/states.jsonl.
  check     Run the deterministic checker over the states and audit it against
            the provisional labels; write checker.jsonl and checker_audit.json.
  run       Send states to the Jev API (network; needs TYPESAFE_API_KEY in the
            environment) with repeats and a response cache.
  score     Join cached responses with labels and stored signals; write
            report.json and report.md.
  validate  Public offline check of the frozen config and state contract.

The API key is read only from the environment and is never written to disk.
Nothing here reads the sealed Confirmation Set v1 manifests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detector_metrics as metrics  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "jev_battery_v1.json"
GOLD_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
ANNOTATIONS_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_full100_draft.jsonl"
DEMO_PATH = PROJECT_ROOT / "reports" / "bizhallu_demo_v2_data.json"
SCORES_PATH = PROJECT_ROOT / "results" / "full100_statistics_v2_scores.csv"
DEFAULT_GENERATIONS = PROJECT_ROOT / "outputs" / "qwen_full100_generations.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "jev_battery_v1"

DISPLAY_COLUMNS = {
    "country": "country",
    "year_month": "year_month",
    "stock_code": "stock_code",
    "description": "product_name",
    "net_revenue": "net_revenue_gbp",
    "gross_positive_revenue": "gross_positive_revenue_gbp",
    "cancellation_revenue": "cancellation_return_revenue_gbp",
    "invoice_count": "invoice_count",
}
NUMERIC_COLUMNS = ["net_revenue", "gross_positive_revenue", "cancellation_revenue", "invoice_count"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
POSITIVE_LABELS = {"hallucinated_key_fact", "unsupported_claim"}
NEGATIVE_LABELS = {"correct_key_fact"}
MARK_OPEN, MARK_CLOSE = "【", "】"
REFERENCE_ARMS = ["one_minus_min_top2_margin", "mean_token_entropy", "dev_fact_type_prior", "all_positive"]


# ---------------------------------------------------------------- loading ---

def read_jsonl(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_config(path=CONFIG_PATH):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_gold(path=GOLD_PATH):
    return {record["question_id"]: record for record in read_jsonl(path)}


def load_annotations(path=ANNOTATIONS_PATH):
    rows = read_jsonl(path)
    for row in rows:
        if row["label"] in POSITIVE_LABELS:
            row["binary_label"] = 1
        elif row["label"] in NEGATIVE_LABELS:
            row["binary_label"] = 0
        else:
            row["binary_label"] = None
    return rows


def load_generated_texts(generations_path=None, demo_path=DEMO_PATH):
    """Generated answers by question id: local generation file first, demo bundle as fallback."""
    texts, sources = {}, {}
    if generations_path and Path(generations_path).exists():
        for record in read_jsonl(generations_path):
            text = record.get("generated_text")
            if isinstance(text, str) and record.get("question_id"):
                texts[record["question_id"]] = text
                sources[record["question_id"]] = "local_generations"
    if Path(demo_path).exists():
        with Path(demo_path).open("r", encoding="utf-8") as handle:
            demo = json.load(handle)
        for case in demo.get("cases", []):
            qid = case.get("question_id")
            if qid and qid not in texts and isinstance(case.get("generated_text"), str):
                texts[qid] = case["generated_text"]
                sources[qid] = "public_demo_bundle"
    return texts, sources


def load_stored_signals(path=SCORES_PATH, arm="saved_trace_precision"):
    signals = {}
    if not Path(path).exists():
        return signals
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("arm") != arm:
                continue
            signals[row["annotation_id"]] = {
                "evidence_cluster": row.get("evidence_cluster"),
                "period_component": row.get("period_component"),
                **{key: float(row[key]) for key in REFERENCE_ARMS if key in row},
            }
    return signals


# ------------------------------------------------- prompt reconstruction ---

def stable_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ordered_rows(record):
    """Same row order the generator saw; mirrors src/build_prompts.ordered_rows."""
    rows = list(record["evidence"]["rows"])
    question_type = record["question_type"]
    if question_type in {"top_product_month", "top3_products_month", "product_revenue_share_month"}:
        question_id = record["question_id"]
        return sorted(rows, key=lambda row: stable_hash(f"{question_id}|{row.get('stock_code')}|{row.get('description')}"))
    if question_type in {"top_country_month", "country_comparison_month"}:
        return sorted(rows, key=lambda row: str(row.get("country", "")).lower())
    if question_type == "monthly_revenue_change":
        return sorted(rows, key=lambda row: str(row.get("year_month", "")))
    return rows


def metric_definitions(record):
    definitions = [
        "net_revenue = gross_positive_revenue + cancellation_return_revenue.",
        "cancellation_return_revenue is negative when cancellations or returns reduce revenue.",
        "All currency amounts are in GBP.",
    ]
    if "product" in record["question_type"]:
        definitions.append(
            "merchandise net revenue excludes non-product charges such as postage, discounts, bank charges, and manual adjustments."
        )
    if record["question_type"] == "product_revenue_share_month":
        total = record["evidence"].get("metadata", {}).get("total_merchandise_net_revenue")
        if total is not None:
            definitions.append(
                f"Total merchandise net revenue for the month is GBP {float(total):,.2f}; use this as the denominator for share calculations."
            )
    return definitions


def scope_notes(record):
    notes = []
    filters = record["evidence"]["filters"]
    if filters.get("exclude_countries"):
        notes.append("Exclude these countries when selecting the answer: " + ", ".join(filters["exclude_countries"]) + ".")
    if filters.get("year_month") == "2011-12" or record["gold_answer"].get("year_month") == "2011-12":
        notes.append("December 2011 evidence is partial and covers data through December 9 only.")
    if record["question_type"] == "return_impact_month":
        notes.append("Report the reduction as a positive amount even though cancellation_return_revenue is negative.")
    if record["question_type"] == "monthly_revenue_change":
        notes.append("For percentage change, divide the absolute change by the previous month's net revenue.")
    return notes or ["No additional scope notes."]


def evidence_rows_for_state(record):
    rows = []
    for index, row in enumerate(ordered_rows(record), start=1):
        item = {"row_id": f"r{index}"}
        for column, value in row.items():
            item[DISPLAY_COLUMNS.get(column, column)] = value
        rows.append(item)
    return rows


def build_state(record, span, answer_text):
    start, end = span["span_start_char"], span["span_end_char"]
    if answer_text[start:end] != span["span_text"]:
        raise ValueError(f"Span offsets do not match generated text for {span['annotation_id']}")
    return {
        "question": record["question"],
        "metric_definitions": metric_definitions(record),
        "scope_notes": scope_notes(record),
        "evidence_rows": evidence_rows_for_state(record),
        "answer": answer_text,
        "marked_answer": answer_text[:start] + MARK_OPEN + span["span_text"] + MARK_CLOSE + answer_text[end:],
        "marked_text": span["span_text"],
    }


def forbidden_fragments(record, span):
    """Strings that must never appear in a state for this span."""
    fragments = [record["gold_short_answer"]]
    label = record["evidence"].get("metadata", {}).get("share_numerator_label")
    if label:
        fragments.append(label)
    gold_ref = span.get("gold_reference") or {}
    for key in ("reason", "notes"):
        if span.get(key):
            fragments.append(str(span[key]))
    if gold_ref:
        fragments.append(json.dumps(gold_ref, sort_keys=True))
    return fragments


def check_state_contract(state, record, span, config):
    contract = config["state_contract"]
    problems = []
    if sorted(state) != sorted(contract["included_keys"]):
        problems.append(f"state keys {sorted(state)} differ from contract")
    serialized = json.dumps(state, ensure_ascii=False)
    for fragment in forbidden_fragments(record, span):
        if fragment and fragment in serialized and fragment not in state["answer"]:
            problems.append(f"forbidden fragment present: {fragment[:60]}")
    for key in ("label", "fact_type", "split", "gold", "binary_label"):
        if f'"{key}"' in serialized:
            problems.append(f"forbidden key name present: {key}")
    if state["marked_answer"].count(MARK_OPEN) != 1 or state["marked_answer"].count(MARK_CLOSE) != 1:
        problems.append("marker must appear exactly once")
    return problems


def build_questions(config, state):
    """Frozen wording from the config; dynamic option lists depend only on the table shape."""
    questions = {}
    row_ids = [row["row_id"] for row in state["evidence_rows"]]
    numeric = [column for column in state["evidence_rows"][0] if column not in {"row_id", "country", "year_month", "stock_code", "product_name"}]
    for key, spec in config["questions"].items():
        question = {"type": spec["type"], "instructions": spec["instructions"]}
        dynamic = spec.get("dynamic_criteria")
        if dynamic == "row_ids_plus_none":
            question["criteria"] = {**{rid: f"Row {rid} of evidence_rows" for rid in row_ids}, "none": "Not tied to a single row"}
        elif dynamic == "numeric_columns_plus_not_a_number_plus_derived":
            question["criteria"] = {**{column: f"Copied from column {column}" for column in numeric},
                                    "derived": "A number computed from the table, such as a difference, sum or percentage",
                                    "not_a_number": "The marked text is not a number"}
        elif dynamic == "rank_positions_plus_unranked":
            question["criteria"] = {**{f"rank_{i}": f"Rank position {i}" for i in range(1, len(row_ids) + 1)},
                                    "unranked": "No rank position is assigned"}
        elif "criteria" in spec:
            question["criteria"] = spec["criteria"]
        questions[key] = question
    return questions


def build_states(config, gold, annotations, texts, sources):
    states, skipped = [], []
    for span in sorted(annotations, key=lambda row: row["annotation_id"]):
        qid = span["question_id"]
        if span["binary_label"] is None:
            skipped.append({"annotation_id": span["annotation_id"], "reason": "label excluded from binary metrics"})
            continue
        if qid not in texts:
            skipped.append({"annotation_id": span["annotation_id"], "reason": "generated text unavailable"})
            continue
        record = gold[qid]
        state = build_state(record, span, texts[qid])
        problems = check_state_contract(state, record, span, config)
        if problems:
            raise ValueError(f"{span['annotation_id']}: " + "; ".join(problems))
        states.append({
            "annotation_id": span["annotation_id"],
            "question_id": qid,
            "question_type": record["question_type"],
            "text_source": sources[qid],
            "state": state,
            "questions": build_questions(config, state),
        })
    return states, skipped


# ---------------------------------------------------- deterministic check ---

def normalize(text):
    return re.sub(r"[^0-9a-z]", "", str(text).lower())


def parse_number(text):
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return None
    value = float(match.group(0).replace(",", ""))
    if re.search(r"(?<![\w.])-\s?(?:GBP|£)\s?\d", text) or text.strip().startswith("-"):
        value = -abs(value)
    return value


def within_currency(value, reference, tolerance):
    return abs(value - reference) <= max(tolerance["absolute"], abs(reference) * tolerance["relative_percent"] / 100)


def digit_string(value):
    return re.sub(r"\D", "", f"{abs(value):.2f}")


def is_subsequence(short, long):
    iterator = iter(long)
    return all(char in iterator for char in short)


def magnitude_error(value, references):
    digits = digit_string(value)
    for reference in references:
        other = digit_string(reference)
        if digits == other:
            continue
        if 1 <= abs(len(digits) - len(other)) <= 2 and (is_subsequence(digits, other) or is_subsequence(other, digits)):
            return True
    return False


def context_line(answer, start, end):
    line_start = answer.rfind("\n", 0, start) + 1
    line_end = answer.find("\n", end)
    line_end = len(answer) if line_end == -1 else line_end
    return answer[line_start:line_end], start - line_start, end - line_start


def entity_key(record):
    return "description" if "product" in record["question_type"] else "country"


def entities_in_line(rows, line, key):
    found = []
    lowered = line.lower()
    for index, row in enumerate(rows):
        name = str(row.get(key, ""))
        if name and name.lower() in lowered:
            found.append((lowered.index(name.lower()), index))
        code = str(row.get("stock_code", ""))
        if key == "description" and code and re.search(rf"(?<![\w]){re.escape(code)}(?![\w])", line):
            found.append((line.index(code), index))
    return [index for _, index in sorted(set(found))]


def claimed_rank(line, span_offset):
    head = line[:span_offset]
    match = re.match(r"\s*(?:\*\*)?(\d)[.)]", line)
    if match:
        return int(match.group(1))
    match = re.search(r"rank(?:ed)?\s*#?\s*(\d)|#(\d)\b|\b(first|second|third|fourth|fifth)\b", head + line[span_offset:], re.I)
    if match:
        if match.group(1) or match.group(2):
            return int(match.group(1) or match.group(2))
        return ["first", "second", "third", "fourth", "fifth"].index(match.group(3).lower()) + 1
    return None


def scoped_rows(record, rows):
    excluded = {name.lower() for name in record["evidence"]["filters"].get("exclude_countries", [])}
    return [row for row in rows if str(row.get("country", "")).lower() not in excluded]


def ranking(record, rows):
    return sorted(scoped_rows(record, rows), key=lambda row: -float(row.get("net_revenue", 0)))


def question_months(record):
    return {m.lower() for m in re.findall(r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}", record["question"])}


def comparison_entities(record, rows):
    match = re.search(r"did (.+?) or (.+?) generate", record["question"], re.I)
    if not match:
        return None
    names = [match.group(1).strip(), match.group(2).strip()]
    lookup = {str(row["country"]).lower(): row for row in rows}
    return [lookup.get(name.lower()) for name in names]


def check_span(record, span, answer, tolerance, pct_tol):
    """Label-blind verdict for one span. Returns supported / contradicted / unparsed with a mechanism."""
    rows = ordered_rows(record)
    text = span["span_text"]
    qtype = record["question_type"]
    line, off_start, off_end = context_line(answer, span["span_start_char"], span["span_end_char"])
    key = entity_key(record)
    result = {"annotation_id": span["annotation_id"], "question_id": record["question_id"], "kind": None,
              "verdict": "unparsed", "mechanism": "unparsed", "detail": ""}

    def finish(kind, verdict, mechanism, detail=""):
        result.update({"kind": kind, "verdict": verdict, "mechanism": mechanism, "detail": detail})
        return result

    # months
    if re.fullmatch(r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}", text.strip()):
        ok = text.strip().lower() in question_months(record)
        return finish("month", "supported" if ok else "contradicted", "period_in_question" if ok else "period_not_in_question")

    # rank markers such as "1." or "rank 3"
    if re.fullmatch(r"\s*(?:\*\*)?(\d)[.)]?\s*|\s*rank(?:ed)?\s*#?\d\s*|\s*#\d\s*", text) and qtype in {"top3_products_month", "product_revenue_share_month"}:
        rank = int(re.search(r"\d", text).group(0))
        order = ranking(record, rows)
        named = entities_in_line(rows, line, key)
        if not named or rank > len(order):
            return finish("rank_marker", "unparsed", "unparsed", "no entity on the line")
        expected = order[rank - 1]
        actual = rows[named[0]]
        ok = actual is expected
        return finish("rank_marker", "supported" if ok else "contradicted",
                      "rank_matches" if ok else "self_consistent_wrong_selection",
                      f"rank {rank} named {actual.get(key)}, table rank {rank} is {expected.get(key)}")

    # entities
    entity_rows = [row for row in rows if normalize(row.get(key, "")) == normalize(text) or (row.get("stock_code") and normalize(row["stock_code"]) == normalize(text))]
    if entity_rows:
        row = entity_rows[0]
        if qtype in {"top_country_month", "top_product_month"}:
            expected = ranking(record, rows)[0]
            in_scope_note = normalize(text) in {normalize(n) for n in record["evidence"]["filters"].get("exclude_countries", [])}
            if in_scope_note and off_start < len(line) and "exclud" in line.lower():
                return finish("entity", "supported", "scope_restatement")
            ok = row is expected
            return finish("entity", "supported" if ok else "contradicted", "top_selection" if ok else "self_consistent_wrong_selection",
                          f"named {row.get(key)}, table top is {expected.get(key)}")
        if qtype in {"top3_products_month", "product_revenue_share_month"}:
            rank = claimed_rank(line, off_start)
            order = ranking(record, rows)
            if rank is None:
                if qtype == "product_revenue_share_month":
                    ok = row is order[0]
                    return finish("entity", "supported" if ok else "contradicted", "top_selection" if ok else "self_consistent_wrong_selection")
                return finish("entity", "unparsed", "unparsed", "no rank on the line")
            if rank > len(order):
                return finish("entity", "unparsed", "unparsed", "rank beyond table")
            ok = row is order[rank - 1]
            return finish("entity", "supported" if ok else "contradicted", "rank_matches" if ok else "self_consistent_wrong_selection",
                          f"claimed rank {rank}, table rank {rank} is {order[rank - 1].get(key)}")
        if qtype == "country_comparison_month":
            pair = comparison_entities(record, rows)
            if pair and all(pair):
                if row not in pair:
                    return finish("entity", "contradicted", "entity_not_in_question")
                other = pair[1] if row is pair[0] else pair[0]
                # an entity named as the subject of a higher/lower claim inherits that claim's truth value
                after = line[off_end:off_end + 60]
                claim = re.match(r"\s*(?:generated|had|earned|recorded|posted|produced)?\s*(more|higher|greater|less|lower|fewer)\b", after, re.I)
                if claim:
                    says_higher = claim.group(1).lower() in {"more", "higher", "greater"}
                    truly_higher = float(row["net_revenue"]) > float(other["net_revenue"])
                    ok = says_higher == truly_higher
                    return finish("entity", "supported" if ok else "contradicted",
                                  "compared_entity" if ok else "self_consistent_wrong_selection",
                                  f"{row['country']} claimed {'higher' if says_higher else 'lower'} than {other['country']}")
                return finish("entity", "supported", "compared_entity")
        return finish("entity", "unparsed", "unparsed")

    # comparison direction phrases
    if qtype == "country_comparison_month" and re.search(r"\b(more|less|higher|lower|greater|exceed|outperform)", text, re.I):
        pair = comparison_entities(record, rows)
        named = entities_in_line(rows, line, "country")
        if pair and all(pair) and len(named) >= 2:
            first, second = rows[named[0]], rows[named[1]]
            says_first_higher = bool(re.search(r"\b(more|higher|greater|exceed|outperform)", text, re.I))
            truth_first_higher = float(first["net_revenue"]) > float(second["net_revenue"])
            ok = says_first_higher == truth_first_higher
            return finish("direction", "supported" if ok else "contradicted", "direction_matches" if ok else "direction_reversed",
                          f"{first['country']} vs {second['country']}")
        return finish("direction", "unparsed", "unparsed")

    if qtype == "monthly_revenue_change" and re.fullmatch(r"\s*(increase[sd]?|decrease[sd]?|grew|fell|rose|declined|up|down)\s*", text, re.I):
        prev, cur = sorted(rows, key=lambda r: str(r["year_month"]))[:2]
        went_up = float(cur["net_revenue"]) > float(prev["net_revenue"])
        says_up = bool(re.search(r"increase|grew|rose|up", text, re.I))
        ok = went_up == says_up
        return finish("direction", "supported" if ok else "contradicted", "direction_matches" if ok else "direction_reversed")

    # percentages
    if "%" in text or re.search(r"percent", text, re.I):
        value = parse_number(text)
        if value is None:
            return finish("percentage", "unparsed", "unparsed")
        expected = None
        if qtype == "monthly_revenue_change":
            prev, cur = sorted(rows, key=lambda r: str(r["year_month"]))[:2]
            expected = (float(cur["net_revenue"]) - float(prev["net_revenue"])) / float(prev["net_revenue"]) * 100
        elif qtype == "product_revenue_share_month":
            total = record["evidence"].get("metadata", {}).get("total_merchandise_net_revenue")
            named = entities_in_line(rows, line, key)
            top = ranking(record, rows)[0]
            numerator = rows[named[0]] if named else top
            expected = float(numerator["net_revenue"]) / float(total) * 100 if total else None
        elif qtype == "return_impact_month":
            row = rows[0]
            expected = abs(float(row["cancellation_revenue"])) / float(row["gross_positive_revenue"]) * 100
        if expected is None:
            return finish("percentage", "unparsed", "unparsed")
        ok = abs(abs(value) - abs(expected)) <= pct_tol
        return finish("percentage", "supported" if ok else "contradicted", "derived_value_matches" if ok else "derived_value_mismatch",
                      f"stated {value:.2f}, computed {expected:.2f}")

    # currency amounts and other numbers
    if re.search(r"\d", text):
        value = parse_number(text)
        if value is None:
            return finish("amount", "unparsed", "unparsed")
        cells = [(index, column, float(row[column])) for index, row in enumerate(rows) for column in NUMERIC_COLUMNS if column in row]
        matches = [(index, column) for index, column, cell in cells if within_currency(abs(value), abs(cell), tolerance)]
        named = entities_in_line(rows, line, key) if key in rows[0] else []
        head = line[:off_start].lower()

        if qtype == "monthly_revenue_change":
            prev, cur = sorted(rows, key=lambda r: str(r["year_month"]))[:2]
            change = float(cur["net_revenue"]) - float(prev["net_revenue"])
            if within_currency(abs(value), abs(change), tolerance):
                return finish("amount", "supported", "derived_value_matches", "absolute change")
            if any(column == "net_revenue" for _, column in matches):
                return finish("amount", "supported", "cell_copy", "month net revenue")
            if matches:
                return finish("amount", "contradicted", "same_row_wrong_column", str(matches[0]))
            if magnitude_error(value, [abs(c) for *_, c in cells] + [abs(change)]):
                return finish("amount", "contradicted", "magnitude_digit_error")
            return finish("amount", "contradicted", "derived_value_mismatch", f"stated {value:.2f}, change {change:.2f}")

        if qtype == "return_impact_month":
            row = rows[0]
            reduction, net, gross = abs(float(row["cancellation_revenue"])), float(row["net_revenue"]), float(row["gross_positive_revenue"])
            expected_role = "net" if re.search(r"net revenue", head[-80:]) or re.search(r"net revenue of", head) else ("gross" if "gross" in head[-40:] and "reduc" not in head[-40:] else "reduction")
            expected = {"net": net, "gross": gross, "reduction": reduction}[expected_role]
            if within_currency(abs(value), abs(expected), tolerance):
                return finish("amount", "supported", "cell_copy", expected_role)
            if matches:
                return finish("amount", "contradicted", "same_row_wrong_column", f"expected {expected_role}, value matches {matches[0][1]}")
            if magnitude_error(value, [reduction, net, gross]):
                return finish("amount", "contradicted", "magnitude_digit_error")
            return finish("amount", "contradicted", "value_not_in_table")

        if qtype == "country_comparison_month":
            pair = comparison_entities(record, rows)
            if pair and all(pair):
                delta = abs(float(pair[0]["net_revenue"]) - float(pair[1]["net_revenue"]))
                if within_currency(abs(value), delta, tolerance):
                    return finish("amount", "supported", "derived_value_matches", "difference")
            if named:
                entity = rows[named[-1] if named else 0]
                # the amount belongs to the closest entity mentioned before it on the line
                before = [index for index in named if line.lower().find(str(rows[index][key]).lower()) < off_start]
                entity = rows[before[-1]] if before else rows[named[0]]
                if within_currency(abs(value), abs(float(entity["net_revenue"])), tolerance) and value >= 0:
                    return finish("amount", "supported", "cell_copy", entity[key])
                if any(index == rows.index(entity) for index, _ in matches):
                    return finish("amount", "contradicted", "same_row_wrong_column", entity[key])
                if matches:
                    return finish("amount", "contradicted", "cross_row_value", str(matches[0]))
            if magnitude_error(value, [abs(c) for *_, c in cells]):
                return finish("amount", "contradicted", "magnitude_digit_error")
            return finish("amount", "contradicted", "value_not_in_table" if not matches else "derived_value_mismatch")

        # product and country selection questions
        order = ranking(record, rows)
        if qtype in {"top_country_month", "top_product_month"}:
            expected_row = order[0]
        elif qtype == "product_revenue_share_month":
            total = record["evidence"].get("metadata", {}).get("total_merchandise_net_revenue")
            if total and within_currency(abs(value), float(total), tolerance):
                return finish("amount", "supported", "cell_copy", "total merchandise net revenue")
            expected_row = order[0]
        else:
            rank = claimed_rank(line, off_start)
            expected_row = order[rank - 1] if rank and rank <= len(order) else None
        if expected_row is None:
            if named and within_currency(abs(value), abs(float(rows[named[0]]["net_revenue"])), tolerance):
                return finish("amount", "unparsed", "unparsed", "self-consistent pair without a rank")
            return finish("amount", "unparsed", "unparsed")
        if within_currency(abs(value), abs(float(expected_row["net_revenue"])), tolerance) and (not named or rows[named[0]] is expected_row):
            return finish("amount", "supported", "cell_copy", expected_row.get(key))
        if named:
            entity = rows[named[0]]
            if within_currency(abs(value), abs(float(entity["net_revenue"])), tolerance):
                return finish("amount", "contradicted", "self_consistent_wrong_selection", f"{entity.get(key)} is not the required selection")
            if any(index == named[0] for index, _ in matches):
                return finish("amount", "contradicted", "same_row_wrong_column", entity.get(key))
        if matches:
            return finish("amount", "contradicted", "cross_row_value", str(matches[0]))
        if magnitude_error(value, [abs(c) for *_, c in cells]):
            return finish("amount", "contradicted", "magnitude_digit_error")
        return finish("amount", "contradicted", "value_not_in_table")

    return finish("other", "unparsed", "unparsed", "no number, entity, month or direction recognised")


def run_checker(config, gold, annotations, texts):
    tolerance = config["checker_policy"]["currency_tolerance"]
    pct_tol = config["checker_policy"]["percentage_tolerance_points"]
    results = []
    for span in sorted(annotations, key=lambda row: row["annotation_id"]):
        if span["binary_label"] is None or span["question_id"] not in texts:
            continue
        results.append(check_span(gold[span["question_id"]], span, texts[span["question_id"]], tolerance, pct_tol))
    return results


def wilson(successes, total, z=1.959964):
    if total == 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return {"point": p, "lower_95": max(0.0, centre - half), "upper_95": min(1.0, centre + half)}


def checker_audit(results, annotations):
    """Agreement of the label-blind checker with the provisional labels: an audit, not detection."""
    labels = {row["annotation_id"]: row for row in annotations}
    table = Counter()
    mechanisms = defaultdict(Counter)
    for item in results:
        label = labels[item["annotation_id"]]["binary_label"]
        table[(item["verdict"], label)] += 1
        mechanisms[item["mechanism"]][label] += 1
    parsed = [item for item in results if item["verdict"] != "unparsed"]
    agree = sum(1 for item in parsed if (item["verdict"] == "contradicted") == bool(labels[item["annotation_id"]]["binary_label"]))
    return {
        "span_count": len(results),
        "parsed_count": len(parsed),
        "coverage": wilson(len(parsed), len(results)),
        "agreement_on_parsed": wilson(agree, len(parsed)) if parsed else None,
        "verdict_by_label": {f"{verdict}|label={label}": count for (verdict, label), count in sorted(table.items())},
        "mechanism_by_label": {mechanism: {f"label={label}": count for label, count in sorted(counts.items())}
                               for mechanism, counts in sorted(mechanisms.items())},
        "note": "The checker recomputes the same quantities the labels were derived from; agreement measures label consistency, not detection ability.",
    }


# ------------------------------------------------------------- API runner ---

def request_payload(state_record, config):
    return {"state": state_record["state"], "model": config["api"]["model"], "questions": state_record["questions"]}


def cache_key(payload, repeat):
    return hashlib.sha256((json.dumps(payload, sort_keys=True, ensure_ascii=False) + f"|repeat={repeat}").encode("utf-8")).hexdigest()


def post_json(url, payload, api_key, timeout=60):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def call_with_retry(payload, config, api_key, sender=post_json, sleeper=time.sleep):
    api = config["api"]
    attempts = api.get("max_attempts", 6)
    backoff = api.get("backoff_seconds", [2, 4, 8, 16, 32])
    for attempt in range(attempts):
        try:
            status, body = sender(api["endpoint"], payload, api_key)
            return {"status": status, "body": body, "attempts": attempt + 1}
        except urllib.error.HTTPError as error:
            text = error.read().decode("utf-8", "replace") if hasattr(error, "read") else ""
            if error.code in api.get("retry_statuses", [429, 529]) and attempt < attempts - 1:
                sleeper(backoff[min(attempt, len(backoff) - 1)])
                continue
            if error.code == 401:
                raise SystemExit("401 from the API: TYPESAFE_API_KEY was rejected. Nothing was written.")
            return {"status": error.code, "body": {"error": text[:2000]}, "attempts": attempt + 1}
        except urllib.error.URLError as error:
            if attempt < attempts - 1:
                sleeper(backoff[min(attempt, len(backoff) - 1)])
                continue
            return {"status": None, "body": {"error": str(error)}, "attempts": attempt + 1}
    return {"status": None, "body": {"error": "exhausted"}, "attempts": attempts}


def run_battery(states, config, api_key, repeats, responses_path, limit=None, sender=post_json, sleeper=time.sleep, log=print):
    cached = set()
    if responses_path.exists():
        for row in read_jsonl(responses_path):
            cached.add(row["cache_key"])
    done = failed = 0
    with responses_path.open("a", encoding="utf-8") as handle:
        for state_record in states[:limit]:
            payload = request_payload(state_record, config)
            for repeat in range(repeats):
                key = cache_key(payload, repeat)
                if key in cached:
                    continue
                started = time.time()
                outcome = call_with_retry(payload, config, api_key, sender=sender, sleeper=sleeper)
                row = {"annotation_id": state_record["annotation_id"], "question_id": state_record["question_id"],
                       "repeat": repeat, "cache_key": key, "request_sha256": cache_key(payload, -1),
                       "status": outcome["status"], "attempts": outcome["attempts"],
                       "elapsed_seconds": round(time.time() - started, 3), "response": outcome["body"]}
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                cached.add(key)
                if outcome["status"] == 200:
                    done += 1
                else:
                    failed += 1
                    log(f"{state_record['annotation_id']} repeat {repeat}: status {outcome['status']}")
    return {"completed": done, "failed": failed, "cached_before_run": len(cached) - done - failed}


# ------------------------------------------------------------------ score ---

def derived_scores(response):
    answers = response.get("answers", {})
    scores = {}
    if "supported" in answers:
        scores["jev_risk"] = 1.0 - float(answers["supported"]["noul"])
    if "status" in answers:
        scores["jev_conflict"] = float(answers["status"]["probabilities"].get("m2", 0.0))
    if "present" in answers:
        scores["jev_absent"] = 1.0 - float(answers["present"]["noul"])
    if "conclusion" in answers:
        scores["jev_conclusion"] = float(answers["conclusion"]["noul"])
    for key in ("relation", "source_row", "source_column", "rank_claim", "direction_claim"):
        if key in answers:
            scores[f"{key}_choice"] = answers[key].get("choice")
    return scores


def aggregate_responses(response_rows):
    """Mean probability per span across repeats plus argmax flip rates."""
    per_span = defaultdict(list)
    for row in response_rows:
        if row.get("status") == 200:
            per_span[row["annotation_id"]].append(row["response"])
    aggregated = {}
    for annotation_id, responses in per_span.items():
        numeric = defaultdict(list)
        choices = defaultdict(list)
        models = Counter()
        for response in responses:
            models[response.get("model")] += 1
            for key, value in derived_scores(response).items():
                (choices if key.endswith("_choice") else numeric)[key].append(value)
        item = {key: sum(values) / len(values) for key, values in numeric.items()}
        item["repeats"] = len(responses)
        item["models"] = dict(models)
        item["choice_modes"] = {key: Counter(values).most_common(1)[0][0] for key, values in choices.items()}
        item["choice_flip_rate"] = {key: 1 - Counter(values).most_common(1)[0][1] / len(values) for key, values in choices.items()}
        aggregated[annotation_id] = item
    return aggregated


def score_rows(aggregated, annotations, signals, checker_results):
    checker = {item["annotation_id"]: item for item in checker_results}
    rows = []
    for span in annotations:
        aid = span["annotation_id"]
        if aid not in aggregated or span["binary_label"] is None:
            continue
        stored = signals.get(aid, {})
        row = {"annotation_id": aid, "question_id": span["question_id"], "split": span["split"] if "split" in span else None,
               "fact_type": span["fact_type"], "binary_label": span["binary_label"],
               "evidence_cluster": stored.get("evidence_cluster"), "is_month": span["fact_type"] == "month",
               "checker_verdict": checker.get(aid, {}).get("verdict"), "checker_mechanism": checker.get(aid, {}).get("mechanism"),
               "all_positive": 1.0}
        row.update({key: stored[key] for key in REFERENCE_ARMS if key in stored})
        row.update({key: value for key, value in aggregated[aid].items() if isinstance(value, float)})
        rows.append(row)
    return rows


def attach_splits(rows, gold):
    for row in rows:
        row["split"] = gold[row["question_id"]]["split"]
    return rows


def evaluate_arms(rows, arms):
    dev = [row for row in rows if row["split"] == "dev"]
    test = [row for row in rows if row["split"] == "test"]
    test_main = [row for row in test if not row["is_month"]]
    report = {"counts": {"dev": len(dev), "test": len(test), "test_non_month": len(test_main),
                         "test_positive": sum(r["binary_label"] for r in test)}, "arms": {}, "thresholds": {}}
    for arm in arms:
        usable = [row for row in rows if arm in row and row[arm] is not None]
        if len(usable) != len(rows):
            report["arms"][arm] = {"status": "missing for some spans", "available": len(usable)}
            continue
        try:
            threshold = 0.5 if arm == "all_positive" else metrics.dev_threshold([r for r in usable if r["split"] == "dev"], arm)
        except ValueError as error:
            report["arms"][arm] = {"status": f"threshold not selectable: {error}"}
            continue
        report["thresholds"][arm] = threshold
        report["arms"][arm] = {}
        for name, subset in (("dev", dev), ("test", test), ("test_non_month", test_main)):
            if subset:
                report["arms"][arm][name] = metrics.evaluate([r["binary_label"] for r in subset], [r[arm] for r in subset], threshold)
    return report


def paired_intervals(rows, thresholds, comparisons, replicates, seed):
    test = [row for row in rows if row["split"] == "test" and all(a in row and b in row for a, b in comparisons)]
    if not test:
        return {"status": "no test rows"}
    return metrics.paired_cluster_bootstrap(test, thresholds, comparisons, "question_id", replicates=replicates, seed=seed)


def mechanism_table(rows, score="jev_risk", threshold=None):
    table = {}
    for mechanism, group in groupby_key(rows, "checker_mechanism").items():
        positives = [r for r in group if r["binary_label"] == 1]
        flagged = [r for r in positives if threshold is not None and score in r and r[score] >= threshold]
        table[mechanism] = {"spans": len(group), "hallucinated": len(positives),
                            "flagged_hallucinated": len(flagged), "recall": wilson(len(flagged), len(positives)) if positives and threshold is not None else None}
    return table


def groupby_key(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[row.get(key)].append(row)
    return groups


def render_markdown(report):
    lines = ["# Jev evidence battery v1: retrospective comparison", "",
             f"Spans scored: dev {report['evaluation']['counts']['dev']}, test {report['evaluation']['counts']['test']} "
             f"(non-month {report['evaluation']['counts']['test_non_month']}).", "",
             "| arm | dev threshold | test AP | test AUROC | test F1 | non-month test AP |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for arm, values in report["evaluation"]["arms"].items():
        if "test" not in values:
            lines.append(f"| {arm} | n/a | {values.get('status', '')} | | | |")
            continue
        t, m = values["test"], values.get("test_non_month", {})
        fmt = lambda x: "n/a" if x is None else f"{x:.3f}"  # noqa: E731
        lines.append(f"| {arm} | {report['evaluation']['thresholds'][arm]:.4f} | {fmt(t['average_precision'])} | {fmt(t['auroc'])} | {fmt(t['f1'])} | {fmt(m.get('average_precision'))} |")
    lines += ["", "Paired test intervals (question clusters):", ""]
    for interval in report.get("paired_intervals", {}).get("intervals", []):
        if interval["metric"] in {"average_precision", "f1"}:
            lines.append(f"- {interval['signal']} minus {interval['reference']} {interval['metric']}: "
                         f"{interval['point_difference']:+.4f} [{interval['lower_95']:+.4f}, {interval['upper_95']:+.4f}]")
    lines += ["", "Mechanism strata (checker, label-blind) and jev_risk recall at the dev threshold:", "",
              "| mechanism | spans | hallucinated | flagged | recall |", "| --- | ---: | ---: | ---: | --- |"]
    for mechanism, values in report["mechanisms"].items():
        recall = values["recall"]
        text = "n/a" if recall is None else f"{recall['point']:.2f} [{recall['lower_95']:.2f}, {recall['upper_95']:.2f}]"
        lines.append(f"| {mechanism} | {values['spans']} | {values['hallucinated']} | {values['flagged_hallucinated']} | {text} |")
    lines += ["", "Model versions seen: " + json.dumps(report["model_versions"]),
              "", "Claim boundary: retrospective estimation on AI-assisted provisional labels; historical published values unchanged; "
              "the checker replicates the label rule and is an audit reference, not an independent detector."]
    return "\n".join(lines) + "\n"


def score_battery(config, gold, annotations, responses_path, checker_results, signals, replicates, seed):
    responses = read_jsonl(responses_path) if responses_path.exists() else []
    aggregated = aggregate_responses(responses)
    rows = attach_splits(score_rows(aggregated, annotations, signals, checker_results), gold)
    if not rows:
        raise SystemExit("No successful responses to score; run the battery first.")
    jev_arms = [key for key in ("jev_risk", "jev_conflict", "jev_absent") if all(key in row for row in rows)]
    arms = jev_arms + [arm for arm in REFERENCE_ARMS if all(arm in row for row in rows)]
    evaluation = evaluate_arms(rows, arms)
    comparisons = [(a, b) for a in jev_arms[:1] for b in ("one_minus_min_top2_margin", "dev_fact_type_prior", "all_positive") if b in evaluation["thresholds"]]
    intervals = paired_intervals(rows, evaluation["thresholds"], comparisons, replicates, seed) if comparisons and jev_arms and jev_arms[0] in evaluation["thresholds"] else {"status": "not computed"}
    models = Counter()
    for item in aggregated.values():
        for model, count in item["models"].items():
            models[model] += count
    flip = defaultdict(list)
    for item in aggregated.values():
        for key, value in item["choice_flip_rate"].items():
            flip[key].append(value)
    report = {
        "battery_id": config["battery_id"], "model_pinned": config["api"]["model"], "model_versions": dict(models),
        "unexpected_model_versions": [m for m in models if m != config["api"]["model"]],
        "evaluation": evaluation, "paired_intervals": intervals,
        "mechanisms": mechanism_table(rows, "jev_risk", evaluation["thresholds"].get("jev_risk")),
        "choice_flip_rate_mean": {key: sum(values) / len(values) for key, values in flip.items()},
        "repeats_per_span": Counter(item["repeats"] for item in aggregated.values()),
        "claim_boundary": config["claim_boundary"],
    }
    return report, rows


# --------------------------------------------------------------- validate ---

def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(config_path=CONFIG_PATH, output_dir=OUTPUT_DIR, generations_path=None):
    config = load_config(config_path)
    failures = []
    for key in ("supported", "present", "status", "relation", "conclusion", "source_row", "source_column", "rank_claim", "direction_claim"):
        if key not in config["questions"]:
            failures.append(f"missing question {key}")
    for key, spec in config["questions"].items():
        text = json.dumps(spec).lower()
        if "gold" in text or "label" in text.replace("labelled", ""):
            failures.append(f"question {key} mentions gold or labels")
    if config["api"]["model"] == "jev-latest":
        failures.append("model must be pinned, not jev-latest")
    gold = load_gold()
    annotations = load_annotations()
    texts, sources = load_generated_texts(generations_path)
    try:
        states, skipped = build_states(config, gold, annotations, texts, sources)
    except ValueError as error:
        failures.append(str(error))
        states, skipped = [], []
    checker = run_checker(config, gold, annotations, texts)
    audit = checker_audit(checker, annotations) if checker else None
    result = {"config_sha256": file_sha256(config_path), "script_sha256": file_sha256(__file__),
              "states_built": len(states), "states_skipped": len(skipped), "text_sources": dict(Counter(sources.values())),
              "checker_audit": audit, "num_failures": len(failures), "failures": failures,
              "scope": "offline; no API call; the sealed confirmation manifests are never read"}
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "validation.json").open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    return result


# ------------------------------------------------------------------- main ---

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["build", "check", "run", "score", "validate"])
    parser.add_argument("--generations", default=str(DEFAULT_GENERATIONS), help="local qwen_full100_generations.jsonl")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--split", choices=["dev", "test", "all"], default="all")
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260904)
    parser.add_argument("--model", default=None, help="override the pinned model id (recorded in the report)")
    args = parser.parse_args(argv)

    config = load_config()
    if args.model:
        config["api"]["model"] = args.model
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    gold = load_gold()
    annotations = load_annotations()
    texts, sources = load_generated_texts(args.generations)

    if args.command == "validate":
        result = validate(generations_path=args.generations, output_dir=output_dir)
        print(json.dumps({k: v for k, v in result.items() if k != "checker_audit"}, indent=2))
        return 1 if result["num_failures"] else 0

    states, skipped = build_states(config, gold, annotations, texts, sources)
    if args.split != "all":
        states = [s for s in states if gold[s["question_id"]]["split"] == args.split]
    states_path = output_dir / "states.jsonl"

    if args.command == "build":
        with states_path.open("w", encoding="utf-8") as handle:
            for state in states:
                handle.write(json.dumps(state, ensure_ascii=False) + "\n")
        print(json.dumps({"states": len(states), "skipped": skipped[:5], "skipped_count": len(skipped),
                          "text_sources": dict(Counter(sources.values())), "path": str(states_path)}, indent=2, ensure_ascii=False))
        return 0

    checker_results = run_checker(config, gold, annotations, texts)
    if args.command == "check":
        with (output_dir / "checker.jsonl").open("w", encoding="utf-8") as handle:
            for item in checker_results:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        audit = checker_audit(checker_results, annotations)
        with (output_dir / "checker_audit.json").open("w", encoding="utf-8") as handle:
            json.dump(audit, handle, indent=2, ensure_ascii=False)
        print(json.dumps(audit, indent=2, ensure_ascii=False))
        return 0

    responses_path = output_dir / "responses.jsonl"
    if args.command == "run":
        api_key = os.environ.get("TYPESAFE_API_KEY")
        if not api_key:
            raise SystemExit("Set TYPESAFE_API_KEY in the environment (never in a file).")
        repeats = args.repeats or config["analysis_policy"]["repeats_per_span"]
        summary = run_battery(states, config, api_key, repeats, responses_path, limit=args.limit)
        print(json.dumps(summary, indent=2))
        return 0

    signals = load_stored_signals()
    report, rows = score_battery(config, gold, annotations, responses_path, checker_results, signals, args.replicates, args.seed)
    with (output_dir / "report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, default=str)
    with (output_dir / "span_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
