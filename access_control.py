from __future__ import annotations

ROLES = ("한국 수출 관리", "미국 통관", "원산지 검토")

ROLE_PAGES: dict[str, tuple[str, ...]] = {
    "한국 수출 관리": (
        "대시보드",
        "통관 신고서",
        "사전 분석",
        "관세 영향",
        "정정 검토",
        "공식 자료",
        "AI 도우미",
        "운영 설정",
    ),
    "미국 통관": (
        "대시보드",
        "통관 신고서",
        "사전 분석",
        "관세 영향",
        "정정 검토",
        "공식 자료",
        "AI 도우미",
    ),
    "원산지 검토": (
        "대시보드",
        "통관 신고서",
        "정정 검토",
        "공식 자료",
        "AI 도우미",
    ),
}

ROLE_ACTIONS: dict[str, frozenset[str]] = {
    "한국 수출 관리": frozenset(
        {
            "upload_shipment",
            "run_analysis",
            "create_review",
            "download_reports",
            "manage_workspace",
        }
    ),
    "미국 통관": frozenset(
        {
            "run_analysis",
            "manual_classification",
            "update_review",
            "complete_psc",
            "download_reports",
        }
    ),
    "원산지 검토": frozenset({"update_review", "download_reports"}),
}

ROLE_SUMMARIES = {
    "한국 수출 관리": "신고자료 등록 · 자동분석 · 검토 요청",
    "미국 통관": "HTS·세율 확정 · 정정 및 PSC 처리",
    "원산지 검토": "원산지 증빙 확인 · 검토 승인/반려",
}


def pages_for_role(role: str) -> tuple[str, ...]:
    return ROLE_PAGES.get(role, ROLE_PAGES[ROLES[0]])


def can_access_page(role: str, page: str) -> bool:
    return page in pages_for_role(role)


def can_perform(role: str, action: str) -> bool:
    return action in ROLE_ACTIONS.get(role, frozenset())
