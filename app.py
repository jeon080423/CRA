"""
수석 리서치 품질 검수관 - 보고서 분석기
Streamlit Cloud 배포용 메인 앱
"""
import streamlit as st
import concurrent.futures
import datetime
import config
from config import (
    APP_TITLE, APP_ICON, APP_DESCRIPTION,
    AVAILABLE_MODELS, DEFAULT_MODEL, MAX_TEXT_CHARS,
    MODEL_DISPLAY_NAMES, AUTO_MODE_LABEL, AUTO_MODEL_PRIORITY,
)
from file_processor import extract_text, truncate_text
from analyzer import (
    run_analysis_stream, run_analysis, _run_single,
    STEP_PROMPTS, STEP_LABELS,
    FULL_ANALYSIS_PROMPT, get_api_key, get_api_keys,
    run_step_with_chunks, check_key_quotas
)
from rfp_prompts import RFP_SECTIONS
import rfp_utils
import io
import pandas as pd
import numpy as np
from data_cleaner import DataImputer, WeightCalculator
import plotly.express as px
try:
    from docx import Document
    from docx.shared import Pt
except ImportError:
    Document = None

# ── 페이지 설정
st.set_page_config(
    page_title="보고서 검수 AI Tools",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Google Fonts (style 블록과 반드시 분리)
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ── Qualtrics SaaS 스타일 CSS
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
[data-testid="stAppViewContainer"] { background-color: #F4F6F9; }
[data-testid="block-container"] { padding-top: 0 !important; }

[data-testid="stSidebar"] { background-color: #1B2437; border-right: none; }
[data-testid="stSidebar"] * { color: #C8D0DC !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid #374151 !important;
    color: #9CA3AF !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    padding: 0.4rem 1rem !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    border-color: #6B7280 !important;
    color: #D1D5DB !important;
    background: #1F2A3D !important;
}
[data-testid="stSidebar"] hr { border-color: #2D3A50 !important; }
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] [data-baseweb="select"] *,
[data-testid="stSidebar"] [data-baseweb="input"] *,
[data-testid="stSidebar"] [class*="st-"] { color: #FFFFFF !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div { background-color: #243048 !important; border-color: #374151 !important; }

/* 네비게이션 라디오 버튼 텍스트 크기 및 줄바꿈 방지 */
[data-testid="stSidebar"] .stRadio div[data-testid="stMarkdownContainer"] p {
    font-size: 0.82rem !important;
    white-space: nowrap !important;
    overflow: hidden;
    text-overflow: ellipsis;
}


.qx-topbar {
    background: #FFFFFF;
    border-bottom: 1px solid #E5E9F0;
    padding: 0.9rem 2rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.qx-topbar-logo { font-size: 1.35rem; font-weight: 700; color: #0F6CBD; letter-spacing: -0.5px; }
.qx-topbar-sep  { width: 1px; height: 22px; background: #D1D9E6; margin: 0 0.5rem; }
.qx-topbar-title { font-size: 0.88rem; font-weight: 500; color: #4A5568; }
.qx-topbar-badge {
    margin-left: auto;
    background: #EEF4FD; color: #0F6CBD;
    border: 1px solid #BDD7F5; border-radius: 20px;
    padding: 2px 12px; font-size: 0.75rem; font-weight: 600;
}

.qx-section-label {
    font-size: 0.72rem; font-weight: 600;
    letter-spacing: 0.8px; text-transform: uppercase;
    color: #8B96A9; margin-bottom: 0.5rem;
}

.qx-card {
    background: #FFFFFF;
    border: 1px solid #E5E9F0;
    border-radius: 10px;
    padding: 1.5rem 1.75rem;
    box-shadow: 0 1px 4px rgba(15,107,189,0.05);
    margin-bottom: 1rem;
}
.qx-card-title { font-size: 0.95rem; font-weight: 600; color: #1A2237; margin-bottom: 0.3rem; }

.qx-upload-zone {
    background: #FAFBFE;
    border: 2px dashed #C5D5EE;
    border-radius: 10px;
    padding: 2.5rem 1.5rem;
    text-align: center;
    transition: border-color 0.25s, background 0.25s;
}
.qx-upload-zone:hover { border-color: #0F6CBD; background: #EEF4FD; }
.qx-upload-icon  { font-size: 2.2rem; margin-bottom: 0.5rem; }
.qx-upload-text  { font-size: 0.9rem; font-weight: 500; color: #3D4F6B; }
.qx-upload-hint  { font-size: 0.78rem; color: #A0AABB; margin-top: 0.3rem; }

[data-baseweb="tab-list"] {
    background: #FFFFFF !important;
    border-bottom: 2px solid #E5E9F0 !important;
    border-radius: 0 !important;
    padding: 0 !important; gap: 0 !important;
}
[data-baseweb="tab"] {
    font-size: 0.85rem !important; font-weight: 500 !important;
    color: #64748B !important; border-radius: 0 !important;
    padding: 0.7rem 1.25rem !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -2px !important;
}
[data-baseweb="tab"]:hover { color: #0F6CBD !important; background: #F0F7FF !important; }
[aria-selected="true"] {
    color: #0F6CBD !important;
    border-bottom: 2px solid #0F6CBD !important;
    background: transparent !important;
    font-weight: 600 !important;
}

.badge-ok    { background:#EEF4FD; color:#0F6CBD; border:1px solid #BDD7F5; border-radius:20px; padding:3px 11px; font-size:0.76rem; font-weight:600; }
.badge-warn  { background:#FFF8E6; color:#B45309; border:1px solid #FCD34D; border-radius:20px; padding:3px 11px; font-size:0.76rem; font-weight:600; }
.badge-error { background:#FEF2F2; color:#DC2626; border:1px solid #FCA5A5; border-radius:20px; padding:3px 11px; font-size:0.76rem; font-weight:600; }

.stButton > button {
    background: #0F6CBD !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 0.55rem 1.25rem !important;
    box-shadow: 0 1px 3px rgba(15,107,189,0.2) !important;
    transition: background 0.18s !important;
}
.stButton > button:hover { background: #0A5AA0 !important; }

[data-testid="stFileUploader"] {
    background: #FAFBFE;
    border: 1.5px dashed #C5D5EE;
    border-radius: 8px; padding: 0.5rem;
}

[data-testid="stDownloadButton"] > button {
    background: #FFFFFF !important;
    color: #0F6CBD !important;
    border: 1.5px solid #0F6CBD !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
[data-testid="stDownloadButton"] > button:hover { background: #EEF4FD !important; }

.sb-file-card {
    background: #1F2A3D;
    border: 1px solid #2D3A50;
    border-radius: 8px;
    padding: 0.85rem 1rem; margin-bottom: 0.75rem;
}
.sb-file-name { font-size: 0.82rem; font-weight: 600; color: #E2E8F0 !important; word-break: break-all; }
.sb-file-meta { font-size: 0.75rem; color: #8B96A9 !important; margin-top: 0.25rem; }

/* AI 모델 수동 선택 영역 강조 (회색톤으로 변경) */
.sb-highlight-container {
    background: #2D3A50 !important; /* 회색톤 배경 */
    border: 1px solid #4A5568 !important; /* 차분한 회색 테두리 */
    border-radius: 10px;
    padding: 1.2rem;
    margin-top: 0.8rem;
    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
}
.sb-model-badge {
    background: #4A5568; /* 회색톤 배지 */
    color: #FFFFFF !important;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    display: inline-block;
    letter-spacing: 0.5px;
}

hr { border-color: #E5E9F0 !important; margin: 1rem 0 !important; }
[data-testid="stAlert"] { border-radius: 8px !important; font-size: 0.875rem !important; }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* 표 내부 줄바꿈 허용 및 가독성 개선 */
table { width: 100% !important; border-collapse: collapse !important; }
th, td { 
    white-space: normal !important; 
    word-break: keep-all !important; 
    line-height: 1.6 !important; 
    padding: 10px 15px !important;
    vertical-align: top !important;
}
td br { content: ""; display: block; margin-bottom: 0.5rem; }

@media print {
    [data-testid="stSidebar"], .stButton, hr, .qx-topbar-badge, .badge-ok, .badge-warn { display: none !important; }
    [data-testid="block-container"] { padding: 0 !important; background-color: white !important; }
    .qx-card { border: none !important; box-shadow: none !important; padding: 0 !important; margin-bottom: 2rem !important; page-break-inside: avoid; }
    .qx-topbar { border-bottom: 2px solid #0F6CBD !important; }
    body { background-color: white !important; }
}
</style>
""", unsafe_allow_html=True)


# ── 세션 상태 초기화
def init_session():
    defaults = {
        "is_logged_in": False,
        "logged_in_user": "",
        "login_error": "",
        "report_text": "",
        "file_name": "",
        "file_pages": 0,
        "step_results": {1: "", 2: "", 3: ""},
        "full_result": "",
        "selected_model": DEFAULT_MODEL,
        "auto_mode": True,    # 자동 최적화 모드 기본값
        "menu_selection": "과업 내용 체크 리스트",
        "rfp_curr_text": "",
        "rfp_prev_text": "",
        "rfp_results": {},
        "rfp_project_name": "",
        "rfp_curr_name": "",
        "rfp_prev_name": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()


# ── 로그인 헬퍼
def get_allowed_users() -> list:
    try:
        users = st.secrets["ALLOWED_USERS"]
        if isinstance(users, str):
            return [u.strip() for u in users.split(",") if u.strip()]
        return [str(u).strip() for u in users if u]
    except Exception:
        return []


def do_login(username: str):
    allowed = get_allowed_users()
    uid = username.strip()
    if not uid:
        st.session_state["login_error"] = "아이디를 입력해 주세요."
    elif uid in allowed:
        st.session_state["is_logged_in"] = True
        st.session_state["logged_in_user"] = uid
        st.session_state["login_error"] = ""
    else:
        st.session_state["login_error"] = f"'{uid}'은(는) 등록되지 않은 아이디입니다."


def do_logout():
    st.session_state["is_logged_in"] = False
    st.session_state["logged_in_user"] = ""
    st.session_state["login_error"] = ""


def show_win_strategy_section():
    st.markdown("""
    <div class="qx-topbar">
        <span class="qx-topbar-logo">과업 내용 체크 리스트</span>
        <span class="qx-topbar-sep"></span>
        <span class="qx-topbar-title">RFP 심층 분석 솔루션</span>
        <span class="qx-topbar-badge">Winning RFP Analysis</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="qx-section-label">1. 금년도 RFP (필수)</div>', unsafe_allow_html=True)
        curr_file = st.file_uploader("올해 제안요청서", type=["pdf", "docx", "txt"], key="rfp_curr_up")
    with col2:
        st.markdown('<div class="qx-section-label">2. 직전 RFP (선택)</div>', unsafe_allow_html=True)
        prev_file = st.file_uploader("직전 회차 제안요청서", type=["pdf", "docx", "txt"], key="rfp_prev_up")

    # 텍스트 추출 가이드
    if curr_file and curr_file.name != st.session_state["rfp_curr_name"]:
        with st.spinner("금년도 RFP 분석 준비 중..."):
            text, _ = extract_text(curr_file)
            st.session_state["rfp_curr_text"] = text
            st.session_state["rfp_curr_name"] = curr_file.name
    
    if prev_file and prev_file.name != st.session_state["rfp_prev_name"]:
        with st.spinner("직전 RFP 분석 준비 중..."):
            text, _ = extract_text(prev_file)
            st.session_state["rfp_prev_text"] = text
            st.session_state["rfp_prev_name"] = prev_file.name

    st.markdown("<hr>", unsafe_allow_html=True)
    
    if st.button("🚀 RFP 심층 분석 시작", type="primary", use_container_width=True):
        if not st.session_state["rfp_curr_text"]:
            st.error("금년도 RFP 문서를 먼저 업로드해 주세요.")
        else:
            perform_rfp_analysis()

    # 결과 표시 영역
    if st.session_state["rfp_results"]:
        st.success(f"✅ **[{st.session_state['rfp_project_name']}]** 분석 완료")
        
        # 탭으로 결과 표시
        tab_names = [s["title"] for s in RFP_SECTIONS]
        tabs = st.tabs(tab_names)
        
        for i, sec in enumerate(RFP_SECTIONS):
            with tabs[i]:
                res = st.session_state["rfp_results"].get(sec["id"], "분석 결과가 없습니다.")
                st.markdown(res, unsafe_allow_html=True)
        
        # 워드 다운로드 (RFP용)
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("📝 RFP 분석 결과 워드 다운로드", use_container_width=True):
            rfp_md = f"# RFP 분석 보고서: {st.session_state['rfp_project_name']}\n\n"
            for sec in RFP_SECTIONS:
                rfp_md += f"## {sec['title']}\n\n{st.session_state['rfp_results'].get(sec['id'], '')}\n\n"
            
            docx_file = export_to_docx(rfp_md)
            st.download_button(
                label="📥 클릭하여 워드 파일 저장",
                data=docx_file,
                file_name=f"{st.session_state['rfp_project_name']}_RFP분석.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )


def perform_rfp_analysis():
    curr_text = st.session_state["rfp_curr_text"]
    prev_text = st.session_state["rfp_prev_text"]
    
    # 컨텍스트 구성
    user_content = f"[금년도 문서]\n{rfp_utils.get_balanced_context(curr_text, 25000)}\n\n[직전 회차 문서]\n{rfp_utils.get_balanced_context(prev_text, 10000) if prev_text else '없음'}"
    
    # 사업명 감지
    project_name = rfp_utils.detect_project_name(curr_text)
    st.session_state["rfp_project_name"] = project_name
    
    progress_bar = st.progress(0, text="RFP 심층 분석 시작...")
    status_text = st.empty()
    
    total = len(RFP_SECTIONS)
    for i, sec in enumerate(RFP_SECTIONS):
        status_text.info(f"⏳ **{sec['title']}** 분석 중... ({i+1}/{total})")
        
        # analyzer의 run_analysis 활용
        result, err = run_analysis(
            sec["prompt"], 
            user_content, # report_text 인자로 보내야 프롬프트의 {report_text}가 치환됨
            model_name=st.session_state["selected_model"],
            auto_mode=st.session_state["auto_mode"]
        )
        
        if err:
            st.error(f"Error in {sec['title']}: {err}")
            st.session_state["rfp_results"][sec["id"]] = f"⚠️ 분석 실패: {err}"
        else:
            import re
            # 후처리: 모든 세미콜론(; , ；) 뒤의 공백을 포함하여 <br>로 변환 (줄바꿈 구현)
            processed_result = re.sub(r'[;；]\s*', '<br>', result)
            st.session_state["rfp_results"][sec["id"]] = processed_result
        
        progress_bar.progress((i + 1) / total)
    
    status_text.empty()
    progress_bar.empty()
    st.rerun()





def show_unit_nonresponse_system():
    """AI 단위 무응답 검토 및 가중치 조정(Weighting) 시스템 UI"""
    st.markdown("""
    <div class="qx-topbar">
        <span class="qx-topbar-logo">AI 단위 무응답 검토</span>
        <span class="qx-topbar-sep"></span>
        <span class="qx-topbar-title">표본 편향 교정 솔루션</span>
        <span class="qx-topbar-badge">Raking, Weighting</span>
    </div>
    """, unsafe_allow_html=True)

    # [v4.0 추가] 가이드
    with st.expander("📘 AI 단위 무응답(가중치) 검토 가이드", expanded=False):
        st.markdown("""
        ### 🛠️ AI 단위 무응답 교정 가이드
        1. **데이터 업로드:** 응답이 완료된 원본 설문 데이터를 업로드합니다.
        2. **변수 및 목표 설정:** 성별, 연령대 등 가중치 조정 기준 변수를 선택하고 모집단 분포(비율)를 입력합니다.
        3. **Raking 실행:** RIM Weighting 알고리즘을 통해 반복적으로 적정 가중치를 산출합니다.
        4. **품질 검정:** 가중치 분포와 설계효과(Deff)를 확인하여 표본의 대표성을 검토합니다.
        """)

    # 빈 상태 안내
    st.markdown('<div class="qx-section-label">1. 데이터 업로드 (Survey Data)</div>', unsafe_allow_html=True)
    df_file = st.file_uploader("가중치 조정을 수행할 데이터를 업로드하세요", type=["xlsx", "csv"], label_visibility="collapsed", key="uploader_unit")

    if not df_file:
        st.markdown("""
<div class="qx-card" style="text-align:center; padding:3.5rem 2rem; margin-top: 1rem;">
    <div style="font-size:3rem; margin-bottom:1rem;">⚖️</div>
    <div style="font-size:1.1rem; font-weight:600; color:#1A2237; margin-bottom:0.5rem;">
        무응답 교정을 위한 데이터를 업로드하세요
    </div>
    <div style="font-size:0.87rem; color:#8B96A9; margin-bottom:2rem;">
        응답 표본과 모집단 간의 차이를 분석하고 통계적 가중치(Weighting)를 부여합니다.
    </div>
    <div style="display:flex; justify-content:center; gap:1.5rem; flex-wrap:wrap;">
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">📊</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">편향 진단</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">🔢</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">Raking 보정</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">📉</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">Deff 평가</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
        return

    # 데이터 로드
    try:
        df = pd.read_csv(df_file) if df_file.name.endswith(".csv") else pd.read_excel(df_file)
        st.success(f"데이터 로드 완료: {len(df)} 행")
    except Exception as e:
        st.error(f"로드 중 오류: {e}")
        return

    # 변수 선택
    st.markdown('<div class="qx-section-label">2. 가중치 보정 변수 설정</div>', unsafe_allow_html=True)
    weight_vars = st.multiselect("가중치를 부여할 기준 변수를 선택하세요 (예: 성별, 연령)", options=df.columns.tolist())

    if not weight_vars:
        st.info("변수를 선택하면 모집단 비율 입력란이 나타납니다.")
        return

    # 목표 비율 입력
    targets = {}
    st.markdown("##### 📍 모집단 목표 분포 입력 (%)")
    for var in weight_vars:
        with st.expander(f"변수: {var}", expanded=True):
            unique_vals = df[var].dropna().unique().tolist()
            targets[var] = {}
            cols = st.columns(len(unique_vals))
            for i, val in enumerate(unique_vals):
                with cols[i]:
                    prop = st.number_input(f"{val} 비율", min_value=0.0, max_value=100.0, value=100.0/len(unique_vals), key=f"target_{var}_{val}")
                    targets[var][val] = prop / 100.0
            
            # 합계 체크
            total_p = sum(targets[var].values())
            if abs(total_p - 1.0) > 0.001:
                st.warning(f"합계가 {total_p*100:.1f}%입니다. 100%가 되도록 조정하세요.")

    # 실행
    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("🚀 가중치 산출(Raking) 실행", type="primary", use_container_width=True):
        calculator = WeightCalculator(df)
        with st.spinner("RIM Weighting 알고리즘 가동 중..."):
            iters, diff = calculator.apply_raking(targets)
            st.session_state["weighted_df"] = calculator.df
            st.session_state["weight_diag"] = calculator.get_diagnostics()
            st.success(f"가중치 산출 완료! (반복 횟수: {iters}, 최종 수렴 오차: {diff:.6f})")

    # 결과 표시
    if "weighted_df" in st.session_state:
        st.markdown('<div class="qx-section-label">3. 가중치 검정 및 다운로드</div>', unsafe_allow_html=True)
        diag = st.session_state["weight_diag"]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("가중치 범위", f"{diag['min']:.2f} ~ {diag['max']:.2f}")
        m2.metric("평균 가중치", f"{diag['mean']:.2f}")
        m3.metric("설계효과 (Deff)", f"{diag['deff']:.3f}")
        m4.metric("유효 표본 (ESS)", f"{int(diag['ess'])}명")

        # 가중치 분포 시각화
        fig = px.histogram(st.session_state["weighted_df"], x="weight", title="가중치 분포 히스토그램",
                          template="plotly_white", nbins=30)
        fig.update_traces(marker_color="#0F6CBD")
        st.plotly_chart(fig, use_container_width=True)

        # 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state["weighted_df"].to_excel(writer, index=False, sheet_name='WeightedData')
        output.seek(0)
        
        st.download_button("📥 가중치 포함 데이터 다운로드 (Excel)", data=output, 
                           file_name=f"가중치보정_{df_file.name}", use_container_width=True)


def show_outlier_inspection_system(mode="outlier"):
    """AI 이상치/결측치 검토 및 보완 시스템 UI"""
    st.markdown(f"""
    <div class="qx-topbar">
        <span class="qx-topbar-logo">AI {'이상치' if mode == 'outlier' else '결측치'} 검토</span>
        <span class="qx-topbar-sep"></span>
        <span class="qx-topbar-title">데이터 품질 진단 솔루션</span>
        <span class="qx-topbar-badge">Call Back, {'Adjustment' if mode == 'outlier' else 'Imputation'}</span>
    </div>
    """, unsafe_allow_html=True)

    # [v3.5 추가] 이용자 가이드 (User Manual)
    with st.expander(f"📘 AI {'이상치' if mode == 'outlier' else '결측치'} 검토 이용 안내", expanded=False):
        if mode == "outlier":
            st.markdown("""
            ### 🛠️ AI 이상치 검토 가이드
            1. **데이터 업로드:** 검토할 Excel 또는 CSV 파일을 업로드합니다.
            2. **시각적 탐색:** '시각적 이상치 판별' 섹션에서 산점도와 바이올린 플롯을 통해 데이터 분포와 이상 의심 사례를 확인합니다.
            3. **변수 선택:** 분석이 필요한 수치형/범주형 변수를 선택합니다.
            4. **AI 추천 및 설정:** 'AI 추천' 버튼을 클릭하여 적절한 보완 방법을 확인하거나 직접 선택합니다.
            5. **실행 및 다운로드:** 보완된 데이터와 감사 보고서(Audit Log)를 엑셀로 저장합니다.
            """)
        else:
            st.markdown("""
            ### 🛠️ AI 결측치 검토 가이드
            1. **패턴 분석:** 데이터 로드 후 상단의 '결측 패턴 분석'을 통해 어떤 변수가 얼마나 비어있는지 확인합니다.
            2. **AI 진단:** 무작위성 여부(MCAR/MAR/MNAR)를 진단받아 통계적 편향 위험을 파악합니다.
            3. **보완 전략 수립:** 중요한 변수는 'MICE'나 'k-NN'으로, 보완이 불가능한 건은 '재확인(Call-back)'으로 설정합니다.
            4. **조사 가이드 활용:** 재확인 대상에 대해 AI가 생성해주는 전화 조사 스크립트를 활용합니다.
            """)

    # [v3.6 추가] 주요 기능 요약 카드 (메인 화면 스타일)
    st.markdown('<div class="qx-section-label">SYSTEM FEATURES</div>', unsafe_allow_html=True)
    if mode == "outlier":
        st.markdown("""
<div class="qx-card" style="padding:1.25rem 1.5rem; margin-bottom:1.5rem;">
    <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:1.5rem;">
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">01</span><span>데이터 분포 시각화 (Plotly)</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">02</span><span>통계적 이상치 정밀 탐지</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">03</span><span>AI 최적 보완 및 결과 리포트</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="qx-card" style="padding:1.25rem 1.5rem; margin-bottom:1.5rem;">
    <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:1.5rem;">
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">01</span><span>결측 패턴 및 AI 유형 진단</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">02</span><span>고급 통계 보완 (MICE/k-NN)</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">03</span><span>재확인(Call-back) 대상 관리</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    # 1. 파일 업로드
    st.markdown('<div class="qx-section-label">1. 데이터 업로드 (Excel/CSV)</div>', unsafe_allow_html=True)
    df_file = st.file_uploader(f"검토할 데이터를 업로드하세요 ({mode})", type=["xlsx", "csv"], label_visibility="collapsed", key=f"uploader_{mode}")

    if not df_file:
        if mode == "outlier":
            st.markdown("""
<div class="qx-card" style="text-align:center; padding:3.5rem 2rem; margin-top: 1rem;">
    <div style="font-size:3rem; margin-bottom:1rem;">📈</div>
    <div style="font-size:1.1rem; font-weight:600; color:#1A2237; margin-bottom:0.5rem;">
        검토할 데이터를 업로드하세요
    </div>
    <div style="font-size:0.87rem; color:#8B96A9; margin-bottom:2rem;">
        Excel 또는 CSV 데이터를 업로드하면 AI가 이상치 탐지 및 시각적 진단을 수행합니다.
    </div>
    <div style="display:flex; justify-content:center; gap:1.5rem; flex-wrap:wrap;">
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">📍</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">시각적 진단</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">📏</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">통계적 탐지</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">🧠</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">AI 보완 방법</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">📄</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">결과 리포트</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown("""
<div class="qx-card" style="text-align:center; padding:3.5rem 2rem; margin-top: 1rem;">
    <div style="font-size:3rem; margin-bottom:1rem;">📊</div>
    <div style="font-size:1.1rem; font-weight:600; color:#1A2237; margin-bottom:0.5rem;">
        분석할 데이터를 업로드하세요
    </div>
    <div style="font-size:0.87rem; color:#8B96A9; margin-bottom:2rem;">
        데이터를 업로드하면 AI가 결측 패턴을 분석하고 최적의 통계적 보완을 제안합니다.
    </div>
    <div style="display:flex; justify-content:center; gap:1.5rem; flex-wrap:wrap;">
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">🔍</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">패턴 분석</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">🧪</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">고급 보완(MICE)</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">🚨</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">재확인 관리</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">🎙️</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">조사 가이드</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
        return

    # 데이터 로드
    try:
        if df_file.name.endswith(".csv"):
            df = pd.read_csv(df_file)
        else:
            df = pd.read_excel(df_file)
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return

    st.success(f"데이터 로드 완료: {len(df)} 행, {len(df.columns)} 열")
    
    # [v3.5 추가] 시각적 이상치 판별 섹션
    if mode == "outlier":
        with st.expander("📈 시각적 이상치 판별 (Scatter & Violin)", expanded=False):
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) < 1:
                st.warning("시각화할 수 있는 수치형 변수가 없습니다.")
            else:
                viz_tab1, viz_tab2 = st.tabs(["📍 산점도 (Scatter Plot)", "🎻 바이올린 플롯 (Violin Plot)"])
                
                with viz_tab1:
                    st.markdown("##### 두 변수 간의 관계와 극단값 확인")
                    c1, c2, c3 = st.columns([2, 2, 1])
                    with c1:
                        x_axis = st.selectbox("X축 변수", options=numeric_cols, key="viz_x")
                    with c2:
                        y_axis = st.selectbox("Y축 변수", options=numeric_cols, index=min(1, len(numeric_cols)-1), key="viz_y")
                    with c3:
                        dot_color = st.color_picker("점 색상", "#0F6CBD", key="viz_color")
                    
                    fig_scatter = px.scatter(df, x=x_axis, y=y_axis, template="plotly_white", 
                                           title=f"{x_axis} vs {y_axis} 산점도")
                    fig_scatter.update_traces(marker=dict(color=dot_color, size=8, opacity=0.6))
                    st.plotly_chart(fig_scatter, use_container_width=True)
                
                with viz_tab2:
                    st.markdown("##### 데이터의 분포 밀도와 이상치 범위 확인")
                    v_col = st.selectbox("분석할 변수", options=numeric_cols, key="viz_v")
                    fig_violin = px.violin(df, y=v_col, box=True, points="all", template="plotly_white",
                                         title=f"{v_col} 분포 분석 (Violin & Box)")
                    fig_violin.update_traces(fillcolor="#0F6CBD", opacity=0.6, line=dict(color="black"))
                    st.plotly_chart(fig_violin, use_container_width=True)
    
    # [v3.0 추가] 결측치 패턴 분석 섹션
    if mode == "imputation":
        with st.expander("📊 데이터 결측 패턴 분석 (v3.0)", expanded=False):
            missing_counts = df.isnull().sum()
            missing_df = pd.DataFrame({
                "변수명": missing_counts.index,
                "결측건수": missing_counts.values,
                "결측비율(%)": (missing_counts.values / len(df) * 100).round(1)
            })
            missing_df = missing_df[missing_df["결측건수"] > 0].sort_values("결측건수", ascending=False)
            
            if missing_df.empty:
                st.info("현재 결측치가 있는 변수가 없습니다. 데이터가 완벽합니다! ✨")
            else:
                col_m1, col_m2 = st.columns([1, 1])
                with col_m1:
                    st.markdown("### 🔍 주요 결측 변수")
                    st.dataframe(missing_df, hide_index=True, use_container_width=True)
                with col_m2:
                    st.markdown("### 🤖 AI 결측 유형 진단")
                    if st.button("🧠 AI 패턴 진단 실행", key="diag_btn_ai"):
                        diag_prompt = f"다음 데이터의 결측 현황을 보고 MCAR(완전무작위), MAR(무작위), MNAR(비무작위) 중 어느 유형에 가까운지 진단하고 조치 전략을 추천해줘.\n{missing_df.to_string()}"
                        res, err = run_analysis("데이터 품질 전문가", diag_prompt, "결측 패턴 추론 중...")
                        if not err:
                            st.info(res)
                        else:
                            st.error(f"진단 오류: {err}")

    # 2. 변수 선택
    st.markdown('<div class="qx-section-label">2. 검토 대상 변수 선택</div>', unsafe_allow_html=True)
    target_cols = st.multiselect("이상치/결측치 검토가 필요한 변수를 선택하세요", options=df.columns.tolist(), key=f"targets_{mode}")

    if not target_cols:
        st.warning("분석할 변수를 최소 하나 이상 선택해 주세요.")
        return

    # 3. 변수별 보완 설정
    st.markdown('<div class="qx-section-label">3. 변수별 보완 방법 설정</div>', unsafe_allow_html=True)
    
    impute_configs = {}
    
    for col in target_cols:
        with st.expander(f"📍 변수: {col}", expanded=True):
            col_a, col_b = st.columns([2, 1])
            
            with col_b:
                if st.button(f"🪄 AI 추천", key=f"ai_rec_{mode}_{col}"):
                    # AI 추천 로직 (analyzer 활용)
                    prompt = f"다음 변수의 데이터 대체 방법을 추천하고 이유를 설명해줘. 변수명: {col}, 데이터 타입: {df[col].dtype}, 샘플 데이터: {df[col].dropna().head(5).tolist()}"
                    res, err = run_analysis("데이터 분석 전문가", prompt, "샘플 데이터 분석 중...")
                    if not err:
                        st.session_state[f"rec_{mode}_{col}"] = res
                    else:
                        st.session_state[f"rec_{mode}_{col}"] = f"AI 추천 생성 중 오류: {err}"
                
                if f"rec_{mode}_{col}" in st.session_state:
                    st.caption(st.session_state[f"rec_{mode}_{col}"])

            with col_a:
                methods = ["전체 평균 대체", "중앙값 대체", "최빈값 대체", "층별 평균 대체", "MICE 다중 대체", "k-NN 대체", "재확인(Call Back)", "직접 입력"]
                selected_method = st.selectbox(f"보완 방법 선택 ({col})", options=methods, key=f"method_{mode}_{col}")
                
                options = {}
                if selected_method == "층별 평균 대체":
                    strata = st.multiselect(f"층(Strata) 변수 선택 ({col})", options=[c for c in df.columns if c != col], key=f"strata_{mode}_{col}")
                    options["strata"] = strata
                elif selected_method == "k-NN 대체":
                    k_val = st.slider(f"k값 설정 ({col})", 1, 10, 5, key=f"k_{mode}_{col}")
                    options["k"] = k_val
                elif selected_method == "재확인(Call Back)":
                    st.warning("⚠️ 이 데이터는 보완하지 않고 '재조사 명단'에 포함합니다.")
                
                impute_configs[col] = {"method": selected_method, "options": options}

    # 4. 실행 버튼
    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("🚀 데이터 보완 실행", type="primary", use_container_width=True, key=f"run_btn_{mode}"):
        imputer = DataImputer(df)
        
        with st.spinner("통계적 알고리즘 처리 중..."):
            for col, config in impute_configs.items():
                # 이상치/결측치 인덱스 추출
                if mode == "imputation":
                    missing_idx = df[df[col].isna()].index.tolist()
                else:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        m = df[col].mean()
                        s = df[col].std()
                        missing_idx = df[(df[col] < m - 3*s) | (df[col] > m + 3*s) | df[col].isna()].index.tolist()
                    else:
                        missing_idx = df[df[col].isna()].index.tolist()
                
                if not missing_idx:
                    continue
                
                method = config["method"]
                opts = config["options"]
                
                if method == "전체 평균 대체":
                    imputer.impute_grand_mean(col, missing_idx)
                elif method == "중앙값 대체":
                    imputer.impute_median(col, missing_idx)
                elif method == "최빈값 대체":
                    imputer.impute_mode(col, missing_idx)
                elif method == "층별 평균 대체" and opts.get("strata"):
                    imputer.impute_stratified_mean(col, missing_idx, opts["strata"])
                elif method == "k-NN 대체":
                    imputer.impute_knn(col, missing_idx, k=opts.get("k", 5))
                elif method == "MICE 다중 대체":
                    imputer.impute_mice(col, missing_idx)
                elif method == "재확인(Call Back)":
                    imputer._apply_imputation(col, missing_idx, "CALL_BACK", "재확인 대상분류")
                else:
                    imputer.impute_grand_mean(col, missing_idx)
            
            st.session_state[f"imputed_df_{mode}"] = imputer.df
            st.session_state[f"impute_summary_{mode}"] = imputer.get_summary()
            st.session_state[f"impute_log_{mode}"] = imputer.audit_log
            
        st.success("데이터 보완 처리가 완료되었습니다!")

    # 5. 결과 확인 및 다운로드
    if f"imputed_df_{mode}" in st.session_state:
        st.markdown('<div class="qx-section-label">4. 결과 요약 및 다운로드</div>', unsafe_allow_html=True)
        
        summary = st.session_state[f"impute_summary_{mode}"]
        if isinstance(summary, dict) and summary:
            cols_metric = st.columns(len(summary))
            for i, (col_name, count) in enumerate(summary.items()):
                cols_metric[i].metric(col_name, f"{count}건 보완")
        
        orig_df = df.copy()
        adj_df = st.session_state[f"imputed_df_{mode}"]
        log_list = st.session_state[f"impute_log_{mode}"]
        log_df = pd.DataFrame(log_list)

        # 결과 엑셀용 DF 구성
        export_df = orig_df.copy()
        for col in target_cols:
            export_df[f"{col}_보완"] = adj_df[col]
            method_map = {row['인덱스']: row['적용방법'] for row in log_list if row['변수명'] == col}
            export_df[f"{col}_보완방법"] = export_df.index.map(lambda x: method_map.get(x, ""))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Result')
            if not log_df.empty:
                log_df.to_excel(writer, index=False, sheet_name='AuditLog')
        output.seek(0)
        
        st.download_button(
            "📥 보완 데이터 다운로드 (Excel)",
            data=output,
            file_name=f"보완완료_{df_file.name}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_btn_{mode}"
        )
        
        with st.expander("📝 상세 보완 내역 (Log)", expanded=True):
            st.dataframe(log_df, use_container_width=True)
            
        # [v3.0 추가] 재확인(Call-back) 대상 명단 별도 표시
        callback_df = log_df[log_df["적용방법"] == "재확인 대상분류"]
        if not callback_df.empty:
            st.markdown('<div class="qx-section-label" style="color:#d32f2f;">🚨 재조사(Call-back) 필요 명단</div>', unsafe_allow_html=True)
            st.error(f"총 {len(callback_df)}건의 데이터가 재확인 대상으로 분류되었습니다. 아래 명단을 조사원에게 전달하세요.")
            
            # 조사 가이드 생성 (AI가 각 변수별로 생성)
            target_callback_vars = callback_df["변수명"].unique().tolist()
            if st.button("🎙️ AI 재조사 질문 가이드 생성", key="btn_callback_guide"):
                guide_prompt = f"다음 변수들에 대해 전화 재조사를 실시할 때, 응답자에게 자연스럽게 물어볼 수 있는 질문 스크립트를 작성해줘.\n변수: {', '.join(target_callback_vars)}"
                res, err = run_analysis("전화조사 슈퍼바이저", guide_prompt, "스크립트 작성 중...")
                if not err:
                    st.info(res)
            
            st.dataframe(callback_df, use_container_width=True, hide_index=True)


# ── 사이드바
with st.sidebar:
    # 로고 추가 (가운데 정렬)
    try:
        _, mid_col, _ = st.columns([1, 3, 1])
        with mid_col:
            st.image("logo.png", width=180)
    except:
        pass
    st.markdown("<h3 style='text-align: center; color: white;'>AI 과업 관리 솔루션</h3>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # 내비게이션
    st.markdown('<div class="qx-section-label">NAVIGATION</div>', unsafe_allow_html=True)
    menu_options = [
        "과업 내용 체크 리스트", 
        "AI 이상치 검토 (Call Back, Data Adjustment)", 
        "AI 결측치 검토 (Call Back, Imputation)",
        "AI 단위 무응답 검토",
        "보고서 검수 AI Tools"
    ]
    
    # 세션 상태에 저장된 메뉴가 옵션에 없으면 기본값(첫 번째) 사용
    try:
        current_idx = menu_options.index(st.session_state["menu_selection"])
    except (ValueError, KeyError):
        current_idx = 0

    menu = st.radio(
        "메뉴를 선택하세요",
        menu_options,
        index=current_idx,
        label_visibility="collapsed",
        key="nav_radio"
    )
    st.session_state["menu_selection"] = menu
    st.markdown("<hr>", unsafe_allow_html=True)

    if not st.session_state["is_logged_in"]:
        st.markdown('<div class="qx-section-label">LOGIN</div>', unsafe_allow_html=True)
        login_id = st.text_input(
            "ID",
            placeholder="아이디를 입력하세요",
            label_visibility="collapsed",
            key="login_input",
        )
        if st.button("로그인", use_container_width=True, key="btn_login"):
            do_login(login_id)
            st.rerun()
        if st.session_state["login_error"]:
            st.error(st.session_state["login_error"], icon="⚠️")
        st.markdown("<hr>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="sb-file-card" style="margin-bottom:0.5rem;">'
            '<div class="sb-file-name">&#128100; ' + st.session_state["logged_in_user"] + '</div>'
            '<div class="sb-file-meta">로그인됨</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("로그아웃", use_container_width=True, key="btn_logout"):
            do_logout()
            st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)

    # API 키 상태
    _keys = get_api_keys()
    api_key = _keys[0] if _keys else None
    if _keys:
        st.success(f"API 키 {len(_keys)}개 연결됨", icon="✅")
        st.caption(f"요청마다 {len(_keys)}개 키 중 랜덤 선택")
    else:
        st.error("API 키 없음 — Streamlit Secrets에 GEMINI_API_KEYS를 추가하세요.", icon="⚠️")

    st.markdown("<hr>", unsafe_allow_html=True)
    
    # API 할당량 진단 (v2.9)
    st.markdown('<div class="qx-section-label">진단 도구</div>', unsafe_allow_html=True)
    if st.button("🔍 API 할당량 진단 시작", use_container_width=True, key="btn_diag"):
        with st.expander("진단 결과", expanded=True):
            diag_prog = st.progress(0, text="진단 대기 중...")
            diag_status = st.empty()
            
            def diag_callback(curr, total, msg):
                diag_prog.progress(curr/total, text=f"진단 중... ({curr}/{total})")
                diag_status.caption(msg)
                
            with st.spinner("모든 키와 모델 상태를 확인 중입니다..."):
                results = check_key_quotas(progress_callback=diag_callback)
                diag_prog.empty()
                diag_status.empty()
                
                if results:
                    import pandas as pd
                    df = pd.DataFrame(results)
                    st.dataframe(
                        df, 
                        hide_index=True,
                        column_config={
                            "상태": st.column_config.TextColumn("상태", width="medium"),
                            "상세 내용": st.column_config.TextColumn("상세 내용", width="large"),
                        },
                        use_container_width=True
                    )
                    
                    ok_count = sum(1 for r in results if "정상" in r["상태"])
                    
                    # INFO 행에서 발견된 모델 목록 추출 및 표시
                    info_row = next((r for r in results if r["순번"] == "INFO"), None)
                    if info_row:
                        st.info(f"🔍 **발견된 가용 모델 ID 목록:**\n\n`{info_row['상세 내용']}`")
                        # 분석에 사용 가능한 후보군만 따로 강조
                        candidates = [m for m in info_row['상세 내용'].split(", ") if "flash" in m or "pro" in m]
                        st.caption(f"이 중 분석 도구에서 활용 가능한 모델: {', '.join(candidates)}")

                    st.success(f"진단 완료: 총 {len(results)-1 if info_row else len(results)}개 조합 중 {ok_count}개 정상")

                    if ok_count == 0:
                        st.error("사용 가능한 키/모델 조합이 없습니다. API 키를 교체해 주세요.")
                else:
                    st.warning("진단할 API 키가 없습니다.")
    
    st.markdown("<hr>", unsafe_allow_html=True)

    # 모델 선택
    st.markdown('<div class="qx-section-label">AI 모델 설정</div>', unsafe_allow_html=True)
    auto_mode = st.toggle(
        "🤖 자동 최적화 (권장)",
        value=st.session_state["auto_mode"],
        help="할당량 초과 시 최적 모델로 자동 전환합니다. 우선순위: Gemini 2.5 Flash → 2.0 Flash → ...",
    )
    st.session_state["auto_mode"] = auto_mode

    if auto_mode:
        priority_names = " → ".join(
            MODEL_DISPLAY_NAMES.get(m, m).replace("Gemini ", "") for m in AUTO_MODEL_PRIORITY[:4]
        ) + " → ..."
        st.caption(f"우선순위: {priority_names}")
    else:
        # 수동 선택 영역을 테두리가 있는 컨테이너로 묶음
        with st.container(border=True):
            # 표시 이름 목록 생성
            display_options = [MODEL_DISPLAY_NAMES.get(m, m) for m in AVAILABLE_MODELS]
            display_default = MODEL_DISPLAY_NAMES.get(DEFAULT_MODEL, DEFAULT_MODEL)
            
            selected_display = st.selectbox(
                "모델을 직접 선택하세요",
                display_options,
                index=display_options.index(display_default),
                label_visibility="visible",
                key="sb_model_select"
            )
            
            # 표시 이름 → 실제 모델 ID 역매핑
            reverse_map = {v: k for k, v in MODEL_DISPLAY_NAMES.items()}
            selected_model = reverse_map.get(selected_display, DEFAULT_MODEL)
            st.session_state["selected_model"] = selected_model
            
            # 모델 ID 가시성 극대화 (회색톤 + 화이트 텍스트)
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; margin-top: 5px;">
                    <div style="
                        background: #4A5568; 
                        color: #FFFFFF; 
                        padding: 3px 10px; 
                        border-radius: 4px; 
                        font-family: 'Roboto Mono', monospace; 
                        font-size: 0.75rem;
                        font-weight: 700;
                    ">
                        {selected_model}
                    </div>
                    <span style="font-size: 0.7rem; color: #A0AABB;">Active ID</span>
                </div>
            """, unsafe_allow_html=True)


    st.markdown("<hr>", unsafe_allow_html=True)

    # 파일 현황
    st.markdown('<div class="qx-section-label">파일 업로드 현황</div>', unsafe_allow_html=True)
    if st.session_state["file_name"]:
        pages_info = f" · {st.session_state['file_pages']}p" if st.session_state["file_pages"] else ""
        st.markdown(
            '<div class="sb-file-card">'
            '<div class="sb-file-name">&#128196; ' + st.session_state["file_name"] + '</div>'
            '<div class="sb-file-meta">' + f"{len(st.session_state['report_text']):,}자{pages_info}" + '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        step_done = sum(1 for v in st.session_state["step_results"].values() if v)
        st.progress(step_done / 3, text=f"단계별 분석 {step_done}/3 완료")
    else:
        st.caption("파일을 업로드하면 현황이 표시됩니다.")

    st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("초기화", use_container_width=True):
        for k in ["report_text", "file_name", "full_result", "rfp_curr_text", "rfp_prev_text", "rfp_project_name"]:
            st.session_state[k] = ""
        st.session_state["step_results"] = {1: "", 2: "", 3: ""}
        st.session_state["rfp_results"] = {}
        st.session_state["file_pages"] = 0
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    st.caption("개발: ㅈㅅㅎ")
    st.caption("문의: shjeon1@metrix.co.kr")
    st.caption("Powered by Google Gemini · v2.9")



def export_to_docx(markdown_text: str) -> io.BytesIO:
    """마크다운-텍스트를 워드(DOCX) 파일로 변환 (표 객체 및 빨간색 강조 지원)"""
    if Document is None:
        return io.BytesIO(b"python-docx is not installed")
    
    doc = Document()
    style = doc.styles['Normal']
    style.font.size = Pt(11)
    
    from docx.shared import RGBColor
    import re
    
    lines = markdown_text.split('\n')
    table_buffer = []
    
    def flush_table():
        if not table_buffer:
            return
        # 컬럼 수 결정 (가장 긴 행 기준)
        max_cols = max(len(row) for row in table_buffer)
        if max_cols == 0:
            return
        
        table = doc.add_table(rows=0, cols=max_cols)
        table.style = 'Table Grid'
        
        for row_data in table_buffer:
            row_cells = table.add_row().cells
            for i, cell_text in enumerate(row_data):
                if i < max_cols:
                    # 셀 내부에도 빨간색 강조 적용 시도
                    p = row_cells[i].paragraphs[0]
                    # 셀 내부에도 볼드 및 빨간색 강조 적용
                    add_formatted_text(p, cell_text)
        table_buffer.clear()
        doc.add_paragraph() # 표 뒤에 공백 추가

    def add_formatted_text(paragraph, text):
        """정규표현식을 사용하여 마크다운 볼드(**), span 태그, blue 태그 처리"""
        import re
        # <br> 태그를 실제 줄바꿈으로 변환 (워드용)
        text = text.replace("<br>", "\n")
        
        # 1. 빨간색 강조(<span...>), 파란색 강조(<blue>), 볼드(**...**)를 식별하기 위한 정규식
        pattern = r"(<span style='color:red'>.*?</span>|<blue>.*?</blue>|\*\*.*?\*\*)"
        parts = re.split(pattern, text)
        
        for part in parts:
            if part.startswith("<span style='color:red'>"):
                inner = re.sub(r"<span style='color:red'>(.*?)</span>", r"\1", part)
                inner = inner.replace("**", "")
                run = paragraph.add_run(inner)
                run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
                run.bold = True
            elif part.startswith("<blue>"):
                inner = re.sub(r"<blue>(.*?)</blue>", r"\1", part)
                inner = inner.replace("**", "")
                run = paragraph.add_run(inner)
                run.font.color.rgb = RGBColor(0x00, 0x00, 0xFF)
                run.bold = True
            elif part.startswith("**") and part.endswith("**"):
                inner = part[2:-2]
                run = paragraph.add_run(inner)
                run.bold = True
            else:
                if part:
                    paragraph.add_run(part)

    for line in lines:
        line_strip = line.strip()
        
        # 표 행 감지 (| 로 시작하거나 포함된 경우)
        if '|' in line_strip:
            if re.match(r'^[|\s\-:]+$', line_strip):
                continue
            parts = [p.strip() for p in line_strip.split('|') if p.strip()]
            if parts:
                table_buffer.append(parts)
                continue
        
        if table_buffer:
            flush_table()
        
        if not line_strip:
            continue
        
        if line_strip.startswith('###'):
            doc.add_heading(line_strip.lstrip('#').strip(), level=3)
        elif line_strip.startswith('##'):
            doc.add_heading(line_strip.lstrip('#').strip(), level=2)
        elif line_strip.startswith('#'):
            doc.add_heading(line_strip.lstrip('#').strip(), level=1)
        else:
            is_bullet = line_strip.startswith('- ') or line_strip.startswith('* ')
            text_content = line_strip[2:] if is_bullet else line_strip
            
            if is_bullet:
                p = doc.add_paragraph(style='List Bullet')
            else:
                p = doc.add_paragraph()
            
            add_formatted_text(p, text_content)
    
    flush_table()
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


# ── 로그인 가드
if not st.session_state["is_logged_in"]:
    st.markdown("""
<div class="qx-topbar">
    <span class="qx-topbar-logo">보고서 검수 AI Tools</span>
    <span class="qx-topbar-sep"></span>
    <span class="qx-topbar-title">수석 리서치 품질 검수관</span>
</div>
""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
<div class="qx-card" style="max-width:480px; margin:0 auto; text-align:center; padding:3rem 2rem;">
    <div style="font-size:2.5rem; margin-bottom:1rem;">&#128272;</div>
    <div style="font-size:1.1rem; font-weight:600; color:#1A2237; margin-bottom:0.5rem;">로그인이 필요합니다</div>
    <div style="font-size:0.85rem; color:#8B96A9;">좌측 사이드바에서 아이디를 입력하고 로그인 버튼을 클릭하세요.</div>
</div>
""", unsafe_allow_html=True)

else:
    if st.session_state["menu_selection"] == "보고서 검수 AI Tools":
        # 상단 헤더 바
        st.markdown("""
    <div class="qx-topbar">
        <span class="qx-topbar-logo">보고서 검수 AI Tools</span>
        <span class="qx-topbar-sep"></span>
        <span class="qx-topbar-title">수석 리서치 품질 검수관</span>
        <span class="qx-topbar-badge">AI-Powered Quality Check</span>
    </div>
    """, unsafe_allow_html=True)
    elif st.session_state["menu_selection"] == "과업 내용 체크 리스트":
        show_win_strategy_section()
        # End Win Strategy here (early return or just wrap)
        st.stop()
    elif st.session_state["menu_selection"] == "AI 이상치 검토 (Call Back, Data Adjustment)":
        show_outlier_inspection_system(mode="outlier")
        st.stop()
    elif st.session_state["menu_selection"] == "AI 결측치 검토 (Call Back, Imputation)":
        show_outlier_inspection_system(mode="imputation")
        st.stop()
    elif st.session_state["menu_selection"] == "AI 단위 무응답 검토":
        show_unit_nonresponse_system()
        st.stop()

    # 파일 업로드 + 검수 항목
    col_up, col_items = st.columns([3, 2], gap="large")

    with col_up:
        st.markdown('<div class="qx-section-label">UPLOAD REPORT</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="qx-upload-zone">
    <div class="qx-upload-icon">&#128203;</div>
    <div class="qx-upload-text">PDF · DOCX · TXT 파일을 업로드하세요</div>
    <div class="qx-upload-hint">최대 50MB · PDF는 페이지 번호 자동 태그</div>
</div>
""", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "파일 선택",
            type=["pdf", "docx", "txt"],
            label_visibility="collapsed",
        )

    with col_items:
        st.markdown('<div class="qx-section-label">REVIEW ITEMS</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="qx-card" style="padding:1.25rem 1.5rem;">
    <div style="display:flex;flex-direction:column;gap:0.65rem;">
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">01</span><span>조사 설계 및 요약</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">02</span><span>부문별 정밀 검수 및 오류 식별</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">03</span><span>종합 검수 보고서</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    # 파일 처리
    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.get("file_name", ""):
            with st.spinner("파일 텍스트 추출 중..."):
                text, pages = extract_text(uploaded_file)
                if text:
                    truncated = truncate_text(text, MAX_TEXT_CHARS)
                    st.session_state["report_text"] = truncated
                    st.session_state["file_name"] = uploaded_file.name
                    st.session_state["file_pages"] = pages
                    st.session_state["step_results"] = {1: "", 2: "", 3: ""}
                    st.session_state["full_result"] = ""
                    if len(text) > MAX_TEXT_CHARS:
                        st.warning(
                            f"텍스트가 너무 깁니다 ({len(text):,}자). "
                            f"{MAX_TEXT_CHARS:,}자로 균형 있게 잘라 분석합니다."
                        )
                    else:
                        pages_str = f", {pages}페이지" if pages else ""
                        st.success(
                            f"파일 로드 완료 — **{uploaded_file.name}** ({len(text):,}자{pages_str})"
                        )
                else:
                    st.error("파일에서 텍스트를 추출할 수 없습니다.")

    # 분석 영역
    if st.session_state["report_text"]:
        st.markdown("<hr>", unsafe_allow_html=True)

        col_btn, col_hint = st.columns([1, 3])
        with col_btn:
            run_full = st.button("⚡ 전체 3단계 병렬 분석", use_container_width=True, type="primary")
        with col_hint:
            st.markdown(
                '<span style="font-size:0.82rem;color:#8B96A9;">'
                '1~3단계를 <b>동시에</b> 병렬 실행합니다. 순차 실행 대비 최대 3배 빠릅니다.'
                '</span>',
                unsafe_allow_html=True,
            )

        if run_full:
            api_key = get_api_key()
            if not api_key:
                st.error("API 키가 설정되지 않았습니다. Streamlit Secrets에 GEMINI_API_KEYS를 추가하세요.")
            else:
                _auto = st.session_state["auto_mode"]
                _model = st.session_state["selected_model"]
                st.session_state["full_result"] = ""
                st.session_state["step_results"] = {1: "", 2: "", 3: ""}

                progress_bar = st.progress(0, text="⚡ 3단계 병렬 분석 실시간 진행 중...")
                status_cols = st.columns(3)
                placeholders = {i+1: status_cols[i].empty() for i in range(3)}
                
                # 초기 상태 표시
                step_names = [
                    "조사 설계 및 요약", 
                    "부문별 정밀 검수 및 오류 식별", 
                    "종합 검수 보고서"
                ]
                for i, name in enumerate(step_names, 1):
                    placeholders[i].markdown(f"**[{i}단계]** {name}...")
                
                st.info("🚀 분석을 시작합니다. 잠시만 기다려 주세요 (약 2~3분 소요)")

                # 실시간 순차 처리 (안정성 및 사용자 피드백 최대화)
                # 데드락 방지를 위해 상위 레벨에서는 순차 실행, 내부(analyzer)에서는 청크별 병렬 실행
                from analyzer import run_step_with_chunks, STEP_PROMPTS
                from file_processor import slice_text_for_step
                from config import STEP_TEXT_RATIO
                
                log_area = st.empty()
                log_content = []
                timer_area = st.empty()
                start_time = datetime.datetime.now()

                def update_logs(msg):
                    import datetime
                    # KST (UTC+9) 설정
                    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
                    now = datetime.datetime.now(tz_kst).strftime("%H:%M:%S")
                    log_content.append(f"[{now}] {msg}")
                    # 서버 콘솔 로깅 (Streamlit Cloud Logs)
                    print(f"[UI LOG] [{now}] {msg}", flush=True)
                    # 최근 5개 로그만 표시
                    display_logs = "\n".join(log_content[-5:])
                    log_area.code(display_logs, language="text")
                    
                    # 타이머 업데이트
                    elapsed = datetime.datetime.now() - start_time
                    timer_area.info(f"⏱️ 분석 시작 후 **{elapsed.seconds}초** 경과 중... (엔진 정상 가동 중)")

                update_logs("🚀 전수 검수 시스템 가동 (병렬 가속 모드 v2.7)")
                
                completed_count = 0
                for s in range(1, 4):
                    update_logs(f"➡ {s}단계 분석 시작: {STEP_LABELS[s]}")
                    
                    # 개별 단계 내 청크 진행 상황을 표시하기 위한 콜백 함수
                    def make_callback(step_idx):
                        def callback(curr, total):
                            is_started = (curr < total)
                            sub_prog = curr / total
                            overall = (step_idx - 1) / 3 + (sub_prog / 3)
                            
                            status_msg = f"⏳ {step_idx}단계 분석 중... (조각 {curr+1 if is_started else curr}/{total})"
                            progress_bar.progress(min(overall, 0.99), text=status_msg)
                            
                            if is_started:
                                update_logs(f"ㄴ {step_idx}단계 조각 {curr+1}/{total} 분석 요청됨...")
                            else:
                                update_logs(f"✅ {step_idx}단계 모든 조각 분석 완료!")
                        return callback

                    # 개별 단계 실행 (v14.1: 3단계는 이전 결과물 요약 방식)
                    if s == 3:
                        # 1, 2단계 결과물 조합하여 3단계의 '분석 대상'으로 전달
                        input_text = f"--- [1단계 조사설계 요약] ---\n{st.session_state['step_results'][1]}\n\n"
                        input_text += f"--- [2단계 정밀검수 결과] ---\n{st.session_state['step_results'][2]}"
                        prompt_ready = STEP_PROMPTS[s]
                    else:
                        prompt_ready = STEP_PROMPTS[s]
                        input_text = slice_text_for_step(st.session_state["report_text"], s, STEP_TEXT_RATIO)

                    text, err = run_step_with_chunks(
                        s, 
                        input_text,
                        prompt_ready,
                        model_name=_model,
                        auto_mode=_auto,
                        progress_callback=make_callback(s)
                    )
                    
                    completed_count += 1
                    
                    if not text and err:
                        placeholders[s].error(f"❌ {s}단계 실패")
                        st.session_state["step_results"][s] = f"실패 사유: {err}"
                        update_logs(f"❌ {s}단계 분석 실패: {err}")
                    elif err:
                        # 일부 조각 실패 (부분 성공)
                        placeholders[s].warning(f"⚠️ {s}단계 부분 성공")
                        st.session_state["step_results"][s] = text
                        update_logs(f"⚠ {s}단계 일부 조각 누락됨 (분석은 계속 진행)")
                    else:
                        placeholders[s].success(f"✅ {s}단계 완료")
                        st.session_state["step_results"][s] = text
                        update_logs(f"✅ {s}단계 분석 성공")
                    
                    progress_bar.progress(completed_count / 3, text=f"⚡ {s}단계 완료! ({completed_count}/3 전체 진행)")

                # 결과 취합
                combined = ""
                for s in range(1, 4):
                    if st.session_state["step_results"][s]:
                        combined += f"\n\n---\n\n## {STEP_LABELS[s]}\n\n{st.session_state['step_results'][s]}"
                
                st.session_state["full_result"] = combined
                if combined:
                    st.success("⚡ 전체 병렬 분석이 완료되었습니다!")
                    st.rerun()
                else:
                    st.error("분석 결과 생성에 실패했습니다.")

        st.markdown("<hr>", unsafe_allow_html=True)

        # 단일 페이지 분석 UI (v16.0: 한 페이지에 모두 표시)
        for s in [1, 2, 3]:
            st.markdown(f'<div class="qx-section-label">{STEP_LABELS[s]}</div>', unsafe_allow_html=True)
            
            # 각 단계별 카드 섹션
            with st.container():
                col_hd, col_st = st.columns([3, 1])
                with col_hd:
                    st.markdown(f"### {STEP_LABELS[s]}")
                with col_st:
                    if st.session_state["step_results"][s]:
                        st.markdown('<span class="badge-ok">완료</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-warn">대기</span>', unsafe_allow_html=True)

                run_btn = st.button(
                    f"{s}단계 분석 실행",
                    key=f"btn_step_{s}",
                )
                
                result_area = st.empty()
                
                # 결과 표시
                if st.session_state["step_results"][s]:
                    result_area.markdown(st.session_state["step_results"][s], unsafe_allow_html=True)
                elif st.session_state["full_result"] and not st.session_state["step_results"][s]:
                    result_area.info(f"{s}단계의 통합 결과가 준비되어 있습니다.")

                if run_btn:
                    if not get_api_keys():
                        st.error("API 키가 설정되지 않았습니다.")
                    else:
                        _auto = st.session_state["auto_mode"]
                        _model = st.session_state["selected_model"]
                        with st.spinner(f"{s}단계 분석 중..."):
                            full_text = ""
                            # 스트리밍 방식 호출 (실시간 피드백)
                            for chunk, is_error, _ in run_analysis_stream(
                                STEP_PROMPTS[s],
                                st.session_state["report_text"],
                                model_name=_model,
                                auto_mode=_auto,
                            ):
                                if is_error:
                                    st.error(chunk)
                                    break
                                full_text += chunk
                                result_area.markdown(full_text + " ▌", unsafe_allow_html=True)
                            
                            if full_text:
                                result_area.markdown(full_text, unsafe_allow_html=True)
                                st.session_state["step_results"][s] = full_text
                                # 전체 결과 업데이트
                                combined = ""
                                for i in range(1, 4):
                                    if st.session_state["step_results"][i]:
                                        combined += f"\n\n---\n\n## {STEP_LABELS[i]}\n\n{st.session_state['step_results'][i]}"
                                st.session_state["full_result"] = combined
                                st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

        # 다운로드
        # 인쇄 버튼 (JS 기반)
        st.markdown("""
        <div class="no-print">
            <button onclick="window.print()" style="
                width: 100%;
                background-color: #0F6CBD;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0.75rem;
                font-size: 0.9rem;
                font-weight: 600;
                cursor: pointer;
                margin-top: 1rem;
                margin-bottom: 1.5rem;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            ">
                🖨️ 분석 결과 리포트 인쇄하기
            </button>
        </div>
        <style>
            @media print { .no-print { display: none !important; } }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="qx-section-label">DOWNLOAD RESULTS</div>', unsafe_allow_html=True)

        def build_full_report() -> str:
            fname = st.session_state.get("file_name", "보고서")
            parts = [f"# 수석 리서치 품질 검수 보고서\n\n**대상 파일:** {fname}\n\n---\n"]
            if st.session_state["full_result"]:
                parts.append("## 전체 3단계 종합 분석\n\n")
                parts.append(st.session_state["full_result"])
            else:
                for step in range(1, 4):
                    result = st.session_state["step_results"].get(step, "")
                    parts.append(f"\n\n## {STEP_LABELS[step]}\n\n")
                    parts.append(result if result else "*아직 분석이 실행되지 않았습니다.*")
            return "\n".join(parts)

        col_dl1, _ = st.columns([2, 2])
        report_md = build_full_report()
        base_name = st.session_state.get("file_name", "report").rsplit(".", 1)[0]

        with col_dl1:
            try:
                docx_file = export_to_docx(report_md)
                st.download_button(
                    label="📝 워드 파일로 다운로드 (.docx)",
                    data=docx_file,
                    file_name=f"{base_name}_검수보고서.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"워드 변환 중 오류 발생: {e}")

    else:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
<div class="qx-card" style="text-align:center; padding:3.5rem 2rem;">
    <div style="font-size:3rem; margin-bottom:1rem;">&#128203;</div>
    <div style="font-size:1.1rem; font-weight:600; color:#1A2237; margin-bottom:0.5rem;">
        보고서 파일을 업로드하세요
    </div>
    <div style="font-size:0.87rem; color:#8B96A9; margin-bottom:2rem;">
        PDF, DOCX, TXT 형식의 결과보고서를 업로드하면 AI가 4단계 전문 검수를 자동으로 수행합니다.
    </div>
    <div style="display:flex; justify-content:center; gap:1.5rem; flex-wrap:wrap;">
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">&#128203;</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">조사 설계 요약</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">&#128269;</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">부문별 정밀 검수</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">&#9888;&#65039;</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">5대 오류 기준 점검</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:1rem 1.5rem;min-width:130px;">
            <div style="font-size:1.4rem;">&#128196;</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.4rem;">종합 검수 보고서</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Last forced sync: 2026-02-22 07:10:00
