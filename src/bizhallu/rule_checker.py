"""Deterministic rule checker and evidence lookup for BizHallu spans (standard library and evidence.py only).

Moved from decision_battery.py in task card T1.3 and revised in T1.10. It must not import decision_battery.
Its agreement with gold-derived labels is a label-consistency audit, not detection ability.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal

from bizhallu.evidence import (
    NUMERIC_COLUMNS,
    evidence_rows_for_state,
    metric_definitions,
    ordered_rows,
    scope_notes,
)

# ---------------------------------------------------- deterministic check ---

def normalize(text):
    return re.sub(r"[^0-9a-z]", "", str(text).lower())


def parse_number(text):
    text = text.replace(chr(0x2212), "-")  # Unicode minus sign
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


def _mentions(name, line):
    return [match.start() for match in re.finditer(rf"(?<!\w){re.escape(name)}(?!\w)", line, re.IGNORECASE)]


def bound_entity(record, rows, line, key, off_start, before_only=False):
    """Index of the row whose name is mentioned closest before the span on the line.

    Names match on word boundaries and names in filters.exclude_countries are skipped. A stock code
    is used only when no name precedes the span; then the first mention after the span, unless
    before_only is set. None when nothing is mentioned.
    """
    excluded = {name.lower() for name in record["evidence"]["filters"].get("exclude_countries", [])}
    names, codes = [], []
    for index, row in enumerate(rows):
        name = str(row.get(key) or "")
        if name and name.lower() not in excluded:
            names += [(position, index) for position in _mentions(name, line)]
        code = str(row.get("stock_code") or "")
        if key == "description" and code:
            codes += [(position, index) for position in _mentions(code, line)]
    for found in (names, codes):
        before = [item for item in found if item[0] < off_start]
        if before:
            return max(before)[1]
    if before_only:
        return None
    after = sorted(item for item in names + codes if item[0] >= off_start)
    return after[0][1] if after else None


def claimed_rank(line, span_offset):
    """The rank a line claims: its list marker (1 to 9, not a decimal), else its one distinct rank expression.

    Zero or several distinct rank values on the line give None. span_offset is kept for the call signature.
    """
    match = re.match(r"\s*(?:\*\*)?([1-9])[.)](?!\d)", line)
    if match:
        return int(match.group(1))
    values = set()
    for found in re.finditer(r"rank(?:ed)?\s*#?\s*([1-9])\b|#([1-9])\b|\b(first|second|third|fourth|fifth)\b", line, re.IGNORECASE):
        if found.group(1) or found.group(2):
            values.add(int(found.group(1) or found.group(2)))
        else:
            values.add(["first", "second", "third", "fourth", "fifth"].index(found.group(3).lower()) + 1)
    return values.pop() if len(values) == 1 else None


def return_impact_role(head, tail):
    """Role of an amount in a return-impact clause: reduction, net, gross or invoice_count; None without a cue."""
    clause = re.split(r",(?!\d)|;|\.\s|\band\b|\bresulting in\b|\bto\b", head)[-1]
    if re.match(r"\W*invoices?\b", tail) or re.search(r"invoice[ _]count\W*(?:of|was|is)?\W*$", clause):
        return "invoice_count"
    if re.search(r"\b(?:reduc|decreas|lower)\w*\b.*\bby\W*(?:gbp|£)?\W*$", clause):
        return "reduction"
    cues = [(found.start(), role) for role, pattern in (("net", r"net[ _]revenue"), ("gross", r"gross"),
                                                         ("reduction", r"reduc|cancel|return"))
            for found in re.finditer(pattern, clause)]
    return max(cues)[1] if cues else None


def scoped_rows(record, rows):
    excluded = {name.lower() for name in record["evidence"]["filters"].get("exclude_countries", [])}
    return [row for row in rows if str(row.get("country", "")).lower() not in excluded]


def ranking(record, rows):
    return sorted(scoped_rows(record, rows), key=lambda row: -float(row.get("net_revenue", 0)))


def share_top_n(record):
    return max(1, int(record["evidence"]["filters"].get("top_n") or 1))


ORDINALS = ["first", "second", "third", "fourth", "fifth"]


def requested_ranks(record):
    """Rank positions the question asks for."""
    qtype = record["question_type"]
    if qtype in {"top_country_month", "top_product_month"}:
        return {1}
    if qtype == "top3_products_month":
        return {1, 2, 3}
    if qtype == "product_revenue_share_month":
        return set(range(1, share_top_n(record) + 1))
    return set()


def question_months(record):
    return {m.lower() for m in re.findall(r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}", record["question"])}


def comparison_entities(record, rows):
    match = re.search(r"did (.+?) or (.+?) generate", record["question"], re.IGNORECASE)
    if not match:
        return None
    names = [match.group(1).strip(), match.group(2).strip()]
    lookup = {str(row["country"]).lower(): row for row in rows}
    return [lookup.get(name.lower()) for name in names]


SUPPORTED_MECHANISMS = {"cell_copy", "derived_value_matches", "rank_matches", "top_selection", "compared_entity",
                        "direction_matches", "period_in_question", "scope_restatement"}
CONTRADICTED_MECHANISMS = {"self_consistent_wrong_selection", "entity_not_in_question", "period_not_in_question",
                           "same_row_wrong_column", "cross_row_value", "operand_as_difference", "magnitude_digit_error",
                           "value_not_in_table", "sign_mismatch", "derived_value_mismatch", "derived_sign_mismatch",
                           "direction_reversed", "comparison_subject_reversed", "rank_claim_mismatch"}


def check_span(record, span, answer, tolerance, pct_tol):
    """Label-blind verdict for one span: supported or contradicted with a mechanism, or abstain with a reason."""
    rows = ordered_rows(record)
    text = span["span_text"]
    qtype = record["question_type"]
    line, off_start, off_end = context_line(answer, span["span_start_char"], span["span_end_char"])
    key = entity_key(record)
    result = {"annotation_id": span["annotation_id"], "question_id": record["question_id"], "kind": None,
              "verdict": "abstain", "mechanism": "abstain", "abstain_reason": None, "detail": ""}

    def finish(kind, verdict, mechanism, detail=""):
        allowed = CONTRADICTED_MECHANISMS if verdict == "contradicted" else SUPPORTED_MECHANISMS
        if mechanism not in allowed:
            raise ValueError(f"mechanism {mechanism} is not listed for verdict {verdict}")
        result.update({"kind": kind, "verdict": verdict, "mechanism": mechanism, "detail": detail})
        return result

    def abstain(kind, reason, detail=""):
        result.update({"kind": kind, "verdict": "abstain", "mechanism": "abstain", "abstain_reason": reason,
                       "detail": detail})
        return result

    def supported(kind, value, reference, mechanism, detail="", derived=False):
        """Supported, unless the stated value carries an explicit minus sign and the reference is not negative."""
        if value < 0 and reference >= 0:
            return finish(kind, "contradicted", "derived_sign_mismatch" if derived else "sign_mismatch",
                          f"stated {value:.2f}, reference {reference:.2f}")
        return finish(kind, "supported", mechanism, detail)

    # months
    if re.fullmatch(r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}", text.strip()):
        ok = text.strip().lower() in question_months(record)
        return finish("month", "supported" if ok else "contradicted", "period_in_question" if ok else "period_not_in_question")

    # rank markers such as "1." or "rank 3"
    if re.fullmatch(r"\s*(?:\*\*)?[1-9][.)]\s*|\s*rank(?:ed)?\s*#?[1-9]\s*|\s*#[1-9]\s*", text) and qtype in {"top3_products_month", "product_revenue_share_month"}:
        rank = int(re.search(r"\d", text).group(0))
        order = ranking(record, rows)
        named = entities_in_line(rows, line, key)
        if not named or rank < 1 or rank > len(order):
            return abstain("rank_marker", "rank_marker_without_entity")
        expected = order[rank - 1]
        actual = rows[named[0]]
        ok = actual is expected
        return finish("rank_marker", "supported" if ok else "contradicted",
                      "rank_matches" if ok else "self_consistent_wrong_selection",
                      f"rank {rank} named {actual.get(key)}, table rank {rank} is {expected.get(key)}")

    # rank phrases such as "ranked 2nd" or "ranking is second": never parsed as amounts
    rank_word = re.search(r"\brank(?:ed|ing)?\b", text, re.IGNORECASE)
    if rank_word:
        stated = re.search(r"(?<![\d.,])(\d{1,2})(?:st|nd|rd|th)?(?![\d.,%])|\b(first|second|third|fourth|fifth)\b",
                           text[rank_word.end():], re.IGNORECASE)
        if not stated:
            return abstain("rank_claim", "rank_claim_without_position")
        position = int(stated.group(1)) if stated.group(1) else ORDINALS.index(stated.group(2).lower()) + 1
        bound = bound_entity(record, rows, line, key, off_start, before_only=True) if key in rows[0] else None
        order = ranking(record, rows)
        if bound is None or not any(rows[bound] is row for row in order):
            return abstain("rank_claim", "rank_claim_without_entity")
        actual = next(index for index, row in enumerate(order, start=1) if row is rows[bound])
        if actual == position:
            return finish("rank_claim", "supported", "rank_matches", f"{rows[bound].get(key)} is rank {actual}")
        mechanism = "self_consistent_wrong_selection" if position in requested_ranks(record) else "rank_claim_mismatch"
        return finish("rank_claim", "contradicted", mechanism, f"claimed rank {position}, {rows[bound].get(key)} is rank {actual}")

    # entities
    entity_rows =[row for row in rows if normalize(row.get(key, "")) == normalize(text) or (row.get("stock_code") and normalize(row["stock_code"]) == normalize(text))]
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
                    ok = any(row is member for member in order[:share_top_n(record)])
                    return finish("entity", "supported" if ok else "contradicted", "top_selection" if ok else "self_consistent_wrong_selection")
                return abstain("entity", "no_rank_on_line")
            if rank > len(order):
                return abstain("entity", "rank_beyond_table")
            ok = row is order[rank - 1]
            return finish("entity", "supported" if ok else "contradicted", "rank_matches" if ok else "self_consistent_wrong_selection",
                          f"claimed rank {rank}, table rank {rank} is {order[rank - 1].get(key)}")
        if qtype == "country_comparison_month":
            pair = comparison_entities(record, rows)
            if pair and all(pair):
                if row not in pair:
                    return finish("entity", "contradicted", "entity_not_in_question")
                other = pair[1] if row is pair[0] else pair[0]
                # an entity named as the subject of a higher/lower claim inherits that claim's truth value;
                # markdown emphasis is removed before matching
                after = re.sub(r"^[\s*_`]+", " ", line[off_end:off_end + 60])
                claim = re.match(r"\s*(?:generated|had|earned|recorded|posted|produced)?\s*(more|higher|greater|less|lower|fewer)\b", after, re.IGNORECASE)
                if claim:
                    says_higher = claim.group(1).lower() in {"more", "higher", "greater"}
                    truly_higher = float(row["net_revenue"]) > float(other["net_revenue"])
                    ok = says_higher == truly_higher
                    return finish("entity", "supported" if ok else "contradicted",
                                  "compared_entity" if ok else "comparison_subject_reversed",
                                  f"{row['country']} claimed {'higher' if says_higher else 'lower'} than {other['country']}")
                before = re.sub(r"[*_`]", "", line[:off_start])
                if re.search(r"\b(?:than|compared (?:to|with)|versus|vs\.?)\s+(?:the\s+)?$", before, re.IGNORECASE):
                    return finish("entity", "supported", "compared_entity", "object of the comparison")
                return abstain("entity", "no_comparative_for_entity")
        return abstain("entity", "entity_without_rule_for_question_type")

    # comparison direction phrases
    if qtype == "country_comparison_month" and re.search(r"\b(more|less|higher|lower|greater|exceed|outperform)", text, re.IGNORECASE):
        pair = comparison_entities(record, rows)
        named = entities_in_line(rows, line, "country")
        if pair and all(pair) and len(named) >= 2:
            first, second = rows[named[0]], rows[named[1]]
            says_first_higher = bool(re.search(r"\b(more|higher|greater|exceed|outperform)", text, re.IGNORECASE))
            truth_first_higher = float(first["net_revenue"]) > float(second["net_revenue"])
            ok = says_first_higher == truth_first_higher
            return finish("direction", "supported" if ok else "contradicted", "direction_matches" if ok else "direction_reversed",
                          f"{first['country']} vs {second['country']}")
        return abstain("direction", "direction_without_two_entities")

    if qtype == "monthly_revenue_change" and re.fullmatch(r"\s*(increase[sd]?|decrease[sd]?|grew|fell|rose|declined|up|down)\s*", text, re.IGNORECASE):
        prev, cur = sorted(rows, key=lambda r: str(r["year_month"]))[:2]
        went_up = float(cur["net_revenue"]) > float(prev["net_revenue"])
        says_up = bool(re.search(r"increase|grew|rose|up", text, re.IGNORECASE))
        ok = went_up == says_up
        return finish("direction", "supported" if ok else "contradicted", "direction_matches" if ok else "direction_reversed")

    # percentages
    if "%" in text or re.search(r"percent", text, re.IGNORECASE):
        value = parse_number(text)
        if value is None:
            return abstain("percentage", "no_number")
        expected = None
        if qtype == "monthly_revenue_change":
            prev, cur = sorted(rows, key=lambda r: str(r["year_month"]))[:2]
            expected = (float(cur["net_revenue"]) - float(prev["net_revenue"])) / float(prev["net_revenue"]) * 100
        elif qtype == "product_revenue_share_month":
            total = record["evidence"].get("metadata", {}).get("total_merchandise_net_revenue")
            required = ranking(record, rows)[:share_top_n(record)]
            bound = bound_entity(record, rows, line, key, off_start)
            if total and bound is not None:
                own = float(rows[bound]["net_revenue"]) / float(total) * 100
                if not any(rows[bound] is member for member in required):
                    mechanism = "self_consistent_wrong_selection" if abs(abs(value) - own) <= pct_tol else "derived_value_mismatch"
                    return finish("percentage", "contradicted", mechanism,
                                  f"stated {value:.2f}, {rows[bound].get(key)} is outside the required selection")
                if len(required) > 1 and abs(abs(value) - own) <= pct_tol:
                    return supported("percentage", value, own, "derived_value_matches", f"component share {own:.2f}", derived=True)
            combined = sum(float(member["net_revenue"]) for member in required)
            expected = combined / float(total) * 100 if total else None
        elif qtype == "return_impact_month":
            row = rows[0]
            expected = abs(float(row["cancellation_revenue"])) / float(row["gross_positive_revenue"]) * 100
        if expected is None:
            return abstain("percentage", "percentage_without_defined_basis")
        detail = f"stated {value:.2f}, computed {expected:.2f}"
        if abs(abs(value) - abs(expected)) <= pct_tol:
            return supported("percentage", value, expected, "derived_value_matches", detail, derived=True)
        return finish("percentage", "contradicted", "derived_value_mismatch", detail)

    # currency amounts and other numbers
    if re.search(r"\d", text):
        value = parse_number(text)
        if value is None:
            return abstain("amount", "no_number")
        cells = [(index, column, float(row[column])) for index, row in enumerate(rows) for column in NUMERIC_COLUMNS if column in row]
        matches = [(index, column) for index, column, cell in cells if within_currency(abs(value), abs(cell), tolerance)]
        named = entities_in_line(rows, line, key) if key in rows[0] else []
        head = line[:off_start].lower()

        if qtype == "monthly_revenue_change":
            prev, cur = sorted(rows, key=lambda r: str(r["year_month"]))[:2]
            change = float(cur["net_revenue"]) - float(prev["net_revenue"])
            if within_currency(abs(value), abs(change), tolerance):
                return supported("amount", value, change, "derived_value_matches", "absolute change", derived=True)
            net_cells = [float(rows[index]["net_revenue"]) for index, column in matches if column == "net_revenue"]
            if net_cells:
                return supported("amount", value, net_cells[0], "cell_copy", "month net revenue")
            if matches:
                return finish("amount", "contradicted", "same_row_wrong_column", str(matches[0]))
            if magnitude_error(value, [abs(c) for *_, c in cells] + [abs(change)]):
                return finish("amount", "contradicted", "magnitude_digit_error")
            return finish("amount", "contradicted", "derived_value_mismatch", f"stated {value:.2f}, change {change:.2f}")

        if qtype == "return_impact_month":
            row = rows[0]
            reduction, net, gross = abs(float(row["cancellation_revenue"])), float(row["net_revenue"]), float(row["gross_positive_revenue"])
            expected_role = return_impact_role(head, line[off_end:].lower())
            if expected_role is None:
                return abstain("amount", "no_role_cue_in_clause")
            expected = {"net": net, "gross": gross, "reduction": reduction,
                        "invoice_count": float(row.get("invoice_count") or 0)}[expected_role]
            if within_currency(abs(value), abs(expected), tolerance):
                if expected_role == "reduction":  # 'reduced by X' and the negative cell are both valid
                    return finish("amount", "supported", "cell_copy", expected_role)
                return supported("amount", value, expected, "cell_copy", expected_role)
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
                    return supported("amount", value, delta, "derived_value_matches", "difference", derived=True)
            # a country net revenue presented as the difference; role words sit right before (or more/less right after)
            tail = line[off_end:off_end + 40]
            role_difference = bool(
                re.search(r"\b(?:difference|gap|margin)\b(?:\s+in\s+net[ _]revenue)?\s*(?:of|is|was|:)?\W*(?:gbp)?\W*$", head)
                or re.search(r"\badditional(?:\s+net[ _]revenue)?(?:\s+of)?\W*(?:gbp)?\W*$", head)
                or re.match(r"\W*(?:GBP)?\W*(?:more|less|higher|lower)\b", tail, re.IGNORECASE))
            if role_difference and any(column == "net_revenue" for _, column in matches):
                return finish("amount", "contradicted", "operand_as_difference",
                              "a country net revenue is presented as the difference")
            bound = bound_entity(record, rows, line, key, off_start)
            if bound is not None:
                # the amount belongs to the entity mentioned closest before it on the line
                entity = rows[bound]
                if within_currency(abs(value), abs(float(entity["net_revenue"])), tolerance):
                    return supported("amount", value, float(entity["net_revenue"]), "cell_copy", entity[key])
                if any(index == bound for index, _ in matches):
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
                return supported("amount", value, float(total), "cell_copy", "total merchandise net revenue")
            required = order[:share_top_n(record)]
            if len(required) > 1:
                combined = sum(float(member["net_revenue"]) for member in required)
                if within_currency(abs(value), combined, tolerance):
                    return supported("amount", value, combined, "derived_value_matches",
                                     "combined net revenue of the required selection", derived=True)
                share_bound = bound_entity(record, rows, line, key, off_start)
                for member in required:
                    if (within_currency(abs(value), abs(float(member["net_revenue"])), tolerance)
                            and (share_bound is None or rows[share_bound] is member)):
                        return supported("amount", value, float(member["net_revenue"]), "cell_copy", member.get(key))
            expected_row = order[0]
        else:
            rank = claimed_rank(line, off_start)
            expected_row = order[rank - 1] if rank and rank <= len(order) else None
        bound = bound_entity(record, rows, line, key, off_start) if key in rows[0] else None
        if expected_row is None:
            if bound is not None and within_currency(abs(value), abs(float(rows[bound]["net_revenue"])), tolerance):
                return abstain("amount", "self_consistent_pair_without_rank")
            return abstain("amount", "no_rank_on_line")
        if within_currency(abs(value), abs(float(expected_row["net_revenue"])), tolerance) and (bound is None or rows[bound] is expected_row):
            return supported("amount", value, float(expected_row["net_revenue"]), "cell_copy", expected_row.get(key))
        if bound is not None:
            entity = rows[bound]
            if within_currency(abs(value), abs(float(entity["net_revenue"])), tolerance):
                return finish("amount", "contradicted", "self_consistent_wrong_selection", f"{entity.get(key)} is not the required selection")
            if any(index == bound for index, _ in matches):
                return finish("amount", "contradicted", "same_row_wrong_column", entity.get(key))
        if matches:
            return finish("amount", "contradicted", "cross_row_value", str(matches[0]))
        if magnitude_error(value, [abs(c) for *_, c in cells]):
            return finish("amount", "contradicted", "magnitude_digit_error")
        return finish("amount", "contradicted", "value_not_in_table")

    if re.search(r"\b(?:first|second|third|fourth|fifth)\b", text, re.IGNORECASE):
        return abstain("other", "rank_word_claim")
    return abstain("other", "free_text", "no number, entity, month or direction recognised")


def checker_family(item, policy):
    """checker_policy.family_field: the M code of a contradicted mechanism, 'abstain', or None when supported."""
    if item["verdict"] == "abstain":
        return "abstain"
    if item["verdict"] == "contradicted":
        mapping = policy["mechanism_to_family"]
        if item["mechanism"] not in mapping:
            raise ValueError(f"{item['annotation_id']}: mechanism {item['mechanism']} has no family in checker_policy")
        return mapping[item["mechanism"]]
    return None


def run_checker(config, gold, spans, texts):
    """Checker verdicts for every span whose answer text is available; labels are never read."""
    policy = config["checker_policy"]
    tolerance = policy["currency_tolerance"]
    pct_tol = policy["percentage_tolerance_points"]
    results = []
    for span in sorted(spans, key=lambda row: row["annotation_id"]):
        if span["question_id"] not in texts:
            continue
        item = check_span(gold[span["question_id"]], span, texts[span["question_id"]], tolerance, pct_tol)
        item["family"] = checker_family(item, policy)
        results.append(item)
    return results


# --------------------------------------------------------- evidence lookup ---

def _lookup_number(text):
    """First number of the text with currency marks, three-digit group commas and the sign removed."""
    cleaned = re.sub(r"GBP|£", " ", str(text), flags=re.IGNORECASE)
    cleaned = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", cleaned)
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None, 0
    token = match.group(0)
    return Decimal(token), len(token.split(".")[1]) if "." in token else 0


def _number_matches(value, decimals, reference):
    reference = abs(reference)
    if value == reference:
        return True
    return value == reference.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def _lookup_name(text):
    name = " ".join(str(text).strip(" *_`\"'").lower().split())
    return re.sub(r"^(?:the|a|an)\s+", "", name)


MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
               "october", "november", "december"]


def evidence_lookup(record, span, span_kind, config):
    """analysis_policy.binary_arms.evidence_lookup: flagged when the marked value or name appears nowhere in the
    evidence cells as the generator saw them, the question, metric_definitions or scope_notes; not_flagged when it
    does; abstain for span kinds it does not apply to. By definition it ignores which row or role the sentence
    attaches the value to."""
    policy = config["analysis_policy"]["binary_arms"]["evidence_lookup"]
    result = {"annotation_id": span["annotation_id"], "question_id": record["question_id"], "span_kind": span_kind}
    if span_kind not in policy["applies_to_span_kinds"]:
        return {**result, "verdict": "abstain", "detail": f"not applicable to {span_kind}"}
    rows = evidence_rows_for_state(record)
    cells = [value for row in rows for column, value in row.items() if column != "row_id"]
    free_text = [record["question"], *metric_definitions(record), *scope_notes(record)]
    text = span["span_text"]
    if span_kind in {"currency_or_number", "percentage"}:
        value, decimals = _lookup_number(text)
        if value is None:
            return {**result, "verdict": "abstain", "detail": "no number in the marked text"}
        references = []
        for cell in cells:
            number, _ = _lookup_number(cell) if re.fullmatch(r"-?[\d.,]+", cell) else (None, 0)
            if number is not None:
                references.append(number)
        tokenizer = re.compile(config["state_contract"]["numeric_scan"]["tokenizer_regex"])
        for line in free_text:
            for token in tokenizer.finditer(line):
                number, _ = _lookup_number(token.group(0))
                if number is not None:
                    references.append(number)
        found = any(_number_matches(value, decimals, reference) for reference in references)
    elif span_kind == "month":
        name = _lookup_name(text)
        match = re.fullmatch(r"([a-z]+)\s+(\d{4})", name)
        if not match or match.group(1) not in MONTH_NAMES:
            return {**result, "verdict": "abstain", "detail": "not a Month YYYY text"}
        period = f"{match.group(2)}-{MONTH_NAMES.index(match.group(1)) + 1:02d}"
        found = period in cells or any(name in _lookup_name(line) or period in line for line in free_text)
    else:
        name = _lookup_name(text)
        names = {_lookup_name(cell) for cell in cells}
        found = bool(name) and (name in names or any(
            re.search(rf"(?<!\w){re.escape(name)}(?!\w)", _lookup_name(line)) for line in free_text))
    return {**result, "verdict": "not_flagged" if found else "flagged",
            "detail": "found in the evidence" if found else "not found in the evidence"}


def run_evidence_lookup(config, gold, spans, span_kinds):
    """evidence_lookup for every span; span_kinds maps annotation_id to its span_kind."""
    return [evidence_lookup(gold[span["question_id"]], span, span_kinds[span["annotation_id"]], config)
            for span in sorted(spans, key=lambda row: row["annotation_id"])]


# ------------------------------------------------------------------- audit ---

def wilson(successes, total, z=1.959964):
    if total == 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return {"point": p, "lower_95": max(0.0, centre - half), "upper_95": min(1.0, centre + half)}


def _agreement(results, labels):
    decided = [item for item in results if item["verdict"] != "abstain"]
    agree = sum(1 for item in decided if (item["verdict"] == "contradicted") == bool(labels[item["annotation_id"]]))
    return {"span_count": len(results), "decided_count": len(decided), "agree_count": agree,
            "coverage": wilson(len(decided), len(results)),
            "agreement_on_decided": wilson(agree, len(decided)),
            "agreement_all_spans_abstain_as_miss": wilson(agree, len(results))}


def checker_audit(results, labels, roles=None, public_question_ids=None):
    """Agreement of the label-blind checker with binary labels: an audit, not detection.

    `labels` maps annotation_id to a binary label; spans without one are skipped and counted. `roles` maps
    annotation_id to its evaluation role; `public_question_ids` are the nine public demo answers the rules were
    first written against. A span is decided when its verdict is not abstain.
    """
    unlabelled = [item for item in results if labels.get(item["annotation_id"]) is None]
    results = [item for item in results if labels.get(item["annotation_id"]) is not None]
    table = Counter()
    mechanisms = defaultdict(Counter)
    for item in results:
        label = labels[item["annotation_id"]]
        table[(item["verdict"], label)] += 1
        mechanisms[item["mechanism"]][label] += 1
    breakdown = {"all": _agreement(results, labels)}
    for role in sorted({(roles or {}).get(item["annotation_id"]) for item in results} - {None}):
        breakdown[role] = _agreement([item for item in results if roles.get(item["annotation_id"]) == role], labels)
    if public_question_ids is not None:
        breakdown["public_demo_answers"] = _agreement(
            [item for item in results if item["question_id"] in public_question_ids], labels)
        breakdown["other_answers"] = _agreement(
            [item for item in results if item["question_id"] not in public_question_ids], labels)
    return {
        **breakdown["all"],
        "unlabelled_skipped": len(unlabelled),
        "breakdown": breakdown,
        "abstain_reasons": dict(Counter(item.get("abstain_reason") for item in results if item["verdict"] == "abstain")),
        "verdict_by_label": {f"{verdict}|label={label}": count for (verdict, label), count in sorted(table.items())},
        "mechanism_by_label": {mechanism: {f"label={label}": count for label, count in sorted(counts.items())}
                               for mechanism, counts in sorted(mechanisms.items())},
        "note": ("The checker recomputes the same quantities the labels were derived from; agreement measures label "
                 "consistency, not detection ability. The rules were first written against the nine public demo "
                 "answers and revised in task card T1.10 against all 35 dev and test answers, so every figure here "
                 "is in-sample."),
    }
