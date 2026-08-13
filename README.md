# 미국 KD 수출품목 사전확인

한국산 KD 자동차 부품의 미국 수입신고 전 HTS 분류, 관세 영향, 정정 검토를 지원하는 Streamlit 앱입니다.

## 주요 기능

- 신고서 및 품목별 HTS 사전검토
- CSV 신고자료 업로드
- 신고 관세와 검토 관세 비교
- PSC 정정 검토 후보 관리
- 담당자·기한·상태 기반 검토 요청 처리
- Federal Register 및 USITC 변경자료 조회
- Gemini Interactions API 기반 관세 도우미
- 신고서별 CSV 및 Markdown 검토 보고서 다운로드
- 전체 작업 데이터 JSON 백업·복원과 작업 이력 확인
- 미분석·판정 근거 누락·중복 신고번호 데이터 품질 점검
- 버튼식 역할 선택과 역할별 메뉴·기능 권한

## 역할별 접근 권한

| 역할 | 주요 메뉴 | 변경 가능한 기능 |
|---|---|---|
| 한국 수출 관리 | 전체 업무 화면 | 신고자료 등록, 자동분석, 검토 요청 생성, 운영 설정 |
| 미국 통관 | 운영 설정을 제외한 통관·분석 화면 | 자동분석, 추천 HTS·세율 확정, 검토 상태 및 PSC 완료 처리 |
| 원산지 검토 | 대시보드, 신고서 조회, 정정 검토, 공식자료, AI | 원산지 관련 검토 승인·반려 및 의견 저장 |

앱 진입 시 역할 카드의 시작 버튼을 누릅니다. 선택된 역할은 현재 세션에 고정되며 사이드바의 `역할 변경` 버튼으로 선택 화면에 돌아갈 수 있습니다.

## 품목 판정 방식

- 자동검증은 내장된 `HTS 2025 Revision 32` 원문 CSV에서 신고 HTS의 정확한 일치 여부와 Column 1 General 기본세율을 확인합니다.
- 단순 종가세(`Free`, `2.5%` 등)만 자동 계산하며 복합세·종량세 또는 공식표 미일치 코드는 담당자 확인 대상으로 분류합니다.
- 관세차액은 `신고가액 × (검토세율 - 신고세율) ÷ 100`으로 매번 다시 계산합니다.
- 자동검증은 품명만으로 새로운 HTS를 만들지 않습니다. 관세사 또는 미국 통관 담당자가 사전 분석 화면에서 추천 HTS, 총 검토세율, 판정 근거를 저장할 수 있습니다.
- 수입일이 지났고 HTS 또는 세율 차이가 있는 경우에만 PSC 후보로 표시합니다. 실제 PSC 제출 가능 여부는 신고 상태와 CBP 절차를 별도로 확인해야 합니다.

## 로컬 실행

Python 3.11 이상 환경에서 다음 명령을 실행합니다.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

AI 연결이 필요하면 `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사하고 실제 Gemini API 키를 입력합니다. 실제 키 파일은 Git에 포함되지 않습니다.

```toml
GEMINI_API_KEY = "실제_API_키"
GEMINI_MODEL = "gemini-3.6-flash"
```

## Streamlit Community Cloud 배포

1. 이 GitHub 저장소의 최신 `main` 브랜치를 사용합니다.
2. Streamlit Community Cloud에서 **Create app**을 선택합니다.
3. Repository는 `blue-sky-sailboat/us-kd-tariff-precheck`, Main file path는 `streamlit_app.py`로 지정합니다.
4. **Advanced settings → Secrets**에 아래 값을 등록합니다.

```toml
GEMINI_API_KEY = "실제_API_키"
GEMINI_MODEL = "gemini-3.6-flash"
```

5. Deploy를 실행합니다.

API 키는 Streamlit 서버에서만 읽으며 브라우저나 GitHub 저장소에 포함되지 않습니다.

> 이 앱은 사전검토 지원 도구입니다. 최종 품목분류, 관세율 및 신고 판단은 관세사와 미국 통관 담당자의 확인이 필요합니다.
