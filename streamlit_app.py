from __future__ import annotations

import copy
import csv
import json
from datetime import datetime
from html import escape
from pathlib import Path
from textwrap import dedent
from typing import Any

import pandas as pd
import streamlit as st
from google import genai

from access_control import (
    ROLES,
    ROLE_SUMMARIES,
    can_access_page,
    can_perform,
    pages_for_role,
)
from classification_engine import evaluate_item, load_hts_index


APP_DIR = Path(__file__).parent
OFFICIAL_DATA_FILE = APP_DIR / "data" / "official-data.json"
HTS_DATA_FILE = APP_DIR / "data" / "hts_2025_revision_32.csv"
SAMPLE_SHIPMENT_FILE = APP_DIR / "public" / "선적자료_예제.csv"
GEMINI_DEFAULT_MODEL = "gemini-3.6-flash"


st.set_page_config(
    page_title="미국 KD 수출품목 사전확인",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
      :root {
        --navy-950:#071022; --navy-900:#0a1128; --navy-800:#0f1c3f;
        --navy:#002c5f; --blue:#075a93; --cyan:#00aad2;
        --ink:#172033; --muted:#64748b; --line:#dce5ef;
        --bg:#f8fafc; --panel:#ffffff; --soft:#f1f5f9;
        --success:#087f5b; --warning:#b45309; --danger:#be123c;
      }
      html, body, [class*="css"] {
        font-family:"Pretendard Variable",Pretendard,"Noto Sans KR","Segoe UI",sans-serif;
      }
      .stApp { background:var(--bg); color:var(--ink); }
      [data-testid="stHeader"] { display:block; min-height:0!important; height:0!important; background:transparent; pointer-events:none; }
      [data-testid="stToolbarActions"],[data-testid="stAppDeployButton"],[data-testid="stMainMenu"] { display:none!important; }
      [data-testid="stExpandSidebarButton"] { position:fixed!important; top:.65rem!important; left:.6rem!important; width:2.2rem!important; height:2.2rem!important;
        display:flex!important; align-items:center!important; justify-content:center!important; pointer-events:auto; z-index:150;
        color:#0f172a!important; background:white!important; border:1px solid #e2e8f0!important; border-radius:.55rem!important; box-shadow:0 4px 14px rgba(15,23,42,.08)!important; }
      .block-container { max-width:1480px; padding:0 2.25rem 3rem; }
      .stMainBlockContainer { padding-top:0; }
      h1,h2,h3 { color:#0f172a; letter-spacing:-.025em; }
      h3 { font-size:1rem!important; font-weight:800!important; }
      a { color:#0369a1; }

      /* Sidebar: original product navigation */
      [data-testid="stSidebar"] {
        background:linear-gradient(180deg,var(--navy-800) 0,var(--navy-900) 24%,var(--navy-950) 100%);
        border-right:1px solid rgba(148,163,184,.17);
        box-shadow:12px 0 36px rgba(15,23,42,.12);
      }
      [data-testid="stSidebar"][aria-expanded="true"] { width:17rem!important; min-width:17rem!important; }
      [data-testid="stSidebar"][aria-expanded="false"] { width:0!important; min-width:0!important; flex-basis:0!important; }
      [data-testid="stSidebar"] > div:first-child { padding-top:0; }
      [data-testid="stSidebarHeader"] { position:absolute; top:.65rem; right:.6rem; width:auto!important; height:0!important; min-height:0!important; padding:0!important; z-index:400; }
      [data-testid="stSidebarHeader"] button { color:white!important; background:rgba(15,23,42,.6)!important; border-radius:.5rem!important; }
      [data-testid="stSidebarCollapseButton"] { position:absolute!important; top:.65rem!important; right:.55rem!important; left:auto!important; width:2rem!important; height:2rem!important;
        display:flex!important; align-items:center!important; justify-content:center!important; color:white!important; background:rgba(15,23,42,.78)!important;
        border:1px solid rgba(148,163,184,.35)!important; border-radius:.55rem!important; z-index:300!important; box-shadow:0 6px 18px rgba(0,0,0,.18)!important; }
      [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
      [data-testid="stSidebarCollapseButton"] span { color:white!important; }
      [data-testid="stSidebarCollapsedControl"] { top:.55rem; left:.55rem; z-index:120; }
      [data-testid="stSidebarCollapsedControl"] button { background:white!important; border:1px solid #e2e8f0!important; border-radius:.55rem!important; box-shadow:0 4px 14px rgba(15,23,42,.08)!important; }
      [data-testid="stSidebarUserContent"] { margin-top:0!important; padding-top:4.85rem!important; }
      [data-testid="stSidebarContent"] { overscroll-behavior:contain; }
      [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.55rem; }
      [data-testid="stSidebar"] .stMarkdown { color:#e2e8f0; }
      [data-testid="stSidebar"] .stSelectbox label,
      [data-testid="stSidebar"] .stRadio > label {
        color:#94a3b8!important; font-size:.65rem!important; font-weight:800!important;
        letter-spacing:.08em; text-transform:uppercase;
      }
      [data-testid="stSidebar"] [data-baseweb="select"] > div {
        min-height:2.45rem; color:#e2e8f0; background:rgba(30,41,59,.82);
        border:1px solid rgba(100,116,139,.55); border-radius:.7rem;
      }
      [data-testid="stSidebar"] [data-baseweb="select"] svg { fill:#94a3b8; }
      [data-testid="stSidebar"] div[role="radiogroup"] { gap:.22rem; }
      [data-testid="stSidebar"] div[role="radiogroup"] label {
        min-height:2.55rem; padding:.58rem .72rem; border-radius:.7rem;
        color:#cbd5e1; border:1px solid transparent; transition:.16s ease;
      }
      [data-testid="stSidebar"] div[role="radiogroup"] label p { color:#94a3b8!important; font-size:.72rem; font-weight:750; }
      [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        color:white; background:rgba(51,65,85,.62);
      }
      [data-testid="stSidebar"] div[role="radiogroup"] label:hover p { color:white!important; }
      [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        color:white; background:linear-gradient(90deg,#0891b2,#1d4ed8);
        border-color:rgba(103,232,249,.28); box-shadow:0 8px 24px rgba(8,145,178,.22);
      }
      [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p { color:white!important; }
      [data-testid="stSidebar"] div[role="radiogroup"] [data-testid="stWidgetLabel"] { display:none; }
      [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child { display:none; }
      [data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div > div:first-child { display:none; }
      [data-testid="stSidebar"] hr { border-color:rgba(100,116,139,.35); margin:.35rem 0; }
      [data-testid="stSidebar"] .stButton > button {
        background:rgba(30,41,59,.84); color:#e2e8f0; border-color:rgba(100,116,139,.55);
      }
      .brand-shell { position:absolute; top:-4.85rem; left:0; z-index:200; width:17rem; box-sizing:border-box; margin:0; padding:1.2rem 1rem 1.05rem;
        background:linear-gradient(180deg,#13244d,#0a1128); border-bottom:1px solid rgba(100,116,139,.26); }
      .brand-row { display:flex; gap:.72rem; align-items:center; }
      .brand-mark { width:2.55rem; height:2.55rem; display:flex; align-items:center; justify-content:center;
        border-radius:.78rem; color:#67e8f9; background:#002c5f; border:1px solid rgba(34,211,238,.4);
        font-weight:900; box-shadow:inset 0 1px rgba(255,255,255,.12),0 8px 20px rgba(0,0,0,.18); }
      .brand-name { color:white; font-size:.82rem; font-weight:900; letter-spacing:.04em; }
      .brand-sub { color:#22d3ee; font-size:.68rem; font-weight:700; margin-top:.08rem; }
      .side-context { display:flex; align-items:center; justify-content:space-between; padding:.65rem .7rem;
        background:rgba(30,41,59,.82); border:1px solid rgba(100,116,139,.4); border-radius:.72rem;
        color:#cbd5e1; font-size:.69rem; font-weight:700; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(> .side-context) { margin-bottom:0!important; }
      .side-context span:last-child:empty { flex:0 0 .45rem; width:.45rem; height:.45rem; border-radius:99px; background:#38bdf8; box-shadow:0 0 0 4px rgba(56,189,248,.11); }
      .side-context:has(span:last-child:not(:empty)) { display:block; }
      .side-context span:last-child:not(:empty) { display:block; width:auto; height:auto; margin-top:.28rem; color:#94a3b8;
        background:none; box-shadow:none; font-size:.6rem; font-weight:600; line-height:1.45; overflow-wrap:anywhere; }
      .system-box { margin-top:.15rem; padding:.78rem; border:1px solid rgba(71,85,105,.55); border-radius:.8rem;
        background:rgba(2,6,23,.55); box-shadow:inset 0 1px rgba(255,255,255,.03); }
      .system-line { display:flex; align-items:center; justify-content:space-between; color:#cbd5e1; font-size:.67rem; font-weight:800; }
      .system-chip { color:#67e8f9; border:1px solid rgba(34,211,238,.28); background:rgba(6,182,212,.1); padding:.18rem .42rem; border-radius:.35rem; }

      /* Product header and page hero */
      .app-topbar { min-height:4rem; margin:-1rem -2.25rem 1.55rem; padding:0 2.25rem; display:flex; align-items:center;
        justify-content:space-between; background:rgba(255,255,255,.94); border-bottom:1px solid #e2e8f0;
        box-shadow:0 2px 8px rgba(15,23,42,.035); position:sticky; top:0; z-index:90; backdrop-filter:blur(15px); }
      .topbar-title { display:flex; gap:.72rem; align-items:center; color:#0f172a; font-size:.91rem; font-weight:900; }
      .topbar-title:before { content:""; width:.24rem; height:1.1rem; border-radius:10px; background:linear-gradient(#22d3ee,#2563eb); }
      .topbar-actions { display:flex; gap:.55rem; align-items:center; }
      .topbar-pill { display:inline-flex; align-items:center; gap:.4rem; padding:.42rem .68rem; border-radius:.62rem;
        font-size:.66rem; font-weight:800; border:1px solid #bae6fd; color:#075985; background:#f0f9ff; }
      .topbar-pill:before { content:""; width:.38rem; height:.38rem; border-radius:99px; background:#0ea5e9; }
      .topbar-role { padding:.42rem .68rem; border-radius:.62rem; color:#334155; background:#f8fafc; border:1px solid #e2e8f0; font-size:.66rem; font-weight:800; }
      .hero { position:relative; overflow:hidden; background:linear-gradient(120deg,#001e42 0,#002c5f 55%,#0a192f 100%);
        color:white; padding:1.55rem 1.7rem; border-radius:1.05rem; margin-bottom:1.25rem;
        border:1px solid rgba(34,211,238,.19); box-shadow:0 16px 36px rgba(0,44,95,.14); }
      .hero:after { content:""; position:absolute; width:18rem; height:18rem; right:-7rem; top:-10rem; border-radius:50%;
        background:radial-gradient(circle,rgba(34,211,238,.22),transparent 68%); }
      .hero-eyebrow { color:#67e8f9; font-size:.62rem; font-weight:900; letter-spacing:.14em; margin-bottom:.42rem; }
      .hero h1 { position:relative; z-index:1; margin:0 0 .38rem; color:white; font-size:1.42rem; font-weight:900; letter-spacing:-.03em; }
      .hero p { position:relative; z-index:1; margin:0; color:#cfe9f5; font-size:.78rem; }

      /* Cards, sections, data surfaces */
      .kpi-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1rem; margin:.15rem 0 1.35rem; }
      .kpi-card { min-height:8.2rem; padding:1.1rem 1.15rem; background:white; border:1px solid #e2e8f0; border-radius:.9rem;
        box-shadow:0 4px 14px rgba(15,23,42,.04); transition:transform .16s,border-color .16s,box-shadow .16s; }
      .kpi-card:hover { transform:translateY(-2px); border-color:#cbd5e1; box-shadow:0 10px 24px rgba(15,23,42,.07); }
      .kpi-top { display:flex; align-items:flex-start; justify-content:space-between; gap:.6rem; }
      .kpi-label { color:#64748b; font-size:.7rem; font-weight:800; line-height:1.35; }
      .kpi-icon { width:2rem; height:2rem; display:flex; align-items:center; justify-content:center; border-radius:.58rem;
        font-size:.88rem; font-weight:900; color:#1d4ed8; background:#eff6ff; border:1px solid #dbeafe; }
      .kpi-icon.cyan { color:#0e7490; background:#ecfeff; border-color:#cffafe; }
      .kpi-icon.warn { color:#b45309; background:#fffbeb; border-color:#fef3c7; }
      .kpi-icon.rose { color:#be123c; background:#fff1f2; border-color:#ffe4e6; }
      .kpi-value { margin-top:.7rem; color:#0f172a; font-size:1.5rem; line-height:1; font-weight:950; letter-spacing:-.04em; }
      .kpi-sub { margin-top:.55rem; color:#64748b; font-size:.65rem; line-height:1.35; }
      .kpi-sub.emphasis { color:#be123c; font-weight:800; }
      .section-head { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin:1.55rem 0 .72rem; }
      .section-head h3 { margin:0; font-size:.93rem!important; font-weight:900!important; }
      .section-head p { margin:.18rem 0 0; color:#64748b; font-size:.68rem; }
      .panel { background:white; border:1px solid #e2e8f0; border-radius:1rem; padding:1.1rem; box-shadow:0 4px 16px rgba(15,23,42,.035); }
      .workflow { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.72rem; padding:1rem; margin:.2rem 0 1.3rem;
        background:white; border:1px solid #e2e8f0; border-radius:1rem; box-shadow:0 4px 16px rgba(15,23,42,.035); }
      .workflow-step { position:relative; min-height:5.2rem; padding:.8rem .7rem; text-align:center; background:#f8fafc;
        border:1px solid #e2e8f0; border-radius:.75rem; }
      .workflow-step.active { background:#eff6ff; border-color:#93c5fd; }
      .workflow-num { color:#1d4ed8; font-size:.58rem; font-weight:950; letter-spacing:.08em; }
      .workflow-title { margin-top:.3rem; color:#0f172a; font-size:.7rem; font-weight:900; }
      .workflow-desc { margin-top:.22rem; color:#64748b; font-size:.59rem; }
      .shipment-list { display:grid; gap:.72rem; margin-bottom:1.25rem; }
      .shipment-card { padding:1rem 1.05rem; background:white; border:1px solid #e2e8f0; border-radius:.9rem; box-shadow:0 3px 12px rgba(15,23,42,.035); }
      .shipment-top { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; }
      .entry-chip { display:inline-block; color:#075985; background:#e0f2fe; border:1px solid #bae6fd; border-radius:.35rem;
        padding:.15rem .4rem; font-size:.58rem; font-weight:950; letter-spacing:.035em; }
      .shipment-title { margin-top:.42rem; color:#0f172a; font-size:.79rem; font-weight:900; }
      .shipment-meta { display:grid; grid-template-columns:1.25fr 1fr .8fr .8fr; gap:.75rem; margin-top:.78rem; padding-top:.72rem; border-top:1px solid #f1f5f9; }
      .meta-label { display:block; color:#94a3b8; font-size:.56rem; font-weight:700; }
      .meta-value { display:block; margin-top:.16rem; color:#334155; font-size:.65rem; font-weight:800; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .meta-value.risk { color:#be123c; }
      .badge { display:inline-flex; align-items:center; padding:.25rem .5rem; border-radius:.38rem; font-size:.59rem; font-weight:900; border:1px solid; white-space:nowrap; }
      .badge.low { color:#047857; background:#ecfdf5; border-color:#a7f3d0; }
      .badge.medium { color:#1d4ed8; background:#eff6ff; border-color:#bfdbfe; }
      .badge.high { color:#b45309; background:#fffbeb; border-color:#fde68a; }
      .badge.critical { color:#be123c; background:#fff1f2; border-color:#fecdd3; }
      .info-strip { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.75rem .9rem; margin:.1rem 0 1rem;
        border:1px solid #dbeafe; background:#eff6ff; border-radius:.75rem; color:#1e3a8a; font-size:.68rem; font-weight:750; }
      .status-ok,.status-warn { display:inline-flex; align-items:center; gap:.38rem; padding:.44rem .65rem; border-radius:.55rem; font-size:.68rem; font-weight:850; }
      .status-ok { color:#047857; background:#ecfdf5; border:1px solid #a7f3d0; }
      .status-warn { color:#b45309; background:#fffbeb; border:1px solid #fde68a; }
      .app-footer { margin-top:2rem; padding:1rem 0 .2rem; color:#64748b; font-size:.62rem; text-align:center; border-top:1px solid #e2e8f0; }

      [data-testid="stMetric"] { background:white; border:1px solid #e2e8f0; padding:1rem 1.05rem; border-radius:.85rem; box-shadow:0 4px 14px rgba(15,23,42,.035); }
      [data-testid="stMetricLabel"] { color:#64748b; font-weight:750; }
      [data-testid="stMetricValue"] { color:#0f172a; font-weight:900; letter-spacing:-.035em; }
      [data-testid="stDataFrame"] { background:white; border:1px solid #e2e8f0; border-radius:.85rem; overflow:hidden; box-shadow:0 4px 14px rgba(15,23,42,.035); }
      [data-testid="stVegaLiteChart"] { background:white; border:1px solid #e2e8f0; border-radius:.9rem; padding:.9rem; box-shadow:0 4px 14px rgba(15,23,42,.035); }
      [data-testid="stExpander"] { background:white; border:1px solid #e2e8f0; border-radius:.85rem!important; box-shadow:0 4px 14px rgba(15,23,42,.03); overflow:hidden; }
      [data-testid="stFileUploaderDropzone"] { border:1px dashed #93c5fd; background:#f8fbff; border-radius:.8rem; }
      .stButton > button,.stDownloadButton > button,.stFormSubmitButton > button {
        min-height:2.45rem; border-radius:.65rem; font-weight:850; font-size:.75rem; border-color:#cbd5e1; transition:.16s ease;
      }
      .stButton > button[kind="primary"],.stFormSubmitButton > button[kind="primary"] {
        color:white; background:linear-gradient(90deg,#0891b2,#1d4ed8); border-color:#0891b2; box-shadow:0 7px 18px rgba(8,145,178,.2);
      }
      .stButton > button:hover,.stDownloadButton > button:hover { transform:translateY(-1px); border-color:#38bdf8; color:#075985; }
      [data-baseweb="input"] > div,[data-baseweb="textarea"] > div,[data-baseweb="select"] > div {
        border-color:#d7e0ea; border-radius:.65rem; background:white;
      }
      .stTabs [data-baseweb="tab-list"] { gap:.35rem; border-bottom:1px solid #e2e8f0; }
      .stTabs [data-baseweb="tab"] { color:#64748b; background:transparent; border:0; border-radius:.5rem .5rem 0 0; padding:.55rem .85rem; font-size:.72rem; font-weight:800; }
      .stTabs [aria-selected="true"] { color:#075985!important; background:#f0f9ff!important; }
      [data-testid="stChatMessage"] { background:white; border:1px solid #e2e8f0; border-radius:.9rem; padding:.5rem .8rem; }
      [data-testid="stChatInput"] { border-radius:.8rem; box-shadow:0 7px 24px rgba(15,23,42,.08); }

      /* Readability scale and predictable Korean wrapping */
      body,.stApp { font-size:16px; }
      .stMarkdown p,[data-testid="stCaptionContainer"],[data-testid="stAlert"] p {
        font-size:.86rem; line-height:1.65; word-break:keep-all; overflow-wrap:anywhere;
      }
      [data-testid="stWidgetLabel"] p { font-size:.8rem; line-height:1.45; }
      [data-baseweb="input"] input,[data-baseweb="textarea"] textarea,[data-baseweb="select"] > div { font-size:.84rem; }
      [data-testid="stSidebar"] .stSelectbox label,[data-testid="stSidebar"] .stRadio > label { font-size:.72rem!important; }
      [data-testid="stSidebar"] div[role="radiogroup"] label p { font-size:.79rem!important; line-height:1.35; }
      [data-testid="stSidebar"] [data-baseweb="select"] > div { font-size:.82rem; }
      .brand-name { font-size:.88rem; }
      .brand-sub { font-size:.73rem; }
      .side-context { font-size:.75rem; line-height:1.45; }
      .side-context span:last-child:not(:empty) { font-size:.67rem; }
      .system-line { font-size:.73rem; }
      .system-chip { font-size:.68rem; }
      .topbar-title { font-size:1rem; white-space:nowrap; }
      .topbar-pill,.topbar-role { font-size:.72rem; white-space:nowrap; }
      .hero-eyebrow { font-size:.68rem; }
      .hero h1 { font-size:1.55rem; line-height:1.3; word-break:keep-all; overflow-wrap:anywhere; }
      .hero p { font-size:.86rem; line-height:1.65; word-break:keep-all; overflow-wrap:anywhere; }
      .kpi-label { font-size:.77rem; word-break:keep-all; overflow-wrap:anywhere; }
      .kpi-value { font-size:1.62rem; }
      .kpi-sub { font-size:.72rem; line-height:1.5; word-break:keep-all; overflow-wrap:anywhere; }
      .section-head h3 { font-size:1.04rem!important; }
      .section-head p { font-size:.76rem; line-height:1.5; word-break:keep-all; overflow-wrap:anywhere; }
      .workflow-num { font-size:.64rem; }
      .workflow-title { font-size:.77rem; line-height:1.4; word-break:keep-all; }
      .workflow-desc { font-size:.66rem; line-height:1.5; word-break:keep-all; overflow-wrap:anywhere; }
      .entry-chip { font-size:.65rem; }
      .shipment-title { font-size:.86rem; line-height:1.45; word-break:keep-all; overflow-wrap:anywhere; }
      .meta-label { font-size:.63rem; }
      .meta-value { font-size:.72rem; }
      .badge { font-size:.66rem; }
      .info-strip { font-size:.76rem; line-height:1.5; word-break:keep-all; overflow-wrap:anywhere; }
      .status-ok,.status-warn { font-size:.75rem; }
      .app-footer { font-size:.69rem; line-height:1.55; }
      [data-testid="stMetricLabel"] p { font-size:.78rem; }
      [data-testid="stMetricValue"] { font-size:1.65rem; }
      .stButton > button,.stDownloadButton > button,.stFormSubmitButton > button { font-size:.82rem; }
      .stTabs [data-baseweb="tab"] { font-size:.8rem; }

      @media (max-width:1100px) {
        .kpi-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .workflow { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .shipment-meta { grid-template-columns:repeat(2,minmax(0,1fr)); }
      }
      @media (max-width:700px) {
        [data-testid="stSidebar"][aria-expanded="true"] { width:min(17rem,86vw)!important; min-width:min(17rem,86vw)!important; }
        .brand-shell { width:min(17rem,86vw); }
        .block-container { padding:0 1rem 2rem; }
        .app-topbar { margin:-1rem -1rem 1rem; padding:0 1rem; min-height:3.5rem; }
        .topbar-actions { display:none; }
        .topbar-title { margin-left:2.45rem; }
        .hero { padding:1.25rem; border-radius:.85rem; }
        .hero h1 { font-size:1.3rem; }
        .kpi-grid { grid-template-columns:1fr; gap:.65rem; }
        .kpi-card { min-height:auto; }
        .workflow { grid-template-columns:1fr; }
        .shipment-meta { grid-template-columns:1fr 1fr; }
        .section-head { align-items:flex-start; flex-direction:column; gap:.25rem; }
        .info-strip { align-items:flex-start; flex-direction:column; gap:.35rem; }
        .shipment-top { flex-direction:column; gap:.5rem; }
      }
      @media (max-width:420px) {
        .shipment-meta { grid-template-columns:1fr; }
      }
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


@st.cache_data
def load_official_hts_index() -> dict[str, dict[str, Any]]:
    try:
        return load_hts_index(HTS_DATA_FILE)
    except (OSError, csv.Error):
        return {}




def initialize_state() -> None:
    defaults = {
        "shipments": [],
        "analysis_runs": [],
        "reviews": [],
        "audit_log": [],
        "messages": [{"role": "assistant", "content": "품목번호, 관세율, 추가관세 또는 신고 정정 절차를 질문해 주세요."}],
        "previous_interaction_id": None,
        "selected_entry": "",
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


def selected_shipment() -> dict[str, Any] | None:
    """선택된 신고서를 돌려준다. 등록된 신고서가 없으면 None."""
    shipments = st.session_state.shipments
    if not shipments:
        return None
    return next(
        (s for s in shipments if s["entryNumber"] == st.session_state.selected_entry),
        shipments[0],
    )


def empty_state(message: str = "등록된 신고서가 없습니다.") -> None:
    """신고서가 하나도 없을 때 안내를 띄운다. 업로드가 서비스의 시작점이다."""
    st.info(f"{message}  \n\n왼쪽 메뉴의 **통관 신고서**에서 CSV 신고자료를 업로드하면 분석이 시작됩니다. "
            "같은 화면에서 예제 CSV를 내려받아 형식을 확인할 수 있습니다.")


def active_role() -> str:
    role = str(st.session_state.get("role", ROLES[0]))
    return role if role in ROLES else ROLES[0]


def topbar(page: str, role: str, official_count: int) -> None:
    st.markdown(
        f"""
        <div class="app-topbar">
          <div class="topbar-title">{escape(page)}</div>
          <div class="topbar-actions">
            <span class="topbar-pill">공식 관세 자료 {official_count}개 연결</span>
            <span class="topbar-role">{escape(role)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-eyebrow">US CUSTOMS · KD PRE-CHECK</div>
          <h1>{escape(title)}</h1>
          <p>{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_grid(cards: list[dict[str, str]]) -> None:
    markup = []
    for card in cards:
        tone = card.get("tone", "")
        sub_class = " emphasis" if card.get("emphasis") else ""
        markup.append(
            dedent(f"""
            <div class="kpi-card">
              <div class="kpi-top">
                <span class="kpi-label">{escape(card['label'])}</span>
                <span class="kpi-icon {escape(tone)}">{escape(card.get('icon', '•'))}</span>
              </div>
              <div class="kpi-value">{escape(card['value'])}</div>
              <div class="kpi-sub{sub_class}">{escape(card.get('sub', ''))}</div>
            </div>
            """).strip()
        )
    st.markdown(f'<div class="kpi-grid">{"".join(markup)}</div>', unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "") -> None:
    subtitle_markup = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f'<div class="section-head"><div><h3>{escape(title)}</h3>{subtitle_markup}</div></div>',
        unsafe_allow_html=True,
    )


def risk_badge(level: str) -> str:
    tone = {
        "낮음": "low", "보통": "medium", "높음": "high", "매우 높음": "critical", "미분석": "medium"
    }.get(level, "medium")
    return f'<span class="badge {tone}">{escape(level)}</span>'


def shipment_cards(shipments: list[dict[str, Any]]) -> None:
    cards = []
    for shipment in shipments:
        total = shipment_totals(shipment)
        cards.append(
            dedent(f"""
            <div class="shipment-card">
              <div class="shipment-top">
                <div>
                  <span class="entry-chip">{escape(str(shipment['entryNumber']))}</span>
                  <div class="shipment-title">{escape(str(shipment['shipmentTitle']))}</div>
                </div>
                {risk_badge(str(shipment.get('riskLevel', '미분석')))}
              </div>
              <div class="shipment-meta">
                <div><span class="meta-label">수입신고인 (IOR)</span><span class="meta-value">{escape(str(shipment.get('importerOfRecord', '-')))}</span></div>
                <div><span class="meta-label">입항항구</span><span class="meta-value">{escape(str(shipment.get('portOfEntry', '-')))}</span></div>
                <div><span class="meta-label">신고가액</span><span class="meta-value">{escape(currency(total['value']))}</span></div>
                <div><span class="meta-label">예상 관세차액</span><span class="meta-value risk">{escape(currency(total['gap']))}</span></div>
              </div>
            </div>
            """).strip()
        )
    st.markdown(f'<div class="shipment-list">{"".join(cards)}</div>', unsafe_allow_html=True)


def workflow_panel() -> None:
    steps = [
        ("1단계", "신고서 업로드", "CSV 품목자료 읽기"),
        ("2단계", "품목번호 확인", "신고값과 연결표 대조"),
        ("3단계", "공식 판본 비교", "공지·관세율 변경 확인"),
        ("4단계", "담당자 검토", "신고 수정 필요사항 확인"),
        ("5단계", "제출 자료 준비", "관세사 최종 확인"),
    ]
    markup = []
    for index, (number, title, description) in enumerate(steps):
        active = " active" if index == len(steps) - 1 else ""
        markup.append(
            f'<div class="workflow-step{active}"><div class="workflow-num">{number}</div>'
            f'<div class="workflow-title">{title}</div><div class="workflow-desc">{description}</div></div>'
        )
    st.markdown(f'<div class="workflow">{"".join(markup)}</div>', unsafe_allow_html=True)


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
            "판정 주체": item.get("decisionSource", "기존 저장값"),
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
    hero("미국 KD 수출품목 사전확인 및 관세 영향 분석", "미국 수입신고 전 HTS 분류, 관세 차액과 정정 검토 대상을 한 화면에서 확인합니다.")
    shipments = st.session_state.shipments
    if not shipments:
        empty_state()
        return
    totals = [shipment_totals(s) for s in shipments]
    risky = sum(s.get("riskLevel") in {"높음", "매우 높음"} for s in shipments)
    psc = sum(item.get("pscRequired", False) for s in shipments for item in s.get("items", []))
    pending = sum(s.get("status") in {"검토 필요", "분석 중"} for s in shipments)
    total_value = sum(t["value"] for t in totals)
    total_gap = sum(t["gap"] for t in totals)
    kpi_grid([
        {"label":"전체 사전분석 신고서", "value":f"{len(shipments)}건", "sub":f"신고서 총 품목 가액 · {currency(total_value)}", "icon":"▤"},
        {"label":"품목번호 고위험 선적", "value":f"{risky}건", "sub":"추가 확인이 필요한 선적 건수", "icon":"!", "tone":"rose", "emphasis":"true"},
        {"label":"신고 내용 수정 검토 품목", "value":f"{psc}개", "sub":f"예상 관세 차액 · +{currency(total_gap)}", "icon":"◇", "tone":"warn", "emphasis":"true"},
        {"label":"검토 요청 대기", "value":f"{pending}건", "sub":"KD담당자 / 수입전담자 협업 진행 중", "icon":"✓", "tone":"cyan"},
    ])

    section_header("업무 흐름", "신고자료 등록부터 관세사 최종 확인까지의 사전검토 단계")
    workflow_panel()

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
        section_header("오늘의 우선 검토 작업", "오분류 가능성과 관세 차액을 기준으로 선별한 우선 확인 품목")
        with st.expander(f"우선 검토 대상 {len(urgent_items)}개 펼쳐보기", expanded=False):
            st.dataframe(pd.DataFrame(urgent_items), width="stretch", hide_index=True,
                         column_config={"관세차액": st.column_config.NumberColumn(format="$%.0f")})

    section_header("최근 사전확인 통관 신고서", "신고서별 HTS 오분류 위험도 및 예상 관세 차액")
    shipment_cards(shipments)

    section_header("신고서별 관세 비교", "현재 신고 관세와 사전검토 산출 관세의 차이를 비교합니다.")
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
    st.markdown('<div class="info-strip"><span>신고서 등록 → 품목 형식 확인 → 사전 분석 실행</span><span>CSV · 최대 20MB</span></div>', unsafe_allow_html=True)
    if can_perform(active_role(), "upload_shipment"):
        with st.expander("CSV 신고자료 업로드", expanded=True):
            st.caption("필수 열과 입력 형식이 포함된 예제 파일을 내려받아 내용을 바꿔 사용하세요.")
            if SAMPLE_SHIPMENT_FILE.exists():
                st.download_button(
                    "예제 CSV 다운로드",
                    SAMPLE_SHIPMENT_FILE.read_bytes(),
                    "선적자료_예제.csv",
                    "text/csv",
                    width="stretch",
                )
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
    else:
        st.info(f"{active_role()} 역할은 등록된 신고서를 조회할 수 있지만 CSV 신고자료를 등록할 수는 없습니다.")

    if not st.session_state.shipments:
        st.info("아직 등록된 신고서가 없습니다. 위에서 CSV를 업로드하세요.")
        return
    options = [s["entryNumber"] for s in st.session_state.shipments]
    current_index = options.index(st.session_state.selected_entry) if st.session_state.selected_entry in options else 0
    st.session_state.selected_entry = st.selectbox("신고서 선택", options, index=current_index)
    shipment = selected_shipment()
    if shipment is None:
        empty_state()
        return
    total = shipment_totals(shipment)
    kpi_grid([
        {"label":"등록 품목", "value":f"{len(shipment['items'])}개", "sub":shipment["entryNumber"], "icon":"▤"},
        {"label":"총 신고가액", "value":currency(total["value"]), "sub":shipment["importerOfRecord"], "icon":"$", "tone":"cyan"},
        {"label":"예상 관세차액", "value":currency(total["gap"]), "sub":"신고 대비 검토 관세 차이", "icon":"△", "tone":"warn", "emphasis":"true"},
        {"label":"현재 위험도", "value":shipment["riskLevel"], "sub":shipment["status"], "icon":"!", "tone":"rose"},
    ])
    st.markdown(
        f'<div class="info-strip"><span><strong>{escape(shipment["shipmentTitle"])}</strong> · {escape(shipment["importerOfRecord"])}</span><span>{escape(shipment["portOfEntry"])}</span></div>',
        unsafe_allow_html=True,
    )
    section_header("품목별 HTS 검토표", "품명·품목번호·관세율·PSC 후보를 검색하고 내려받을 수 있습니다.")
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
    if can_perform(active_role(), "download_reports"):
        download_left, download_right = st.columns(2)
        download_left.download_button("품목 검토표 CSV", item_frame.to_csv(index=False).encode("utf-8-sig"), f"{shipment['entryNumber']}_items.csv", "text/csv", width="stretch")
        download_right.download_button("사전검토 보고서", analysis_brief(shipment).encode("utf-8"), f"{shipment['entryNumber']}_brief.md", "text/markdown", width="stretch")


def run_analysis(shipment: dict[str, Any], threshold: int) -> None:
    items = shipment["items"]
    for item in items:
        item.update(
            evaluate_item(
                item,
                shipment,
                official_hts_index,
                threshold,
                str(official_data.get("dataset", {}).get("currentVersion", "공식 HTS 판본")),
            )
        )
    review_items = [i for i in items if i.get("riskLevel") in {"보통", "높음", "매우 높음"}]
    risk_rank = {"낮음": 0, "보통": 1, "높음": 2, "매우 높음": 3}
    shipment["riskLevel"] = max(
        (str(i.get("riskLevel", "낮음")) for i in items),
        key=lambda value: risk_rank.get(value, 0),
        default="낮음",
    )
    shipment["status"] = "검토 필요" if review_items else "자동검증 완료"
    scores = [float(i.get("confidenceScore", 0)) for i in items if float(i.get("confidenceScore", 0)) > 0]
    st.session_state.analysis_runs.insert(0, {
        "실행시각": datetime.now().strftime("%Y-%m-%d %H:%M"), "신고번호": shipment["entryNumber"],
        "품목 수": len(items), "검토 필요": len(review_items), "PSC 후보": sum(bool(i.get("pscRequired")) for i in items),
        "평균 신뢰도": round(sum(scores) / len(scores), 1) if scores else 0,
        "예상 관세차액": shipment_totals(shipment)["gap"],
    })
    record_audit("사전 분석", shipment["entryNumber"], f"검토 필요 {len(review_items)}개")


def page_analysis() -> None:
    hero("사전 분석 실행", "공식 HTS 판본으로 신고 코드와 기본세율을 검증하고 관세차액을 계산합니다.")
    st.markdown('<div class="info-strip"><span>관세차액 = 신고가액 × (검토세율 − 신고세율) ÷ 100</span><span>공식표 자동검증 + 담당자 확정</span></div>', unsafe_allow_html=True)
    if not st.session_state.shipments:
        empty_state("분석할 신고서가 없습니다.")
        return
    options = [s["entryNumber"] for s in st.session_state.shipments]
    entry = st.selectbox("분석할 신고서", options)
    threshold = st.slider("검토 신뢰도 기준", 50, 100, 85)
    shipment = next(s for s in st.session_state.shipments if s["entryNumber"] == entry)
    if can_perform(active_role(), "run_analysis") and st.button("사전 분석 실행", type="primary", width="stretch"):
        run_analysis(shipment, threshold)
        st.session_state.selected_entry = entry
        st.success("분석을 완료했습니다. 검토 대상과 관세차액을 확인해 주세요.")
    if st.session_state.analysis_runs:
        section_header("분석 이력", "최근 실행 순서로 신뢰도와 PSC 후보 결과를 표시합니다.")
        runs_frame = pd.DataFrame(st.session_state.analysis_runs)
        st.dataframe(runs_frame, width="stretch", hide_index=True)
        st.download_button("분석 이력 CSV", runs_frame.to_csv(index=False).encode("utf-8-sig"), "analysis_runs.csv", "text/csv")
    section_header("현재 품목 판정", "선택한 신고서의 품목별 사전검토 결과")
    st.dataframe(items_report_frame(shipment), width="stretch", hide_index=True)
    if can_perform(active_role(), "manual_classification"):
        with st.expander("담당자 판정 입력·수정"):
            st.caption("미국 통관 담당자가 추천 HTS·총 검토세율·근거를 확정할 수 있습니다.")
            item_numbers = [str(item["itemNumber"]) for item in shipment["items"]]
            target_number = st.selectbox("판정할 품목", item_numbers, key=f"manual_item_{entry}")
            target_item = next(item for item in shipment["items"] if str(item["itemNumber"]) == target_number)
            manual = target_item.get("manualDecision") or {}
            safe_key = f"{entry}_{target_number}".replace(" ", "_")
            with st.form(f"manual_decision_{safe_key}"):
                reviewer = st.text_input("판정 담당자", value=str(manual.get("reviewer", "")), key=f"reviewer_{safe_key}")
                recommended_code = st.text_input(
                    "추천 HTS",
                    value=str(manual.get("recommendedHtsCode", target_item.get("recommendedHtsCode") or target_item.get("declaredHtsCode", ""))),
                    key=f"recommended_{safe_key}",
                )
                reviewed_rate = st.number_input(
                    "총 검토세율 (%)",
                    min_value=0.0,
                    max_value=500.0,
                    value=float(manual.get("dutyRateCalculated", target_item.get("dutyRateCalculated", target_item.get("dutyRateDeclared", 0))) or 0),
                    step=0.1,
                    key=f"rate_{safe_key}",
                )
                basis = st.text_area("판정 근거", value=str(manual.get("ruleCitation", "")), placeholder="예: CBP Ruling 번호, HTS 주석, 관세사 검토 의견", key=f"basis_{safe_key}")
                save_decision = st.form_submit_button("담당자 판정 저장", type="primary")
                clear_decision = st.form_submit_button("담당자 판정 삭제")
            if save_decision:
                if not reviewer.strip() or not recommended_code.strip() or not basis.strip():
                    st.error("판정 담당자, 추천 HTS, 판정 근거를 모두 입력해 주세요.")
                else:
                    target_item["manualDecision"] = {
                        "reviewer": reviewer.strip(),
                        "recommendedHtsCode": recommended_code.strip(),
                        "dutyRateCalculated": float(reviewed_rate),
                        "ruleCitation": basis.strip(),
                        "decidedAt": datetime.now().isoformat(timespec="minutes"),
                    }
                    run_analysis(shipment, threshold)
                    record_audit("담당자 판정", f"{entry}/{target_number}", reviewer.strip())
                    st.success("담당자 판정을 저장하고 관세차액·위험도·PSC 후보를 다시 계산했습니다.")
            elif clear_decision:
                target_item.pop("manualDecision", None)
                run_analysis(shipment, threshold)
                record_audit("담당자 판정 삭제", f"{entry}/{target_number}", "자동검증으로 복원")
                st.success("담당자 판정을 삭제하고 공식표 자동검증 결과로 복원했습니다.")
    else:
        st.info("추천 HTS와 총 검토세율의 담당자 확정은 미국 통관 역할에서만 입력할 수 있습니다.")


def page_impact() -> None:
    hero("관세 영향 시각화", "신고 관세와 검토 후 관세를 비교해 우선 검토 대상을 찾습니다.")
    if not st.session_state.shipments:
        empty_state("분석할 신고서가 없습니다.")
        return
    rows = []
    for shipment in st.session_state.shipments:
        total = shipment_totals(shipment)
        rows.append({"신고번호": shipment["entryNumber"], "신고 관세": total["declared_duty"], "검토 관세": total["calculated_duty"], "차액": total["gap"]})
    frame = pd.DataFrame(rows)
    total_declared = float(frame["신고 관세"].sum())
    total_reviewed = float(frame["검토 관세"].sum())
    total_gap = float(frame["차액"].sum())
    kpi_grid([
        {"label":"총 신고 관세", "value":currency(total_declared), "sub":"현재 신고 기준", "icon":"$"},
        {"label":"총 검토 관세", "value":currency(total_reviewed), "sub":"사전검토 산출 기준", "icon":"◇", "tone":"cyan"},
        {"label":"추가 관세 노출액", "value":currency(total_gap), "sub":"우선 검토 필요 금액", "icon":"△", "tone":"rose", "emphasis":"true"},
        {"label":"영향 신고서", "value":f"{int((frame['차액'] > 0).sum())}건", "sub":f"전체 {len(frame)}건 중 차액 발생", "icon":"!", "tone":"warn"},
    ])
    section_header("신고서별 관세 영향", "신고 관세와 검토 관세를 금액 기준으로 비교합니다.")
    st.dataframe(frame, width="stretch", hide_index=True, column_config={c: st.column_config.NumberColumn(format="$%.0f") for c in ["신고 관세", "검토 관세", "차액"]})
    long = frame.melt(id_vars="신고번호", value_vars=["신고 관세", "검토 관세"], var_name="구분", value_name="금액")
    st.bar_chart(long, x="신고번호", y="금액", color="구분", stack=False)


def page_reviews() -> None:
    hero("정정 검토 요청", "오분류 또는 관세차액이 있는 품목을 미국 통관 담당자와 검토합니다.")
    shipment = selected_shipment()
    if shipment is None:
        empty_state()
        return
    candidates = [i for i in shipment["items"] if i.get("pscRequired") or i.get("declaredHtsCode") != i.get("recommendedHtsCode")]
    st.markdown(
        f'<div class="info-strip"><span>활성 신고서 · <strong>{escape(shipment["entryNumber"])}</strong></span><span>검토 후보 {len(candidates)}개</span></div>',
        unsafe_allow_html=True,
    )
    if can_perform(active_role(), "create_review"):
        section_header("신규 검토 요청", "분류 근거 확인이 필요한 품목을 담당자에게 전달합니다.")
        if candidates:
            labels = [f"{i['itemNumber']} · {i['partNameKo'] or i['partNameEn']}" for i in candidates]
            selected = st.selectbox("검토 품목", labels)
            form_left, form_right = st.columns(2)
            owner = form_left.selectbox("담당자", ["미국 통관", "원산지 검토"])
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
    else:
        st.info(f"{active_role()} 역할은 기존 검토 요청을 확인하고 처리할 수 있으며 신규 요청 생성은 한국 수출 관리 역할에서 담당합니다.")
    if st.session_state.reviews:
        section_header("검토 요청 목록", "담당자별 처리 상태와 기한을 확인합니다.")
        review_frame = pd.DataFrame(st.session_state.reviews)
        status_filter = st.multiselect("상태 필터", ["대기", "검토 중", "승인", "반려", "PSC 완료"], default=[])
        visible_reviews = review_frame if not status_filter else review_frame[review_frame["상태"].isin(status_filter)]
        st.dataframe(visible_reviews, width="stretch", hide_index=True)
        st.download_button("검토 요청 목록 CSV", visible_reviews.to_csv(index=False).encode("utf-8-sig"), "review_requests.csv", "text/csv")
        if can_perform(active_role(), "update_review"):
            actionable_reviews = [review for review in st.session_state.reviews if review.get("담당자") == active_role()]
            if actionable_reviews:
                section_header("검토 상태 처리", "현재 역할에 배정된 요청의 상태와 검토 의견을 갱신합니다.")
                review_ids = [review["요청번호"] for review in actionable_reviews]
                target_id = st.selectbox("요청번호", review_ids)
                target_review = next(review for review in actionable_reviews if review["요청번호"] == target_id)
                status_options = ["대기", "검토 중", "승인", "반려"]
                if can_perform(active_role(), "complete_psc"):
                    status_options.append("PSC 완료")
                if target_review["상태"] not in status_options:
                    status_options.append(target_review["상태"])
                status = st.selectbox("변경 상태", status_options, index=status_options.index(target_review["상태"]))
                comment = st.text_area("검토 의견", value=target_review.get("검토의견", ""), key=f"comment-{target_id}")
                if st.button("상태 저장"):
                    target_review["상태"] = status
                    target_review["검토의견"] = comment
                    record_audit("검토 상태 변경", target_id, f"{active_role()} · {status}")
                    st.success("검토 상태를 저장했습니다.")
            else:
                st.info(f"현재 {active_role()} 역할에 배정된 검토 요청이 없습니다.")
        else:
            st.caption("한국 수출 관리 역할에서는 요청 진행상태를 조회만 할 수 있습니다.")


def page_official_data(official: dict[str, Any]) -> None:
    hero("공식 공지·HTS 변경자료", "Federal Register와 USITC 판본 비교 결과를 조회합니다.")
    dataset = official.get("dataset", {})
    kpi_grid([
        {"label":"이전 HTS 판본", "value":str(dataset.get("previousVersion", "-")), "sub":"비교 기준 판본", "icon":"◀"},
        {"label":"현재 HTS 판본", "value":str(dataset.get("currentVersion", "-")), "sub":"현재 적용 판본", "icon":"✓", "tone":"cyan"},
        {"label":"변경 항목", "value":f"{dataset.get('changeCount', 0)}건", "sub":"추가·수정·삭제 합계", "icon":"△", "tone":"warn"},
        {"label":"공식 출처 연결", "value":f"{len(official.get('sources', []))}개", "sub":"Federal Register · USITC", "icon":"↗", "tone":"cyan"},
    ])
    section_header("HTS 변경 항목", "품목번호와 영문 설명으로 공식 판본 변경 내역을 검색합니다.")
    changes = official.get("htsChanges", [])
    if changes:
        changes_frame = pd.DataFrame(changes)[["htsCode", "changeType", "descriptionEn", "generalRateBefore", "generalRateAfter"]]
        search = st.text_input("HTS·설명 검색", placeholder="예: 9903.94 또는 automobile parts")
        if search:
            mask = changes_frame.astype(str).apply(lambda column: column.str.contains(search, case=False, na=False)).any(axis=1)
            changes_frame = changes_frame[mask]
        st.dataframe(changes_frame, width="stretch", hide_index=True)
        st.download_button("HTS 변경자료 CSV", changes_frame.to_csv(index=False).encode("utf-8-sig"), "official_hts_changes.csv", "text/csv")
    section_header("공식 출처", "검토에 사용된 기관별 원문 자료")
    for source in official.get("sources", []):
        st.markdown(f"- [{source.get('publisher', source.get('id', '공식 자료'))}]({source.get('url', '#')})")


def local_conversation_response(question: str) -> str | None:
    normalized = question.strip().lower().rstrip(".!?~。！？")
    greetings = {"안녕", "안녕하세요", "반가워", "반갑습니다", "hello", "hi", "hey"}
    thanks = {"고마워", "고맙습니다", "감사", "감사합니다", "thank you", "thanks"}
    goodbyes = {"잘 가", "안녕히 가세요", "다음에 봐", "bye", "goodbye"}
    if normalized in greetings:
        return "안녕하세요! 무엇을 도와드릴까요?"
    if normalized in thanks:
        return "천만에요! 더 궁금한 점이 있으면 편하게 말씀해 주세요."
    if normalized in goodbyes:
        return "네, 다음에 또 뵐게요. 좋은 하루 보내세요!"
    return None


def build_ai_prompt(question: str, official: dict[str, Any]) -> str:
    shipment = selected_shipment()
    if shipment is None:
        empty_state()
        return
    context = {
        "selected_shipment": shipment,
        "official_dataset": official.get("dataset", {}),
        "official_sources": official.get("sources", []),
        "hts_changes": official.get("htsChanges", [])[:20],
    }
    return f"""당신은 자연스러운 한국어 대화가 가능한 실무 AI이며, 필요할 때 미국 수입통관과 한국산 KD 자동차 부품의 HTS 사전검토를 돕습니다.

응답 원칙:
- 먼저 사용자의 질문에 직접 답하세요. 질문을 임의로 물류나 관세 주제로 바꾸지 마세요.
- 인사, 감사, 가벼운 일상 대화에는 업무 용어를 억지로 붙이지 말고 자연스럽게 1~2문장으로 응답하세요.
- HTS, 관세, 신고, 품목분류, PSC 등 업무 질문일 때만 아래 업무 맥락을 활용하세요.
- 업무 질문에는 필요한 경우 '확인된 사실', '위험 또는 불확실성', '다음 조치'로 나누되, 짧은 질문에는 간단히 답해도 됩니다.
- 질문이 모호하거나 판단에 필요한 정보가 부족하면 추측 대신 가장 필요한 후속 질문 하나를 하세요.
- 법적 최종판단으로 단정하지 말고, 제공 자료 밖의 품목번호나 관세율을 만들어내지 마세요.

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
    st.markdown(
        f'<div class="info-strip"><span>현재 업무 맥락 · <strong>{escape(_ctx["entryNumber"]) if (_ctx := selected_shipment()) else "신고서 미등록"}</strong></span><span>공식자료 기반 응답</span></div>',
        unsafe_allow_html=True,
    )
    section_header("AI Copilot", "선택한 신고서의 HTS 분류, 관세 차액과 다음 조치를 질문하세요.")
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
                local_answer = local_conversation_response(question)
                if local_answer:
                    answer = local_answer
                else:
                    try:
                        client = genai.Client(api_key=api_key)
                        params: dict[str, Any] = {"model": model, "input": build_ai_prompt(question, official), "store": True}
                        if st.session_state.previous_interaction_id:
                            params["previous_interaction_id"] = st.session_state.previous_interaction_id
                        interaction = client.interactions.create(**params)
                        answer = interaction.output_text or "답변을 생성하지 못했습니다. 질문을 조금 더 구체적으로 말씀해 주세요."
                        st.session_state.previous_interaction_id = interaction.id
                    except Exception as exc:
                        answer = f"Gemini 연결에 실패했습니다. Streamlit Secrets의 API 키와 모델 접근 권한을 확인해 주세요.\n\n오류: {exc}"
                st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})


def page_settings(official: dict[str, Any], api_key: str, model: str) -> None:
    hero("운영 설정", "작업 데이터를 백업·복원하고 AI 및 공식자료 연결 상태를 확인합니다.")
    kpi_grid([
        {"label":"Gemini 연결", "value":"연결 준비" if api_key else "키 미설정", "sub":"서버 Secrets 보안 연결", "icon":"●", "tone":"cyan" if api_key else "warn"},
        {"label":"AI 모델", "value":model, "sub":"관세 도우미 응답 모델", "icon":"AI"},
        {"label":"공식자료", "value":f"{len(official.get('sources', []))}개", "sub":"연결된 공식 출처", "icon":"↗", "tone":"cyan"},
        {"label":"작업 세션", "value":f"{len(st.session_state.audit_log)}건", "sub":"현재 세션 감사 기록", "icon":"✓"},
    ])

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
official_hts_index = load_official_hts_index()
try:
    gemini_api_key = str(st.secrets.get("GEMINI_API_KEY", ""))
    gemini_model = str(st.secrets.get("GEMINI_MODEL", GEMINI_DEFAULT_MODEL))
except FileNotFoundError:
    gemini_api_key, gemini_model = "", GEMINI_DEFAULT_MODEL

if not st.session_state.get("role_authenticated", False):
    hero("업무 역할로 시작하기", "담당 업무를 선택하면 해당 역할에 필요한 메뉴와 기능만 표시됩니다.")
    st.markdown('<div class="info-strip"><span>역할별 업무 화면</span><span>버튼을 눌러 바로 시작</span></div>', unsafe_allow_html=True)
    role_columns = st.columns(3)
    role_details = {
        "한국 수출 관리": ("수출", "신고자료 등록, 자동분석 실행, 검토 요청 생성"),
        "미국 통관": ("통관", "추천 HTS·세율 확정, 검토 상태 및 PSC 처리"),
        "원산지 검토": ("원산지", "원산지 증빙 검토, 요청 승인·반려"),
    }
    for column, role_name in zip(role_columns, ROLES):
        short_name, description = role_details[role_name]
        with column:
            st.markdown(
                f'<div class="kpi-card"><div class="kpi-label">{escape(short_name)} 업무</div>'
                f'<div class="kpi-value" style="font-size:1.15rem">{escape(role_name)}</div>'
                f'<div class="kpi-sub">{escape(description)}</div></div>',
                unsafe_allow_html=True,
            )
            if st.button(f"{role_name} 시작", key=f"role_login_{role_name}", type="primary", width="stretch"):
                st.session_state.role = role_name
                st.session_state.role_authenticated = True
                st.session_state.pop("page_navigation", None)
                record_audit("역할 시작", role_name, ROLE_SUMMARIES[role_name])
                st.rerun()
    st.stop()

with st.sidebar:
    st.markdown(
        """
        <div class="brand-shell">
          <div class="brand-row">
            <div class="brand-mark">HG</div>
            <div><div class="brand-name">HYUNDAI GLOVIS</div><div class="brand-sub">미국 KD 세관 사전확인</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    role = active_role()
    st.markdown(
        f'<div class="side-context"><span>▣&nbsp;&nbsp;{escape(role)}</span><span>{escape(ROLE_SUMMARIES[role])}</span></div>',
        unsafe_allow_html=True,
    )
    entry_options = [shipment["entryNumber"] for shipment in st.session_state.shipments]
    entry_index = entry_options.index(st.session_state.selected_entry) if st.session_state.selected_entry in entry_options else 0
    st.session_state.selected_entry = st.selectbox("활성 신고서", entry_options, index=entry_index)
    page_options = list(pages_for_role(role))
    page_labels = {
        "대시보드":"▦　대시보드", "통관 신고서":"▤　통관 신고서 관리", "사전 분석":"⚡　사전 분석 실행",
        "관세 영향":"◒　관세 영향 시각화", "정정 검토":"✓　정정 검토 요청", "공식 자료":"↗　공지 / 공식 자료",
        "AI 도우미":"✦　AI 관세 도우미", "운영 설정":"⚙　운영 설정",
    }
    if st.session_state.get("page_navigation") not in page_options:
        st.session_state.page_navigation = page_options[0]
    page = st.radio("업무 메뉴", page_options, format_func=lambda value: page_labels[value], label_visibility="collapsed", key="page_navigation")
    st.divider()
    if gemini_api_key:
        st.markdown(
            f'<div class="system-box"><div class="system-line"><span>◆ Gemini AI</span><span class="system-chip">연결됨</span></div>'
            f'<div style="color:#64748b;font-size:.6rem;margin-top:.45rem">{escape(gemini_model)}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="system-box"><div class="system-line"><span>◆ Gemini AI</span><span class="system-chip" style="color:#fbbf24">키 미설정</span></div></div>', unsafe_allow_html=True)
    if st.button("역할 변경", width="stretch"):
        record_audit("역할 종료", role, "역할 선택 화면으로 이동")
        st.session_state.role_authenticated = False
        st.session_state.pop("page_navigation", None)
        st.rerun()

topbar(page, role, len(official_data.get("sources", [])))

if not can_access_page(role, page):
    st.error("현재 역할에서는 이 화면에 접근할 수 없습니다.")
    st.stop()

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

st.markdown(
    '<div class="app-footer">본 서비스는 사전검토 지원 도구이며 최종 품목분류·관세·신고 판단은 관세사 및 미국 통관 담당자의 확인이 필요합니다.</div>',
    unsafe_allow_html=True,
)
