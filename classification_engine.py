from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Any


def normalize_hts(value: object) -> str:
    """Return the numeric HTS key so dotted and undotted inputs compare equally."""
    return re.sub(r"\D", "", str(value or ""))


def parse_ad_valorem_rate(value: object) -> float | None:
    """Parse a simple ad-valorem rate. Compound/specific rates require human review."""
    text = str(value or "").strip()
    if not text:
        return None
    if text.lower() == "free":
        return 0.0
    if re.fullmatch(r"\d+(?:\.\d+)?%", text):
        return float(text[:-1])
    return None


def load_hts_index(csv_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load HTS rows and inherit a general rate from the nearest rated parent row."""
    index: dict[str, dict[str, Any]] = {}
    rate_stack: dict[int, str] = {}
    description_stack: dict[int, str] = {}

    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            code = str(row.get("HTS Number", "")).strip()
            if not code:
                continue
            try:
                indent = int(row.get("Indent", 0) or 0)
            except (TypeError, ValueError):
                indent = 0

            for level in [level for level in rate_stack if level > indent]:
                rate_stack.pop(level, None)
            for level in [level for level in description_stack if level > indent]:
                description_stack.pop(level, None)

            description = str(row.get("Description", "")).strip()
            if description:
                description_stack[indent] = description

            explicit_rate = str(row.get("General Rate of Duty", "")).strip()
            if explicit_rate:
                rate_stack[indent] = explicit_rate
            inherited_rate = explicit_rate
            if not inherited_rate:
                parent_levels = [level for level in rate_stack if level < indent]
                if parent_levels:
                    inherited_rate = rate_stack[max(parent_levels)]

            key = normalize_hts(code)
            index[key] = {
                "code": code,
                "description": description,
                "descriptionPath": " > ".join(
                    description_stack[level] for level in sorted(description_stack) if level <= indent
                ),
                "generalRateText": inherited_rate,
                "generalRate": parse_ad_valorem_rate(inherited_rate),
                "indent": indent,
            }
    return index


def _is_imported(shipment: dict[str, Any], today: date) -> bool:
    value = str(shipment.get("importDate", "")).strip()
    if not value:
        return False
    try:
        return date.fromisoformat(value[:10]) <= today
    except ValueError:
        return False


def evaluate_item(
    item: dict[str, Any],
    shipment: dict[str, Any],
    hts_index: dict[str, dict[str, Any]],
    threshold: int,
    dataset_version: str,
    today: date | None = None,
) -> dict[str, Any]:
    """Evaluate one line without inventing an HTS classification.

    Automatic mode validates the declared code against the bundled official table.
    A human decision may override the recommended code/rate when reviewer and basis
    are recorded in ``manualDecision``.
    """
    today = today or date.today()
    declared_code = str(item.get("declaredHtsCode", "")).strip()
    declared_rate = float(item.get("dutyRateDeclared", 0) or 0)
    declared_value = float(item.get("declaredValueUsd", 0) or 0)
    declared_match = hts_index.get(normalize_hts(declared_code))

    manual = item.get("manualDecision") or {}
    manual_code = str(manual.get("recommendedHtsCode", "")).strip()
    reviewer = str(manual.get("reviewer", "")).strip()
    manual_basis = str(manual.get("ruleCitation", "")).strip()
    has_manual_decision = bool(manual_code and reviewer and manual_basis)

    if has_manual_decision:
        recommended_code = manual_code
        recommended_match = hts_index.get(normalize_hts(recommended_code))
        manual_rate = manual.get("dutyRateCalculated")
        if manual_rate not in (None, ""):
            calculated_rate = float(manual_rate)
        elif recommended_match and recommended_match.get("generalRate") is not None:
            calculated_rate = float(recommended_match["generalRate"])
        else:
            calculated_rate = declared_rate
        confidence = 95 if recommended_match else 60
        decision_source = f"담당자 · {reviewer}"
        citation = f"담당자 판정: {manual_basis}"
        if recommended_match:
            citation += (
                f" · {dataset_version} {recommended_match['code']}"
                f" (General {recommended_match['generalRateText'] or '세율 별도 확인'})"
            )
    elif declared_match:
        recommended_code = str(declared_match["code"])
        official_rate = declared_match.get("generalRate")
        calculated_rate = declared_rate if official_rate is None else float(official_rate)
        rate_matches = official_rate is not None and abs(declared_rate - float(official_rate)) < 0.001
        confidence = 90 if rate_matches else 75 if official_rate is not None else 65
        decision_source = "공식표 자동검증"
        citation = (
            f"{dataset_version} {declared_match['code']}"
            f" · General {declared_match['generalRateText'] or '복합·종량세로 담당자 확인 필요'}"
        )
    else:
        recommended_code = ""
        calculated_rate = declared_rate
        confidence = 30
        decision_source = "담당자 확인 필요"
        citation = f"{dataset_version}에서 신고 HTS와 정확히 일치하는 행을 찾지 못함"

    duty_difference = round(declared_value * (calculated_rate - declared_rate) / 100, 2)
    hts_changed = bool(recommended_code) and normalize_hts(recommended_code) != normalize_hts(declared_code)
    correction_needed = hts_changed or abs(duty_difference) >= 0.01
    psc_candidate = _is_imported(shipment, today) and correction_needed

    if not declared_match and not has_manual_decision:
        risk_level = "매우 높음"
    elif has_manual_decision and not hts_index.get(normalize_hts(recommended_code)):
        risk_level = "매우 높음"
    elif correction_needed or psc_candidate:
        risk_level = "높음"
    elif confidence < threshold:
        risk_level = "보통"
    else:
        risk_level = "낮음"

    return {
        "recommendedHtsCode": recommended_code,
        "confidenceScore": confidence,
        "dutyRateCalculated": calculated_rate,
        "dutyDifferenceUsd": duty_difference,
        "riskLevel": risk_level,
        "pscRequired": psc_candidate,
        "ruleCitation": citation,
        "decisionSource": decision_source,
    }
