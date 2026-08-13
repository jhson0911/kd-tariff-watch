from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_FILE = Path(__file__).resolve().parents[1] / "streamlit_app.py"
SAMPLE_CSV = Path(__file__).resolve().parents[1] / "public" / "선적자료_예제.csv"


def sample_shipment() -> dict:
    """예제 CSV를 읽어 테스트용 신고서 한 건을 만든다."""
    import csv as _csv

    with SAMPLE_CSV.open(encoding="utf-8-sig", newline="") as source:
        rows = list(_csv.DictReader(source))
    first = rows[0]
    return {
        "entryNumber": first["entryNumber"],
        "shipmentTitle": first["shipmentTitle"],
        "importerOfRecord": first.get("importerOfRecord", ""),
        "brokerFiler": first.get("brokerFiler", ""),
        "carrier": first.get("carrier", ""),
        "portOfEntry": first.get("portOfEntry", ""),
        "exportDate": first.get("exportDate", ""),
        "importDate": first.get("importDate", ""),
        "status": "검토 필요",
        "riskLevel": "미분석",
        "items": [
            {
                "itemNumber": row["itemNumber"],
                "partNameKo": row.get("partNameKo", ""),
                "partNameEn": row["partNameEn"],
                "declaredHtsCode": row["declaredHtsCode"],
                "recommendedHtsCode": row["declaredHtsCode"],
                "confidenceScore": 0,
                "declaredValueUsd": float(row["declaredValueUsd"]),
                "quantity": float(row["quantity"]),
                "dutyRateDeclared": float(row["dutyRateDeclared"]),
                "dutyRateCalculated": float(row["dutyRateDeclared"]),
                "dutyDifferenceUsd": 0,
                "riskLevel": "미분석",
                "pscRequired": False,
                "ruleCitation": "분석 실행 필요",
            }
            for row in rows
        ],
    }


class RoleUiTests(unittest.TestCase):
    def open_role(self, button_index: int) -> AppTest:
        app = AppTest.from_file(str(APP_FILE), default_timeout=30).run()
        self.assertEqual(
            [button.label for button in app.button],
            ["한국 수출 관리 시작", "미국 통관 시작", "원산지 검토 시작"],
        )
        app.button[button_index].click().run()
        self.assertFalse(app.exception)
        # 앱은 빈 상태로 시작한다. 화면 검증을 위해 예제 CSV를 세션에 직접 넣는다.
        app.session_state["shipments"] = [sample_shipment()]
        app.session_state["selected_entry"] = sample_shipment()["entryNumber"]
        app.run()
        self.assertFalse(app.exception)
        return app

    def test_export_role_can_upload_but_not_enter_manual_classification(self) -> None:
        app = self.open_role(0)
        self.assertEqual(len(app.radio(key="page_navigation").options), 8)
        app.radio(key="page_navigation").set_value("통관 신고서").run()
        self.assertEqual([uploader.label for uploader in app.file_uploader], ["신고자료 CSV"])
        self.assertIn("예제 CSV 다운로드", [button.label for button in app.get("download_button")])
        app.radio(key="page_navigation").set_value("사전 분석").run()
        self.assertNotIn("담당자 판정 입력·수정", [expander.label for expander in app.expander])

    def test_customs_role_can_enter_manual_classification_but_not_upload(self) -> None:
        app = self.open_role(1)
        self.assertEqual(len(app.radio(key="page_navigation").options), 7)
        app.radio(key="page_navigation").set_value("통관 신고서").run()
        self.assertFalse(app.file_uploader)
        app.radio(key="page_navigation").set_value("사전 분석").run()
        self.assertIn("담당자 판정 입력·수정", [expander.label for expander in app.expander])

    def test_origin_role_has_read_and_review_focused_menu(self) -> None:
        app = self.open_role(2)
        self.assertEqual(len(app.radio(key="page_navigation").options), 5)
        menu_labels = app.radio(key="page_navigation").options
        self.assertFalse(any("사전 분석" in label for label in menu_labels))
        self.assertFalse(any("관세 영향" in label for label in menu_labels))


if __name__ == "__main__":
    unittest.main()
