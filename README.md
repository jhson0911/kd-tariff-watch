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
- Streamlit Secrets 기반 선택형 팀 접근 비밀번호

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
APP_PASSWORD = "선택_접근_비밀번호"
```

## Streamlit Community Cloud 배포

1. 이 GitHub 저장소의 최신 `main` 브랜치를 사용합니다.
2. Streamlit Community Cloud에서 **Create app**을 선택합니다.
3. Repository는 `blue-sky-sailboat/us-kd-tariff-precheck`, Main file path는 `streamlit_app.py`로 지정합니다.
4. **Advanced settings → Secrets**에 아래 값을 등록합니다.

```toml
GEMINI_API_KEY = "실제_API_키"
GEMINI_MODEL = "gemini-3.6-flash"
APP_PASSWORD = "선택_접근_비밀번호"
```

5. Deploy를 실행합니다.

API 키는 Streamlit 서버에서만 읽으며 브라우저나 GitHub 저장소에 포함되지 않습니다.
`APP_PASSWORD`는 선택사항입니다. 값을 등록하면 앱 진입 전에 로그인 화면이 표시됩니다.

> 이 앱은 사전검토 지원 도구입니다. 최종 품목분류, 관세율 및 신고 판단은 관세사와 미국 통관 담당자의 확인이 필요합니다.
