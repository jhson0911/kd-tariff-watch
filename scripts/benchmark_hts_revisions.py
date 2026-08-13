from __future__ import annotations

import argparse
import csv
import gc
import json
import statistics
import time
from pathlib import Path

from build_official_data import build_changes, read_hts


PROJECT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_DIR.parents[1]
DATA_DIR = WORKSPACE_DIR / "03_데이터" / "02_HTS_판본"


def independent_rows(path: Path) -> tuple[list[str], dict[str, tuple[str, ...]]]:
    """Build an independent canonical row map with csv.reader."""
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = csv.reader(source)
        header = next(rows)
        code_index = header.index("HTS Number")
        result: dict[str, tuple[str, ...]] = {}
        for row in rows:
            row += [""] * (len(header) - len(row))
            code = row[code_index].strip()
            if code:
                result[code] = tuple(value.strip() for value in row[: len(header)])
        return header, result


def benchmark_pair(before_revision: int, runs: int) -> dict[str, object]:
    after_revision = before_revision + 1
    before_path = DATA_DIR / f"hts_2025_revision_{before_revision}.csv"
    after_path = DATA_DIR / f"hts_2025_revision_{after_revision}.csv"

    timings: list[float] = []
    before: dict[str, dict[str, str]] = {}
    after: dict[str, dict[str, str]] = {}
    changes: list[dict[str, object]] = []
    for _ in range(runs):
        gc.collect()
        started = time.perf_counter()
        before = read_hts(before_path)
        after = read_hts(after_path)
        changes = build_changes(before, after)
        json.dumps(changes, ensure_ascii=False)
        timings.append((time.perf_counter() - started) * 1_000)

    before_header, independent_before = independent_rows(before_path)
    after_header, independent_after = independent_rows(after_path)
    if before_header != after_header:
        raise ValueError(f"CSV headers differ: Revision {before_revision} and {after_revision}")

    truth = {
        code
        for code in set(independent_before) | set(independent_after)
        if independent_before.get(code) != independent_after.get(code)
    }
    predicted = {str(change["htsCode"]) for change in changes}
    true_positive = len(truth & predicted)
    false_positive = len(predicted - truth)
    false_negative = len(truth - predicted)

    change_types = {
        kind: sum(change["changeType"] == kind for change in changes)
        for kind in ("추가", "삭제", "내용 변경")
    }
    return {
        "pair": f"Rev{before_revision}->Rev{after_revision}",
        "beforeRows": len(before),
        "afterRows": len(after),
        "changes": len(changes),
        "changeTypes": change_types,
        "truePositive": true_positive,
        "falsePositive": false_positive,
        "falseNegative": false_negative,
        "precisionPct": 100 * true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 100.0,
        "recallPct": 100 * true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 100.0,
        "errorRatePct": 100 * (false_positive + false_negative) / len(truth)
        if truth
        else 0.0,
        "medianMs": statistics.median(timings),
        "meanMs": statistics.mean(timings),
        "minMs": min(timings),
        "maxMs": max(timings),
        "reviewScopeReductionPct": 100 * (1 - len(changes) / len(after)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark consecutive official HTS revisions.")
    parser.add_argument("--first", type=int, default=24)
    parser.add_argument("--last", type=int, default=32)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    results = [benchmark_pair(revision, args.runs) for revision in range(args.first, args.last)]
    total_true_positive = sum(int(result["truePositive"]) for result in results)
    total_false_positive = sum(int(result["falsePositive"]) for result in results)
    total_false_negative = sum(int(result["falseNegative"]) for result in results)
    total_truth = total_true_positive + total_false_negative

    payload = {
        "summary": {
            "versionPairs": len(results),
            "benchmarkExecutions": len(results) * args.runs,
            "uniqueInputRowsRead": sum(
                int(result["beforeRows"]) + int(result["afterRows"]) for result in results
            ),
            "truthChanges": total_truth,
            "truePositive": total_true_positive,
            "falsePositive": total_false_positive,
            "falseNegative": total_false_negative,
            "precisionPct": 100
            * total_true_positive
            / (total_true_positive + total_false_positive),
            "recallPct": 100
            * total_true_positive
            / (total_true_positive + total_false_negative),
            "errorRatePct": 100
            * (total_false_positive + total_false_negative)
            / total_truth,
            "medianPairProcessingMs": statistics.median(
                float(result["medianMs"]) for result in results
            ),
        },
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
