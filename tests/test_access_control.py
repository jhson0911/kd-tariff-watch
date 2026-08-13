from __future__ import annotations

import unittest

from access_control import ROLES, can_access_page, can_perform, pages_for_role


class AccessControlTests(unittest.TestCase):
    def test_each_role_has_a_distinct_menu(self) -> None:
        menus = [pages_for_role(role) for role in ROLES]
        self.assertEqual(len(set(menus)), 3)

    def test_export_role_owns_upload_and_review_creation(self) -> None:
        self.assertTrue(can_perform("한국 수출 관리", "upload_shipment"))
        self.assertTrue(can_perform("한국 수출 관리", "create_review"))
        self.assertFalse(can_perform("한국 수출 관리", "manual_classification"))

    def test_customs_role_owns_manual_classification_and_psc(self) -> None:
        self.assertTrue(can_perform("미국 통관", "manual_classification"))
        self.assertTrue(can_perform("미국 통관", "complete_psc"))
        self.assertFalse(can_perform("미국 통관", "upload_shipment"))

    def test_origin_role_cannot_open_analysis_or_impact(self) -> None:
        self.assertFalse(can_access_page("원산지 검토", "사전 분석"))
        self.assertFalse(can_access_page("원산지 검토", "관세 영향"))
        self.assertTrue(can_access_page("원산지 검토", "정정 검토"))
        self.assertTrue(can_perform("원산지 검토", "update_review"))
        self.assertFalse(can_perform("원산지 검토", "complete_psc"))


if __name__ == "__main__":
    unittest.main()
