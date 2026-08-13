from __future__ import annotations

import copy
import hmac
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from google import genai


APP_DIR = Path(__file__).parent
OFFICIAL_DATA_FILE = APP_DIR / "data" / "official-data.json"
GEMINI_DEFAULT_MODEL = "gemini-3.6-flash"


st.set_page_config(
    page_title="미국 KD 수출품목 사전확인",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root { --navy:#002c5f; --cyan:#00aad2; --bg:#f4f7fb; }
      .stApp { background: var(--bg); }
      [data-testid="stSidebar"] { background: var(--navy); }
      [data-testid="stSidebar"] * { color: white; }
      [data-testid="stSidebar"] .stRadio label { padding: .35rem .5rem; border-radius: .5rem; }
      [data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,.10); }
      [data-testid="stMetric"] { background:white; border:1px solid #dbe4ef; padding:1rem; border-radius:.8rem; }
      [data-testid="stDataFrame"] { background:white; border:1px solid #dbe4ef; border-radius:.8rem; overflow:hidden; }
      .stButton > button, .stDownloadButton > button { border-radius:.65rem; font-weight:700; }
      .stTabs [data-baseweb="tab-list"] { gap:.4rem; }
      .stTabs [data-baseweb="tab"] { background:white; border:1px solid #dbe4ef; border-radius:.6rem; padding:.45rem .9rem; }
      .block-container { padding-top: 1.6rem; padding-bottom: 3rem; }
      .hero { background:linear-gradient(120deg,#002c5f,#075a93); color:white; padding:1.35rem 1.5rem; border-radius:1rem; margin-bottom:1rem; }
      .hero h1 { margin:0 0 .25rem; font-size:1.75rem; }
      .hero p { margin:0; color:#d7eff9; }
      .status-ok { color:#087f5b; font-weight:700; }
      .status-warn { color:#b35c00; font-weight:700; }
      a { color:#0068a8; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_official_data() -> dict[str, Any]:
    try:
        return json.loads(OFFICIAL_DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"dataset": {}, "sources": [], "notices": [], "htsChanges": []}


DEMO_SHIPMENTS = [
    {
        "entryNumber": "DEMO-ENTRY-001",
        "shipmentTitle": "KD 1차 조립용 차체 부품군",
        "importerOfRecord": "Demo Importer America Inc.",
        "brokerFiler": "Demo Customs Filer LLC",
        "carrier": "HMM",
        "portOfEntry": "Savannah, GA (1703)",
        "exportDate": "2026-07-20",
        "importDate": "2026-08-08",
        "status": "검토 필요",
        "riskLevel": "높음",
        "items": [
            {"itemNumber":"LINE-001","partNameKo":"전방 펜더 프레스 성형품","partNameEn":"Front Fender Press Stamped Sheet Assembly","declaredHtsCode":"8708.29.5060","recommendedHtsCode":"8708.29.5060","confidenceScore":98,"declaredValueUsd":420000,"quantity":3500,"dutyRateDeclared":2.5,"dutyRateCalculated":2.5,"dutyDifferenceUsd":0,"riskLevel":"낮음","pscRequired":False,"ruleCitation":"CBP Ruling HQ 965412"},
            {"itemNumber":"LINE-002","partNameKo":"EV 배터리 트레이 구조 프레임","partNameEn":"EV Battery Tray Structural Reinforced Frame","declaredHtsCode":"7616.99.5190","recommendedHtsCode":"8708.29.5060","confidenceScore":89,"declaredValueUsd":580000,"quantity":1200,"dutyRateDeclared":2.5,"dutyRateCalculated":27.5,"dutyDifferenceUsd":145000,"riskLevel":"매우 높음","pscRequired":True,"ruleCitation":"Federal Register 2025-21940 / CBP Ruling NY N310245"},
            {"itemNumber":"LINE-003","partNameKo":"후방 액슬 크로스멤버","partNameEn":"Rear Axle Crossmember Sub-Assembly","declaredHtsCode":"8708.80.6590","recommendedHtsCode":"8708.80.6590","confidenceScore":95,"declaredValueUsd":150000,"quantity":800,"dutyRateDeclared":2.5,"dutyRateCalculated":2.5,"dutyDifferenceUsd":0,"riskLevel":"낮음","pscRequired":False,"ruleCitation":"USITC Chapter 87 Note 3"},
            {"itemNumber":"LINE-004","partNameKo":"KD 고정용 철강 브래킷","partNameEn":"Iron Stamped Fastener Bracket Kit","declaredHtsCode":"7326.90.8688","recommendedHtsCode":"8708.29.5060","confidenceScore":78,"declaredValueUsd":100000,"quantity":5000,"dutyRateDeclared":2.9,"dutyRateCalculated":27.5,"dutyDifferenceUsd":24600,"riskLevel":"높음","pscRequired":True,"ruleCitation":"CBP Ruling HQ H301192"},
        ],
    },
    {
        "entryNumber": "DEMO-ENTRY-002",
        "shipmentTitle": "엔진·파워트레인 KD 컨테이너 2차분",
        "importerOfRecord": "Demo Importer America Inc.",
        "brokerFiler": "Demo Customs Filer LLC",
        "carrier": "Maersk Line",
        "portOfEntry": "Mobile, AL (1901)",
        "exportDate": "2026-07-15",
        "importDate": "2026-08-01",
        "status": "승인",
        "riskLevel": "낮음",
        "items": [
            {"itemNumber":"LINE-001","partNameKo":"2.5L 가솔린 엔진 조립체","partNameEn":"2.5L Gasoline Engine Assembly","declaredHtsCode":"8407.34.5000","recommendedHtsCode":"8407.34.5000","confidenceScore":99,"declaredValueUsd":650000,"quantity":260,"dutyRateDeclared":2.5,"dutyRateCalculated":2.5,"dutyDifferenceUsd":0,"riskLevel":"낮음","pscRequired":False,"ruleCitation":"HTS Chapter 84 Note 2"},
            {"itemNumber":"LINE-002","partNameKo":"8단 자동변속기 모듈","partNameEn":"8-Speed Automatic Transmission Module","declaredHtsCode":"8708.40.1100","recommendedHtsCode":"8708.40.1100","confidenceScore":96,"declaredValueUsd":240000,"quantity":260,"dutyRateDeclared":2.5,"dutyRateCalculated":2.5,"dutyDifferenceUsd":0,"riskLevel":"낮음","pscRequired":False,"ruleCitation":"CBP Ruling NY K82310"},
        ],
    },
    {
        "entryNumber": "DEMO-ENTRY-003",
        "shipmentTitle": "전기차 전장·조명 수시 선적분",
        "importerOfRecord": "Demo Importer America Inc.",
        "brokerFiler": "Demo Customs Filer LLC",
        "carrier": "ONE",
        "portOfEntry": "Los Angeles, CA (2704)",
        "exportDate": "2026-08-01",
        "importDate": "2026-08-12",
        "status": "분석 중",
        "riskLevel": "보통",
        "items": [
            {"itemNumber":"LINE-001","partNameKo":"고전압 와이어링 하네스","partNameEn":"High Voltage Wiring Harness","declaredHtsCode":"8544.30.0000","recommendedHtsCode":"8544.30.0000","confidenceScore":94,"declaredValueUsd":320000,"quantity":1500,"dutyRateDeclared":5.0,"dutyRateCalculated":5.0,"dutyDifferenceUsd":0,"riskLevel":"낮음","pscRequired":False,"ruleCitation":"CBP Ruling NY G81203"},
            {"itemNumber":"LINE-002","partNameKo":"전방 LED 헤드램프 모듈","partNameEn":"Front Matrix LED Headlamp","declaredHtsCode":"8512.20.2040","recommendedHtsCode":"8512.20.2040","confidenceScore":91,"declaredValueUsd":350000,"quantity":2000,"dutyRateDeclared":0.0,"dutyRateCalculated":25.0,"dutyDifferenceUsd":87500,"riskLevel":"보통","pscRequired":True,"ruleCitation":"Section 301 적용 여부 확인 필요"},
        ],
    },
]


def initialize_state() -> None:
    defaults = {
        "shipments": copy.deepcopy(DEMO_SHIPMENTS),
        "analysis_runs": [],
        "reviews": [],
        "audit_log": [],
        "messages": [{"role": "assistant", "content": "품목번호, 관세율, 추가관세 또는 신고 정정 절차를 질문해 주세요."}],
        "previous_interaction_id": None,
        "selected_entry": DEMO_SHIPMENTS[0]["entryNumber"],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def shipment_totals(shipment: dict[str, Any]) -> dict[str, float]:
    items = shipment.get("items", [])
    return {
        "value": sum(float(item.get("declaredValueUsd", 0)) for item in items),
        "declared_duty": sum(float(item.get("declaredValueUsd", 0)) * float(item.get("dutyRateDeclared", 0)) / 100 for item in items),
        "calculated_duty": sum(float(item.get("declaredValueUsd", 0)) * float(item.get("dutyRateCalculated", item.get("dutyRateDeclared", 0))) / 100 for item in items),
        "gap": sum(float(item.get("dutyDifferenceUsd", 0)) for item in items),
    }


def selected_shipment() -> dict[str, Any]:
    return next(
        (s for s in st.session_state.shipments if s["entryNumber"] == st.session_state.selected_entry),
        st.session_state.shipments[0],
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def currency(value: float) -> str:
    return f"${value:,.0f}"


def record_audit(action: str, target: str, detail: str = "") -> None:
    st.session_state.audit_log.insert(0, {
        "시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "역할": st.session_state.get("role", "한국 수출 관리"),
        "작업": action,
        "대상": target,
        "상세": detail,
    })


def state_snapshot() -> bytes:
    payload = {
        "version": 1,
        "exportedAt": datetime.now().isoformat(timespec="seconds"),
        "shipments": st.session_state.shipments,
        "analysis_runs": st.session_state.analysis_runs,
        "reviews": st.session_state.reviews,
        "audit_log": st.session_state.audit_log,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def restore_snapshot(uploaded_file: Any) -> None:
    payload = json.loads(uploaded_file.getvalue().decode("utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("shipments"), list):
        raise ValueError("지원하지 않는 백업 파일입니다.")
    if not payload["shipments"]:
        raise ValueError("신고서가 하나 이상 필요합니다.")
    st.session_state.shipments = payload["shipments"]
    st.session_state.analysis_runs = payload.get("analysis_runs", [])
    st.session_state.reviews = payload.get("reviews", [])
    st.session_state.audit_log = payload.get("audit_log", [])
    st.session_state.selected_entry = payload["shipments"][0]["entryNumber"]
    record_audit("백업 복원", "전체 작업 데이터", payload.get("exportedAt", ""))


def items_report_frame(shipment: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in shipment.get("items", []):
        rows.append({
            "품목번호": item.get("itemNumber", ""),
            "품명": item.get("partNameKo") or item.get("partNameEn", ""),
            "신고 HTS": item.get("declaredHtsCode", ""),
            "추천 HTS": item.get("recommendedHtsCode", ""),
            "신뢰도": item.get("confidenceScore", 0),
            "신고가액": item.get("declaredValueUsd", 0),
            "신고 세율": item.get("dutyRateDeclared", 0),
            "검토 세율": item.get("dutyRateCalculated", 0),
            "관세차액": item.get("dutyDifferenceUsd", 0),
            "위험도": item.get("riskLevel", ""),
            "PSC 후보": "예" if item.get("pscRequired") else "아니오",
            "판정 근거": item.get("ruleCitation", ""),
        })
    return pd.DataFrame(rows)


def analysis_brief(shipment: dict[str, Any]) -> str:
    total = shipment_totals(shipment)
    candidates = [i for i in shipment["items"] if i.get("pscRequired") or i.get("declaredHtsCode") != i.get("recommendedHtsCode")]
    lines = [
        f"# {shipment['entryNumber']} HTS 사전검토 보고서",
        "",
        f"- 선적명: {shipment['shipmentTitle']}",
        f"- 수입자: {shipment['importerOfRecord']}",
        f"- 입항항구: {shipment['portOfEntry']}",
        f"- 신고가액: {currency(total['value'])}",
        f"- 예상 관세차액: {currency(total['gap'])}",
        f"- 정정 검토 후보: {len(candidates)}개",
        "",
        "## 우선 검토 품목",
    ]
    for item in candidates:
        lines.append(f"- {item['itemNumber']} {item.get('partNameKo') or item.get('partNameEn')}: {item.get('declaredHtsCode')} → {item.get('recommendedHtsCode')} / 차액 {currency(float(item.get('dutyDifferenceUsd', 0)))}")
    if not candidates:
        lines.append("- 현재 후보 없음")
    lines.extend(["", "> 최종 품목분류와 신고 여부는 관세사 및 미국 통관 담당자의 확인이 필요합니다."])
    return "\n".join(lines)


def page_dashboard() -> None:
    hero("미국 KD 수출품목 사전확인", "미국 수입신고 전 HTS 분류와 관세 영향을 한 화면에서 검토합니다.")
    shipments = st.session_state.shipments
    totals = [shipment_totals(s) for s in shipments]
    risky = sum(s.get("riskLevel") in {"높음", "매우 높음"} for s in shipments)
    psc = sum(item.get("pscRequired", False) for s in shipments for item in s.get("items", []))
    cols = st.columns(4)
    cols[0].metric("전체 신고서", f"{len(shipments)}건")
    cols[1].metric("총 신고가액", currency(sum(t["value"] for t in totals)))
    cols[2].metric("고위험 신고서", f"{risky}건")
    cols[3].metric("정정 검토 품목", f"{psc}개")

    urgent_items = []
    for shipment in shipments:
        for item in shipment.get("items", []):
            if item.get("pscRequired") or item.get("riskLevel") in {"높음", "매우 높음"}:
                urgent_items.append({
                    "우선순위": "긴급" if item.get("riskLevel") == "매우 높음" else "확인 필요",
                    "신고번호": shipment["entryNumber"],
                    "품목": item.get("partNameKo") or item.get("partNameEn"),
                    "관세차액": item.get("dutyDifferenceUsd", 0),
                    "조치": "PSC 검토" if item.get("pscRequired") else "분류 근거 확인",
                })
    if urgent_items:
        with st.expander(f"오늘의 우선 검토 작업 · {len(urgent_items)}개", expanded=True):
            st.dataframe(pd.DataFrame(urgent_items), width="stretch", hide_index=True,
                         column_config={"관세차액": st.column_config.NumberColumn(format="$%.0f")})

    st.subheader("최근 신고서")
    rows = []
    for shipment, total in zip(shipments, totals):
        rows.append({
            "신고번호": shipment["entryNumber"], "선적명": shipment["shipmentTitle"],
            "입항항구": shipment["portOfEntry"], "상태": shipment["status"],
            "위험도": shipment["riskLevel"], "품목 수": len(shipment["items"]),
            "신고가액": total["value"], "예상 관세차액": total["gap"],
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True,
                 column_config={"신고가액": st.column_config.NumberColumn(format="$%.0f"), "예상 관세차액": st.column_config.NumberColumn(format="$%.0f")})

    st.subheader("신고서별 관세 비교")
    chart_rows = []
    for shipment, total in zip(shipments, totals):
        chart_rows.extend([
            {"신고번호": shipment["entryNumber"], "구분": "신고 관세", "금액": total["declared_duty"]},
            {"신고번호": shipment["entryNumber"], "구분": "검토 관세", "금액": total["calculated_duty"]},
        ])
    st.bar_chart(pd.DataFrame(chart_rows), x="신고번호", y="금액", color="구분", stack=False)


def parse_upload(uploaded_file: Any) -> dict[str, Any]:
    frame = pd.read_csv(uploaded_file)
    required = {"entryNumber", "shipmentTitle", "itemNumber", "partNameEn", "declaredHtsCode", "declaredValueUsd", "quantity", "dutyRateDeclared"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("필수 열이 없습니다: " + ", ".join(missing))
    first = frame.iloc[0]
    items = []
    for _, row in frame.iterrows():
        value, rate = float(row["declaredValueUsd"]), float(row["dutyRateDeclared"])
        items.append({
            "itemNumber": str(row["itemNumber"]), "partNameKo": str(row.get("partNameKo", "")), "partNameEn": str(row["partNameEn"]),
            "declaredHtsCode": str(row["declaredHtsCode"]), "recommendedHtsCode": str(row["declaredHtsCode"]),
            "confidenceScore": 0, "declaredValueUsd": value, "quantity": float(row["quantity"]),
            "dutyRateDeclared": rate, "dutyRateCalculated": rate, "dutyDifferenceUsd": 0,
            "riskLevel": "미분석", "pscRequired": False, "ruleCitation": "분석 실행 필요",
        })
    return {
        "entryNumber": str(first["entryNumber"]), "shipmentTitle": str(first["shipmentTitle"]),
        "importerOfRecord": str(first.get("importerOfRecord", "")), "brokerFiler": str(first.get("brokerFiler", "")),
        "carrier": str(first.get("carrier", "")), "portOfEntry": str(first.get("portOfEntry", "")),
        "exportDate": str(first.get("exportDate", "")), "importDate": str(first.get("importDate", "")),
        "status": "업로드", "riskLevel": "미분석", "items": items,
    }


def page_shipments() -> None:
    hero("통관 신고서 관리", "CSV 신고자료를 등록하고 품목별 HTS 검토 상태를 확인합니다.")
    with st.expander("CSV 신고자료 업로드", expanded=False):
        st.caption("등록양식: public/선적자료_등록양식.csv")
        uploaded = st.file_uploader("신고자료 CSV", type=["csv"])
        parsed_shipment = None
        if uploaded:
            try:
                parsed_shipment = parse_upload(uploaded)
                st.success(f"형식 확인 완료 · {parsed_shipment['entryNumber']} · {len(parsed_shipment['items'])}개 품목")
                st.dataframe(items_report_frame(parsed_shipment).head(5), width="stretch", hide_index=True)
            except Exception as exc:
                st.error(f"CSV를 읽지 못했습니다: {exc}")
        if parsed_shipment and st.button("확인한 신고서 등록", type="primary"):
            existing = [s for s in st.session_state.shipments if s["entryNumber"] != parsed_shipment["entryNumber"]]
            st.session_state.shipments = [parsed_shipment, *existing]
            st.session_state.selected_entry = parsed_shipment["entryNumber"]
            record_audit("신고서 등록", parsed_shipment["entryNumber"], f"{len(parsed_shipment['items'])}개 품목")
            st.success("신고서를 등록했습니다.")
            st.rerun()

    options = [s["entryNumber"] for s in st.session_state.shipments]
    current_index = options.index(st.session_state.selected_entry) if st.session_state.selected_entry in options else 0
    st.session_state.selected_entry = st.selectbox("신고서 선택", options, index=current_index)
    shipment = selected_shipment()
    total = shipment_totals(shipment)
    cols = st.columns(4)
    cols[0].metric("품목", f"{len(shipment['items'])}개")
    cols[1].metric("신고가액", currency(total["value"]))
    cols[2].metric("예상 관세차액", currency(total["gap"]))
    cols[3].metric("위험도", shipment["riskLevel"])
    st.write(f"**{shipment['shipmentTitle']}** · {shipment['importerOfRecord']} · {shipment['portOfEntry']}")
    left, right = st.columns([1, 1])
    search = left.text_input("품목 검색", placeholder="품명 또는 HTS")
    risk_filter = right.multiselect("위험도", ["미분석", "낮음", "보통", "높음", "매우 높음"], default=[])
    item_frame = items_report_frame(shipment)
    if search:
        mask = item_frame.astype(str).apply(lambda column: column.str.contains(search, case=False, na=False)).any(axis=1)
        item_frame = item_frame[mask]
    if risk_filter:
        item_frame = item_frame[item_frame["위험도"].isin(risk_filter)]
    st.dataframe(item_frame, width="stretch", hide_index=True,
                 column_config={"신고가액": st.column_config.NumberColumn(format="$%.0f"), "관세차액": st.column_config.NumberColumn(format="$%.0f")})
    download_left, download_right = st.columns(2)
    download_left.download_button("품목 검토표 CSV", item_frame.to_csv(index=False).encode("utf-8-sig"), f"{shipment['entryNumber']}_items.csv", "text/csv", width="stretch")
    download_right.download_button("사전검토 보고서", analysis_brief(shipment).encode("utf-8"), f"{shipment['entryNumber']}_brief.md", "text/markdown", width="stretch")


def run_analysis(shipment: dict[str, Any], threshold: int) -> None:
    items = shipment["items"]
    for item in items:
        confidence = float(item.get("confidenceScore", 0))
        mismatch = item.get("recommendedHtsCode") != item.get("declaredHtsCode")
        if mismatch or item.get("pscRequired") or (confidence and confidence < threshold):
            item["riskLevel"] = "높음" if mismatch or item.get("pscRequired") else "보통"
    risky = [i for i in items if i.get("riskLevel") in {"높음", "매우 높음"} or i.get("pscRequired")]
    shipment["riskLevel"] = "높음" if risky else "낮음"
    shipment["status"] = "검토 필요" if risky else "승인"
    scores = [float(i.get("confidenceScore", 0)) for i in items if float(i.get("confidenceScore", 0)) > 0]
    st.session_state.analysis_runs.insert(0, {
        "실행시각": datetime.now().strftime("%Y-%m-%d %H:%M"), "신고번호": shipment["entryNumber"],
        "품목 수": len(items), "검토 필요": len(risky), "PSC 후보": sum(bool(i.get("pscRequired")) for i in items),
        "평균 신뢰도": round(sum(scores) / len(scores), 1) if scores else 0,
        "예상 관세차액": shipment_totals(shipment)["gap"],
    })
    record_audit("사전 분석", shipment["entryNumber"], f"검토 필요 {len(risky)}개")


def page_analysis() -> None:
    hero("사전 분석 실행", "신고 HTS와 추천 HTS, 신뢰도, PSC 필요 여부를 기준으로 검토 대상을 선별합니다.")
    options = [s["entryNumber"] for s in st.session_state.shipments]
    entry = st.selectbox("분석할 신고서", options)
    threshold = st.slider("검토 신뢰도 기준", 50, 100, 85)
    shipment = next(s for s in st.session_state.shipments if s["entryNumber"] == entry)
    if st.button("사전 분석 실행", type="primary", width="stretch"):
        run_analysis(shipment, threshold)
        st.session_state.selected_entry = entry
        st.success("분석을 완료했습니다. 검토 대상과 관세차액을 확인해 주세요.")
    if st.session_state.analysis_runs:
        st.subheader("분석 이력")
        runs_frame = pd.DataFrame(st.session_state.analysis_runs)
        st.dataframe(runs_frame, width="stretch", hide_index=True)
        st.download_button("분석 이력 CSV", runs_frame.to_csv(index=False).encode("utf-8-sig"), "analysis_runs.csv", "text/csv")
    st.subheader("현재 품목 판정")
    st.dataframe(items_report_frame(shipment), width="stretch", hide_index=True)


def page_impact() -> None:
    hero("관세 영향 시각화", "신고 관세와 검토 후 관세를 비교해 우선 검토 대상을 찾습니다.")
    rows = []
    for shipment in st.session_state.shipments:
        total = shipment_totals(shipment)
        rows.append({"신고번호": shipment["entryNumber"], "신고 관세": total["declared_duty"], "검토 관세": total["calculated_duty"], "차액": total["gap"]})
    frame = pd.DataFrame(rows)
    st.dataframe(frame, width="stretch", hide_index=True, column_config={c: st.column_config.NumberColumn(format="$%.0f") for c in ["신고 관세", "검토 관세", "차액"]})
    long = frame.melt(id_vars="신고번호", value_vars=["신고 관세", "검토 관세"], var_name="구분", value_name="금액")
    st.bar_chart(long, x="신고번호", y="금액", color="구분", stack=False)


def page_reviews() -> None:
    hero("정정 검토 요청", "오분류 또는 관세차액이 있는 품목을 미국 통관 담당자와 검토합니다.")
    shipment = selected_shipment()
    candidates = [i for i in shipment["items"] if i.get("pscRequired") or i.get("declaredHtsCode") != i.get("recommendedHtsCode")]
    if candidates:
        labels = [f"{i['itemNumber']} · {i['partNameKo'] or i['partNameEn']}" for i in candidates]
        selected = st.selectbox("검토 품목", labels)
        form_left, form_right = st.columns(2)
        owner = form_left.selectbox("담당자", ["한국 수출 관리", "미국 통관", "원산지 검토"])
        due_date = form_right.date_input("검토 기한")
        reason = st.text_area("검토 사유", placeholder="분류 근거와 확인이 필요한 사항을 입력하세요.")
        if st.button("검토 요청 생성", type="primary"):
            item = candidates[labels.index(selected)]
            review_id = f"REV-{datetime.now().strftime('%m%d%H%M%S')}"
            st.session_state.reviews.insert(0, {"요청번호":review_id, "생성시각":datetime.now().strftime("%Y-%m-%d %H:%M"), "신고번호":shipment["entryNumber"], "품목":item["partNameKo"] or item["partNameEn"], "신고 HTS":item["declaredHtsCode"], "추천 HTS":item["recommendedHtsCode"], "담당자":owner, "검토기한":str(due_date), "상태":"대기", "사유":reason, "검토의견":""})
            record_audit("검토 요청 생성", review_id, shipment["entryNumber"])
            st.success("검토 요청을 생성했습니다.")
    else:
        st.info("현재 선택 신고서에는 정정 검토 후보가 없습니다.")
    if st.session_state.reviews:
        review_frame = pd.DataFrame(st.session_state.reviews)
        status_filter = st.multiselect("상태 필터", ["대기", "검토 중", "승인", "반려", "PSC 완료"], default=[])
        visible_reviews = review_frame if not status_filter else review_frame[review_frame["상태"].isin(status_filter)]
        st.dataframe(visible_reviews, width="stretch", hide_index=True)
        st.download_button("검토 요청 목록 CSV", visible_reviews.to_csv(index=False).encode("utf-8-sig"), "review_requests.csv", "text/csv")
        st.subheader("검토 상태 처리")
        review_ids = [review["요청번호"] for review in st.session_state.reviews]
        target_id = st.selectbox("요청번호", review_ids)
        target_review = next(review for review in st.session_state.reviews if review["요청번호"] == target_id)
        status_options = ["대기", "검토 중", "승인", "반려", "PSC 완료"]
        status = st.selectbox("변경 상태", status_options, index=status_options.index(target_review["상태"]))
        comment = st.text_area("검토 의견", value=target_review.get("검토의견", ""), key=f"comment-{target_id}")
        if st.button("상태 저장"):
            target_review["상태"] = status
            target_review["검토의견"] = comment
            record_audit("검토 상태 변경", target_id, status)
            st.success("검토 상태를 저장했습니다.")


def page_official_data(official: dict[str, Any]) -> None:
    hero("공식 공지·HTS 변경자료", "Federal Register와 USITC 판본 비교 결과를 조회합니다.")
    dataset = official.get("dataset", {})
    cols = st.columns(3)
    cols[0].metric("이전 판본", dataset.get("previousVersion", "-"))
    cols[1].metric("현재 판본", dataset.get("currentVersion", "-"))
    cols[2].metric("변경 항목", f"{dataset.get('changeCount', 0)}건")
    st.subheader("HTS 변경 항목")
    changes = official.get("htsChanges", [])
    if changes:
        changes_frame = pd.DataFrame(changes)[["htsCode", "changeType", "descriptionEn", "generalRateBefore", "generalRateAfter"]]
        search = st.text_input("HTS·설명 검색", placeholder="예: 9903.94 또는 automobile parts")
        if search:
            mask = changes_frame.astype(str).apply(lambda column: column.str.contains(search, case=False, na=False)).any(axis=1)
            changes_frame = changes_frame[mask]
        st.dataframe(changes_frame, width="stretch", hide_index=True)
        st.download_button("HTS 변경자료 CSV", changes_frame.to_csv(index=False).encode("utf-8-sig"), "official_hts_changes.csv", "text/csv")
    st.subheader("공식 출처")
    for source in official.get("sources", []):
        st.markdown(f"- [{source.get('publisher', source.get('id', '공식 자료'))}]({source.get('url', '#')})")


def build_ai_prompt(question: str, official: dict[str, Any]) -> str:
    shipment = selected_shipment()
    context = {
        "selected_shipment": shipment,
        "official_dataset": official.get("dataset", {}),
        "official_sources": official.get("sources", []),
        "hts_changes": official.get("htsChanges", [])[:20],
    }
    return f"""당신은 미국 수입통관과 한국산 KD 자동차 부품의 HTS 사전검토를 돕는 실무 AI입니다.
한국어로 간결하게 답하고 반드시 '확인된 사실', '위험 또는 불확실성', '다음 조치' 순서로 작성하세요.
법적 최종판단으로 단정하지 말고, 제공 자료 밖의 품목번호나 관세율을 만들어내지 마세요.

업무 맥락:
{json.dumps(context, ensure_ascii=False, default=str)}

질문: {question}"""


def page_ai(official: dict[str, Any], api_key: str, model: str) -> None:
    hero("AI 관세 도우미", "API 키는 Streamlit 서버의 Secrets에서만 사용되며 브라우저에 노출되지 않습니다.")
    if api_key:
        st.markdown(f'<p class="status-ok">● Gemini 연결 준비됨 · {model}</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-warn">● Gemini API 키가 설정되지 않았습니다.</p>', unsafe_allow_html=True)
        st.info('Streamlit Cloud의 App settings → Secrets에 GEMINI_API_KEY="..."를 등록하세요.')
    control_left, control_right = st.columns([4, 1])
    quick_question = control_left.selectbox("빠른 질문", ["선택", "선택 신고서의 고위험 품목을 요약해줘", "예상 관세차액과 PSC 후보를 정리해줘", "다음 담당자에게 전달할 검토 체크리스트를 만들어줘"])
    if control_right.button("대화 초기화", width="stretch"):
        st.session_state.messages = [{"role": "assistant", "content": "새 대화를 시작했습니다. 검토할 내용을 질문해 주세요."}]
        st.session_state.previous_interaction_id = None
        st.rerun()
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("선택한 신고서의 HTS·관세 위험을 질문하세요", disabled=not bool(api_key))
    if quick_question != "선택" and not question:
        if st.button("빠른 질문 보내기", type="primary"):
            question = quick_question
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("공식자료와 신고서 맥락을 확인하고 있습니다..."):
                try:
                    client = genai.Client(api_key=api_key)
                    params: dict[str, Any] = {"model": model, "input": build_ai_prompt(question, official), "store": True}
                    if st.session_state.previous_interaction_id:
                        params["previous_interaction_id"] = st.session_state.previous_interaction_id
                    interaction = client.interactions.create(**params)
                    answer = interaction.output_text or "답변을 생성하지 못했습니다."
                    st.session_state.previous_interaction_id = interaction.id
                except Exception as exc:
                    answer = f"Gemini 연결에 실패했습니다. Streamlit Secrets의 API 키와 모델 접근 권한을 확인해 주세요.\n\n오류: {exc}"
                st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})


def page_settings(official: dict[str, Any], api_key: str, model: str) -> None:
    hero("운영 설정", "작업 데이터를 백업·복원하고 AI 및 공식자료 연결 상태를 확인합니다.")
    status_left, status_mid, status_right = st.columns(3)
    status_left.metric("Gemini", "연결 준비" if api_key else "키 미설정")
    status_mid.metric("AI 모델", model)
    status_right.metric("공식자료", f"{len(official.get('sources', []))}개 출처")

    backup_tab, audit_tab, quality_tab = st.tabs(["데이터 백업", "작업 기록", "데이터 품질"])
    with backup_tab:
        st.write("현재 브라우저 세션의 신고서, 분석 이력, 검토 요청을 JSON 파일로 보관할 수 있습니다.")
        st.download_button("전체 작업 데이터 백업", state_snapshot(), f"kd_tariff_backup_{datetime.now().strftime('%Y%m%d')}.json", "application/json", width="stretch")
        backup_file = st.file_uploader("백업 파일 복원", type=["json"], key="backup-file")
        if backup_file and st.button("백업 데이터 복원", type="primary"):
            try:
                restore_snapshot(backup_file)
                st.success("백업 데이터를 복원했습니다.")
                st.rerun()
            except Exception as exc:
                st.error(f"백업을 복원하지 못했습니다: {exc}")
    with audit_tab:
        if st.session_state.audit_log:
            st.dataframe(pd.DataFrame(st.session_state.audit_log), width="stretch", hide_index=True)
        else:
            st.info("아직 기록된 작업이 없습니다.")
    with quality_tab:
        all_items = [item for shipment in st.session_state.shipments for item in shipment.get("items", [])]
        missing_confidence = sum(not float(item.get("confidenceScore", 0)) for item in all_items)
        missing_citation = sum(not item.get("ruleCitation") for item in all_items)
        duplicate_entries = len(st.session_state.shipments) - len({s["entryNumber"] for s in st.session_state.shipments})
        quality = pd.DataFrame([
            {"점검 항목":"미분석 품목", "건수":missing_confidence, "권장 조치":"사전 분석 실행"},
            {"점검 항목":"판정 근거 누락", "건수":missing_citation, "권장 조치":"공식자료 또는 Ruling 연결"},
            {"점검 항목":"중복 신고번호", "건수":duplicate_entries, "권장 조치":"업로드 자료 확인"},
        ])
        st.dataframe(quality, width="stretch", hide_index=True)
        if not api_key:
            st.warning('AI 사용 전 Streamlit Secrets에 GEMINI_API_KEY를 등록해야 합니다.')


initialize_state()
official_data = load_official_data()
try:
    gemini_api_key = str(st.secrets.get("GEMINI_API_KEY", ""))
    gemini_model = str(st.secrets.get("GEMINI_MODEL", GEMINI_DEFAULT_MODEL))
    app_password = str(st.secrets.get("APP_PASSWORD", ""))
except FileNotFoundError:
    gemini_api_key, gemini_model, app_password = "", GEMINI_DEFAULT_MODEL, ""

if app_password and not st.session_state.get("authenticated", False):
    hero("보안 로그인", "허가된 업무 담당자만 통관 사전검토 화면에 접근할 수 있습니다.")
    with st.form("login-form"):
        password_input = st.text_input("접근 비밀번호", type="password")
        submitted = st.form_submit_button("로그인", type="primary", width="stretch")
    if submitted:
        if hmac.compare_digest(password_input, app_password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

with st.sidebar:
    st.markdown("## HG · HYUNDAI GLOVIS")
    st.caption("미국 KD 세관 사전확인")
    role = st.selectbox("업무 역할", ["한국 수출 관리", "미국 통관", "원산지 검토"])
    st.session_state.role = role
    entry_options = [shipment["entryNumber"] for shipment in st.session_state.shipments]
    entry_index = entry_options.index(st.session_state.selected_entry) if st.session_state.selected_entry in entry_options else 0
    st.session_state.selected_entry = st.selectbox("활성 신고서", entry_options, index=entry_index)
    page = st.radio("업무 메뉴", ["대시보드", "통관 신고서", "사전 분석", "관세 영향", "정정 검토", "공식 자료", "AI 도우미", "운영 설정"])
    st.divider()
    if gemini_api_key:
        st.success(f"Gemini 연결됨\n\n{gemini_model}")
    else:
        st.warning("Gemini 키 미설정")
    if app_password and st.button("로그아웃", width="stretch"):
        st.session_state.authenticated = False
        st.rerun()
    st.caption(f"현재 역할: {role}")

pages = {
    "대시보드": page_dashboard,
    "통관 신고서": page_shipments,
    "사전 분석": page_analysis,
    "관세 영향": page_impact,
    "정정 검토": page_reviews,
}
if page in pages:
    pages[page]()
elif page == "공식 자료":
    page_official_data(official_data)
elif page == "AI 도우미":
    page_ai(official_data, gemini_api_key, gemini_model)
else:
    page_settings(official_data, gemini_api_key, gemini_model)

st.caption("본 서비스는 사전검토 지원 도구이며 최종 품목분류·관세·신고 판단은 관세사 및 미국 통관 담당자의 확인이 필요합니다.")
