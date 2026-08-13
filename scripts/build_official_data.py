from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_DIR.parents[1]
SOURCE_DIR = WORKSPACE_DIR / "03_데이터"
OUTPUT_FILE = PROJECT_DIR / "data" / "official-data.json"


def read_hts(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = csv.DictReader(source)
        return {
            row["HTS Number"].strip(): {key: (value or "").strip() for key, value in row.items()}
            for row in rows
            if row.get("HTS Number", "").strip()
        }


def build_changes(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for code in sorted(set(before) | set(after)):
        old = before.get(code)
        new = after.get(code)
        if old == new:
            continue

        if old is None:
            kind = "추가"
        elif new is None:
            kind = "삭제"
        else:
            kind = "내용 변경"

        changed_fields = []
        if old and new:
            changed_fields = [
                key for key in old.keys()
                if old.get(key, "") != new.get(key, "")
            ]

        row = new or old or {}
        changes.append({
            "htsCode": code,
            "changeType": kind,
            "descriptionEn": row.get("Description", ""),
            "generalRateBefore": old.get("General Rate of Duty", "") if old else "",
            "generalRateAfter": new.get("General Rate of Duty", "") if new else "",
            "specialRateBefore": old.get("Special Rate of Duty", "") if old else "",
            "specialRateAfter": new.get("Special Rate of Duty", "") if new else "",
            "additionalDutiesBefore": old.get("Additional Duties", "") if old else "",
            "additionalDutiesAfter": new.get("Additional Duties", "") if new else "",
            "changedFields": changed_fields,
        })
    return changes


def main() -> None:
    revision_31 = SOURCE_DIR / "02_HTS_판본" / "hts_2025_revision_31.csv"
    revision_32 = SOURCE_DIR / "02_HTS_판본" / "hts_2025_revision_32.csv"
    metadata_file = SOURCE_DIR / "01_공식공지" / "2025-21940_한미_관세협정_메타데이터.json"

    before = read_hts(revision_31)
    after = read_hts(revision_32)
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    changes = build_changes(before, after)

    notice = {
        "id": metadata["document_number"],
        "titleKo": "한미 전략적 무역·투자 합의의 관세 조치 시행 공지",
        "titleEn": metadata["title"],
        "category": "Federal Register",
        "summaryKo": (
            "한국산 자동차·자동차 부품은 2025년 11월 1일 이후, 그 밖의 상호관세 대상 품목 등은 "
            "2025년 11월 14일 이후의 수입 건부터 변경 내용이 적용됩니다. 실제 적용 여부는 품목번호, "
            "원산지와 수입 시점을 함께 확인해야 합니다."
        ),
        "contentEn": metadata["abstract"],
        "effectiveDate": metadata["effective_on"],
        "publicationDate": metadata["publication_date"],
        "documentNumber": metadata["document_number"],
        "citation": metadata["citation"],
        "federalRegisterUrl": metadata["html_url"],
        "pdfUrl": metadata["pdf_url"],
        "impactLevel": "high",
        "isImportant": True,
        "createdAt": metadata["publication_date"],
        "sourceFile": str(metadata_file.relative_to(WORKSPACE_DIR)).replace("\\", "/"),
    }

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "previousVersion": "HTS 2025 Revision 31",
            "currentVersion": "HTS 2025 Revision 32",
            "previousRowCount": len(before),
            "currentRowCount": len(after),
            "changeCount": len(changes),
            "comparisonBasis": "HTS Number가 있는 행을 기준으로 Revision 31과 32의 전체 필드를 비교",
        },
        "sources": [
            {
                "id": "federal-register-2025-21940",
                "nameKo": "미국 연방 관보 한미 관세 조치 공지",
                "publisher": "Federal Register / USTR / U.S. Department of Commerce",
                "url": metadata["html_url"],
                "localFile": notice["sourceFile"],
                "purpose": "공지 제목, 시행일, 적용 대상과 공식 원문 제공",
                "language": "영어 원문 / 한국어 요약",
            },
            {
                "id": "usitc-hts-rev31",
                "nameKo": "미국 관세율표 2025 Revision 31",
                "publisher": "U.S. International Trade Commission",
                "url": "https://www.usitc.gov/2025_hts_revision_31",
                "localFile": str(revision_31.relative_to(WORKSPACE_DIR)).replace("\\", "/"),
                "purpose": "한미 관세 조치 반영 전 기준 판본",
                "language": "영어 원문",
            },
            {
                "id": "usitc-hts-rev32",
                "nameKo": "미국 관세율표 2025 Revision 32",
                "publisher": "U.S. International Trade Commission",
                "url": "https://www.usitc.gov/2025_hts_revision_32",
                "localFile": str(revision_32.relative_to(WORKSPACE_DIR)).replace("\\", "/"),
                "purpose": "한미 관세 조치 반영 후 판본과 변경 항목 제공",
                "language": "영어 원문",
            },
            {
                "id": "cbp-csms-66987366",
                "nameKo": "미국 세관 한미 관세 이행 안내",
                "publisher": "U.S. Customs and Border Protection",
                "url": "https://content.govdelivery.com/bulletins/gd/USDHSCBP-3fe2566",
                "localFile": "03_데이터/03_통관업무_참고/CBP_CSMS_66987366_한미관세_이행지침.html",
                "purpose": "미국 세관 신고 시 적용 코드와 처리 유의사항 확인",
                "language": "영어 원문",
            },
        ],
        "notices": [notice],
        "htsChanges": changes,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE} ({len(changes)} HTS changes)")


if __name__ == "__main__":
    main()
