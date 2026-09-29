"""Span-level signals from saved token traces, span kinds and evidence clusters (standard library only).

- Token alignment is ported from src/build_span_token_alignment.py (build_token_char_spans,
  overlapping_tokens) and aggregation from src/build_retrospective_statistics.py (aggregate):
  math.fsum means over the parsed Python floats, 1 - min(top2_margin), no rounding.
- span_kind and restated_from_question follow the span_kind block of the v2 config.
- evidence_cluster hashes the evidence table projection of src/validate_confirmation_question_design.py.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal

SPECIAL_TOKEN_PREFIX = "<|"
SPECIAL_TOKEN_SUFFIX = "|>"
REPLACEMENT_CHAR = chr(0xFFFD)
APPROX_CHAR = chr(0x2248)  # approximately-equal sign


# ------------------------------------------------------------ token signals ---

def is_special_token(token_text):
    return token_text.startswith(SPECIAL_TOKEN_PREFIX) and token_text.endswith(SPECIAL_TOKEN_SUFFIX)


def display_texts_for_alignment(token_traces):
    """Token texts normalised enough to rebuild generated_text (byte-fallback pairs become one sign)."""
    display_texts = [str(token.get("token_text", "")) for token in token_traces]
    for index in range(len(display_texts) - 1):
        current_text = display_texts[index]
        next_text = display_texts[index + 1]
        if current_text.endswith(REPLACEMENT_CHAR) and next_text == REPLACEMENT_CHAR:
            display_texts[index] = current_text[:-1]
            display_texts[index + 1] = APPROX_CHAR
    return display_texts


def build_token_char_spans(question_id, generated_text, token_traces):
    """Character offsets of every token in generated_text; failures list any mismatch."""
    display_texts = display_texts_for_alignment(token_traces)
    token_spans, failures = [], []
    cursor = 0
    for token, display_text in zip(token_traces, display_texts):
        special = is_special_token(str(token.get("token_text", "")))
        if special:
            start = end = cursor
            aligned_text = ""
        else:
            start, end = cursor, cursor + len(display_text)
            if generated_text[start:end] != display_text:
                failures.append({"question_id": question_id, "position": int(token["position"]),
                                 "reason": "token_text does not match generated_text at cursor"})
            aligned_text = display_text
            cursor = end
        token_spans.append({**token, "char_start": start, "char_end": end,
                            "aligned_text": aligned_text, "is_special_token": special})
    if cursor != len(generated_text):
        failures.append({"question_id": question_id, "reason": "token reconstruction length mismatch"})
    return token_spans, failures


def overlapping_tokens(token_spans, span_start, span_end):
    return [token for token in token_spans
            if not token["is_special_token"] and token["char_end"] > span_start and token["char_start"] < span_end]


def _finite(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a detector score")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Score must be finite")
    return result


def aggregate(tokens):
    """Span scores exactly as the saved_trace_precision arm computes them."""
    if not tokens:
        raise ValueError("No tokens in span")
    entropy = [_finite(token["token_entropy"]) for token in tokens]
    margin = [_finite(token["top2_margin"]) for token in tokens]
    return {"mean_token_entropy": math.fsum(entropy) / len(tokens),
            "one_minus_min_top2_margin": 1 - min(margin)}


def span_token_signals(token_traces, generated_text, start, end, question_id=""):
    """Margin and entropy signals for one character span of one generated answer."""
    token_spans, failures = build_token_char_spans(question_id, generated_text, token_traces)
    if failures:
        raise ValueError(f"token reconstruction failed for {question_id}: {failures[0]['reason']}")
    selected = overlapping_tokens(token_spans, start, end)
    scores = aggregate(selected)
    scores["token_positions"] = [int(token["position"]) for token in selected]
    return scores


# ---------------------------------------------------------------- span kind ---

def _direction_pattern(rule):
    match = re.match(r"^matches (.+) and contains no digit$", rule)
    if not match:
        raise ValueError("span_kind.direction_word_rule has an unexpected form")
    return re.compile(match.group(1), re.IGNORECASE)


def _trim(text):
    return str(text).strip(" *").lower()


def span_kind(marked_text, record, rules):
    """Label-independent span kind; the first kind in precedence order that matches wins."""
    text = str(marked_text)
    rows = record["evidence"]["rows"]
    codes = {_trim(row["stock_code"]) for row in rows if row.get("stock_code")}
    names = {_trim(row[key]) for row in rows for key in ("country", "description") if row.get(key)}
    checks = {
        "month": lambda: re.match(rules["month_pattern"], text.strip(), re.IGNORECASE) is not None,
        "percentage": lambda: re.search(rules["percentage_pattern"], text, re.IGNORECASE) is not None,
        "rank_marker": lambda: re.search(rules["rank_marker_pattern"], text, re.IGNORECASE) is not None,
        "direction_word": lambda: (_direction_pattern(rules["direction_word_rule"]).search(text) is not None
                                   and not re.search(r"[0-9]", text)),
        "code": lambda: _trim(text) in codes,
        "entity_name": lambda: _trim(text) in names,
        "currency_or_number": lambda: re.search(r"[0-9]", text) is not None,
        "free_text": lambda: True,
    }
    for kind in rules["precedence"]:
        if checks[kind]():
            return kind
    raise ValueError("span_kind precedence must end with free_text")


def _normalise_for_restatement(text):
    text = re.sub(r"[£$€]", "", str(text).lower())
    text = re.sub(r"(?<=[0-9]),(?=[0-9])", "", text)
    return " ".join(text.split())


def restated_from_question(marked_text, question):
    target = _normalise_for_restatement(marked_text)
    return bool(target) and target in _normalise_for_restatement(question)


# --------------------------------------------------------- evidence cluster ---

def normalize_text(value):
    return " ".join(str(value).strip().split())


def normalize_evidence_value(value):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        numeric = Decimal(str(value))
        if not numeric.is_finite():
            raise ValueError(f"Non-finite evidence value: {value}")
        normalized = format(numeric.normalize(), "f")
        return "0" if normalized in {"-0", "-0.0"} else normalized
    if isinstance(value, str):
        return normalize_text(value)
    return value


def evidence_table_projection(evidence, field_aliases):
    normalized_rows = []
    for source_row in evidence.get("rows", []):
        normalized_row = {}
        for source_key, value in source_row.items():
            key = field_aliases.get(source_key, source_key)
            normalized_value = normalize_evidence_value(value)
            if key in normalized_row and normalized_row[key] != normalized_value:
                raise ValueError(f"Conflicting evidence field alias for {source_key} -> {key}")
            normalized_row[key] = normalized_value
        normalized_rows.append(dict(sorted(normalized_row.items())))
    normalized_rows.sort(key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":"),
                                                   ensure_ascii=True, allow_nan=False))
    return {"rows": normalized_rows}


def evidence_cluster(record):
    projection = evidence_table_projection(record["evidence"], {})
    return hashlib.sha256(json.dumps(projection, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()
