from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from classification_engine import evaluate_item, load_hts_index, normalize_hts, parse_ad_valorem_rate


APP_DIR = Path(__file__).resolve().parents[1]


class ClassificationEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = load_hts_index(APP_DIR / "data" / "hts_2025_revision_32.csv")
        cls.shipment = {"importDate": "2026-08-08"}

    def test_normalizes_dotted_and_undotted_codes(self) -> None:
        self.assertEqual(normalize_hts("7326.90.8688"), "7326908688")
        self.assertEqual(normalize_hts("7326.90.86.88"), "7326908688")

    def test_parses_only_simple_ad_valorem_rates(self) -> None:
        self.assertEqual(parse_ad_valorem_rate("Free"), 0)
        self.assertEqual(parse_ad_valorem_rate("2.9%"), 2.9)
        self.assertIsNone(parse_ad_valorem_rate("6.5% + 3.2¢/kg"))

    def test_automatic_validation_uses_official_inherited_rate(self) -> None:
        result = evaluate_item(
            {"declaredHtsCode": "7326.90.8688", "dutyRateDeclared": 2.9, "declaredValueUsd": 100_000},
            self.shipment,
            self.index,
            85,
            "HTS 2025 Revision 32",
            date(2026, 8, 13),
        )
        self.assertEqual(result["recommendedHtsCode"], "7326.90.86.88")
        self.assertEqual(result["dutyRateCalculated"], 2.9)
        self.assertEqual(result["dutyDifferenceUsd"], 0)
        self.assertEqual(result["riskLevel"], "낮음")

    def test_unknown_code_is_sent_to_human_review(self) -> None:
        result = evaluate_item(
            {"declaredHtsCode": "8708.29.5060", "dutyRateDeclared": 2.5, "declaredValueUsd": 100_000},
            self.shipment,
            self.index,
            85,
            "HTS 2025 Revision 32",
            date(2026, 8, 13),
        )
        self.assertEqual(result["recommendedHtsCode"], "")
        self.assertEqual(result["riskLevel"], "매우 높음")
        self.assertEqual(result["decisionSource"], "담당자 확인 필요")

    def test_human_decision_recalculates_gap_and_psc_candidate(self) -> None:
        result = evaluate_item(
            {
                "declaredHtsCode": "7616.99.5190",
                "dutyRateDeclared": 2.5,
                "declaredValueUsd": 580_000,
                "manualDecision": {
                    "recommendedHtsCode": "8708.29.51.60",
                    "dutyRateCalculated": 15,
                    "reviewer": "관세 담당자",
                    "ruleCitation": "검토 기록 2026-08-13",
                },
            },
            self.shipment,
            self.index,
            85,
            "HTS 2025 Revision 32",
            date(2026, 8, 13),
        )
        self.assertEqual(result["dutyDifferenceUsd"], 72_500)
        self.assertEqual(result["riskLevel"], "높음")
        self.assertTrue(result["pscRequired"])
        self.assertIn("관세 담당자", result["decisionSource"])


if __name__ == "__main__":
    unittest.main()
