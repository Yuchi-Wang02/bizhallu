"""Deterministic rule checker for BizHallu spans (standard library and evidence.py only).

Moved unchanged from decision_battery.py in task card T1.3. It must not import decision_battery.
Its agreement with gold-derived labels is a label-consistency audit, not detection ability.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from bizhallu.evidence import NUMERIC_COLUMNS, ordered_rows


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
