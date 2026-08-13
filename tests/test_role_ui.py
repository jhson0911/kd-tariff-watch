from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_FILE = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class RoleUiTests(unittest.TestCase):
    def open_role(self, button_index: int) -> AppTest:
        app = AppTest.from_file(str(APP_FILE), default_timeout=30).run()
        self.assertEqual(
            [button.label for button in app.button],
            ["한국 수출 관리 시작", "미국 통관 시작", "원산지 검토 시작"],
        )
        app.button[button_index].click().run()
        self.assertFalse(app.exception)
        # 앱은 빈 상태로 시작한다. 화면 검증을 위해 시연용 예시를 먼저 불러온다.
        app.radio(key="page_navigation").set_value("통관 신고서").run()
        for button in app.button:
            if button.label == "시연용 예시 신고서 불러오기":
                button.click().run()
                break
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
