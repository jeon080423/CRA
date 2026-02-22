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
from data_cleaner import DataImputer, WeightCalculator, DataAugmentor
from codebook_utils import CodebookParser
import plotly.express as px
import api_utils
from usage_tracker import UsageTracker

# ── 이용 통계 트래커 초기화
tracker = UsageTracker()
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
        # [v4.12] 로그인 로그 기록
        tracker.log_event(uid, "LOGIN")
    else:
        st.session_state["login_error"] = f"'{uid}'은(는) 등록되지 않은 아이디입니다."


def do_logout():
    st.session_state["is_logged_in"] = False
    st.session_state["logged_in_user"] = ""
    st.session_state["login_error"] = ""


def show_data_roadmap(current_step=1):
    """데이터 처리 프로세스 로드맵 (시각적 도식)"""
    steps = [
        {"id": 1, "icon": "📝", "label": "RFP 분석/설계"},
        {"id": 2, "icon": "📥", "label": "데이터/코드북 업로드"},
        {"id": 3, "icon": "🔍", "label": "이상치/결측치 보정"},
        {"id": 4, "icon": "⚖️", "label": "단위무응답/가중치"},
        {"id": 5, "icon": "📊", "label": "최종 리포트 추출"}
    ]
    
    html = '<div style="display:flex; align-items:center; justify-content:space-between; margin: 1.5rem 0; padding:1rem; background:white; border-radius:12px; border:1px solid #E5E9F0;">'
    for i, s in enumerate(steps):
        is_active = s['id'] == current_step
        color = "#0F6CBD" if is_active else "#64748B"
        bg = "#EEF4FD" if is_active else "#F8FAFC"
        border = "2px solid #0F6CBD" if is_active else "1px solid #E2E8F0"
        
        html += f'''
        <div style="flex:1; display:flex; flex-direction:column; align-items:center; position:relative;">
            <div style="width:40px; height:40px; border-radius:50%; background:{bg}; border:{border}; display:flex; align-items:center; justify-content:center; font-size:1.2rem; margin-bottom:0.5rem; color:{color}; z-index:2;">
                {s['icon']}
            </div>
            <div style="font-size:0.7rem; font-weight:{'700' if is_active else '500'}; color:{color}; text-align:center;">{s['label']}</div>
        '''
        if i < len(steps) - 1:
            html += f'<div style="position:absolute; top:20px; left:calc(50% + 20px); width:calc(100% - 40px); height:2px; background:#E2E8F0; z-index:1;"></div>'
        html += '</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def show_security_notice():
    """데이터 보안 및 로컬 저장 안내 (v4.13)"""
    st.warning("""
    🛡️ **데이터 보안 안내:** 본 시스템은 사용자의 소중한 데이터 보안을 최우선으로 고려하며, 일체의 분석 결과를 서버에 저장하지 않습니다. 
    귀중한 분석 자료의 유실을 방지하기 위해 생성된 결과물은 반드시 개인 단말기에 실시간으로 다운로드하여 보관해 주시기 바랍니다.
    """)


def show_admin_dashboard():
    """관리자 전용 사용량 통계 대시보드"""
    st.markdown("""
    <div class="qx-topbar">
        <span class="qx-topbar-logo">ADMIN DASHBOARD</span>
        <span class="qx-topbar-sep"></span>
        <span class="qx-topbar-title">시스템 이용 통계 분석</span>
        <span class="qx-topbar-badge">Administrator Only</span>
    </div>
    """, unsafe_allow_html=True)

    df_login, df_section, df_all = tracker.get_summary_data()

    if df_login.empty and df_section.empty:
        st.info("📊 아직 수집된 이용 통계 데이터가 없습니다.")
        return

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="qx-section-label">📅 일별 로그인 추이 (최근 7일)</div>', unsafe_allow_html=True)
        if not df_login.empty:
            fig_login = px.line(df_login, x="date", y="count", markers=True, 
                                title="일별 로그인 수 상세", template="plotly_white")
            fig_login.update_traces(line_color="#0F6CBD")
            st.plotly_chart(fig_login, use_container_width=True)
        else:
            st.caption("로그인 데이터 없음")

    with col2:
        st.markdown('<div class="qx-section-label">🍕 당일 섹션별 사용 점유율</div>', unsafe_allow_html=True)
        if not df_section.empty:
            fig_section = px.pie(df_section, values="count", names="section_name", 
                                 title="오늘의 기능별 사용 비중", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_section, use_container_width=True)
        else:
            st.caption("오늘의 사용 데이터 없음")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="qx-section-label">📋 최근 시스템 접근 로그 (Last 100)</div>', unsafe_allow_html=True)
    st.dataframe(df_all, use_container_width=True, hide_index=True)

def show_win_strategy_section():
    st.markdown("""
    <div class="qx-topbar">
        <span class="qx-topbar-logo">과업 내용 체크 리스트</span>
        <span class="qx-topbar-sep"></span>
        <span class="qx-topbar-title">RFP 심층 분석 솔루션</span>
        <span class="qx-topbar-badge">Winning RFP Analysis</span>
    </div>
    """, unsafe_allow_html=True)

    # [v4.8] 도식 및 상세 안내
    with st.expander("📘 RFP 심층 분석 - 이용 방법 및 데이터 프로세스 가이드", expanded=False):
        st.markdown("### 🗺️ 데이터 처리 로드맵")
        show_data_roadmap(1)
        st.markdown("""
        ### 🛠️ 이용 단계 및 상세 가이드
        1. **RFP 업로드:** 금년도 공고된 제안요청서(RFP)를 업로드합니다. (PDF, Word, TXT 지원)
        2. **차이 분석 (선택):** 작년 도 RFP가 있다면 함께 업로드하여 가감된 과업을 자동으로 비교합니다.
        3. **항목별 정밀 진단:** 
           - **참가 자격:** 입찰 자격 제한 요소 및 필수 실적 요건 여부 판별
           - **과업 범위:** 제안서 작성 시 누락되어서는 안 될 핵심 요구사항 추출
           - **기술적 평가:** 정보보안, 개인정보 처리 등 기술 점수 감점 요인 점검
        4. **전략 리포트 추출:** 분석 결과를 엑셀 및 워드 리포트로 저장하여 제안서 기초 자료로 활용합니다.
        """)
    
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
        show_security_notice()
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

    # [v4.8 고도화] 실무용 이용 가이드
    with st.expander("📘 AI 단위 무응답(가중치) 검토 - 이용 방법 및 데이터 프로세스 가이드", expanded=False):
        st.markdown("### 🗺️ 데이터 처리 로드맵")
        show_data_roadmap(4)
        st.markdown("""
        ### 🛠️ 데이터 보정 및 가중치(Weighting) 단계
        1. **데이터 및 모집단 정보 입력:** 
           - 분석 대상 데이터와 변수 정의(코드북)를 업로드합니다.
           - 가중치 산출의 기준이 될 인구통계 변수(성별, 연령, 지역 등)를 선택합니다.
        2. **모집단 목표 분포 설정:** 선택한 각 계층별 모집단(Target) 비율(%)을 입력합니다. (합계 100% 필수)
        3. **데이터 증계 (Data Augmentation):** 
           - **세그먼트 타격:** 표본이 극히 부족하여 가중치만으로 보정이 어려운 특정 집단(예: 20대 남성)을 지정합니다.
           - **합성 데이터 생성:** Bootstrap 또는 Noise-added 기법을 통해 통계적 유의성을 가진 가상 표본을 생성하여 쿼터를 충족시킵니다.
        4. **가중치 산출(Raking):** RIM Weighting 알고리즘을 통해 다차원 주변 분포를 모집단 비율에 맞게 반복 보정합니다.
        5. **보정 품질 검정 (Diagnostics):** 
           - **Deff(설계효과):** 가중치 부여로 인한 분산 증가 정도를 확인합니다. (1.5 이하 권장)
           - **ESS(유효표본):** 가중치 적용 후 실제 분석에 유효한 정보량을 확인합니다.
        6. **통합 시트 다운로드:** 가중치 변수가 포함된 최종 분석용 데이터셋을 엑셀로 추출합니다.
        """)

    # [v4.1 고도화] 전문가용 가이드 (수식 포함)
    with st.expander("📘 AI 단위 무응답(가중치) 검토 - 통계적 모델 설계 및 수식 안내", expanded=False):
        st.markdown("""
        ### 🔍 통계적 가중치 조정(Weighting) 모델
        단위 무응답으로 인한 표본 편향을 교정하기 위해 본 시스템은 **RIM Weighting (Raking)** 알고리즘을 채택합니다.
        
        #### **1. Raking (Iterative Proportional Fitting) 알고리즘**
        여러 인구통계 변수(성별, 연령 등)의 분포를 모집단(Target) 분포에 맞추기 위해 가중치를 반복적으로 업데이트합니다.
        - **수렴 조건:** 모든 차원에서의 주변 분포(Marginal Distribution)오차가 설정된 허용 오차($\epsilon < 10^{-4}$) 이내일 때 종료됩니다.

        #### **2. 가중치 품질 평가지표 (Diagnostic Metrics)**
        가중치 부여는 추정치의 분산을 증가시킬 수 있으므로, **Kish의 설계효과(Design Effect, Deff)**를 통해 보정의 품질을 평가합니다.
        """)
        st.latex(r"Deff \approx 1 + L = \frac{n \sum_{i=1}^{n} w_i^2}{(\sum_{i=1}^{n} w_i)^2}")
        st.markdown(r"""
        - **유효 표본 크기 (Effective Sample Size, ESS):** 가중치 적용 후의 실제 정보량을 나타내며, $ESS = \frac{n}{Deff}$ 로 산출됩니다. 
        - **해석:** $Deff$ 가 1.5 이하일 경우 통계적으로 모델의 안정성이 높다고 판단하며, 2.0을 초과할 경우 특정 계층에 과도한 가중치가 부여되었음을 시사합니다.
        """)

    # 빈 상태 안내 (2컬럼 업로드 레이아웃)
    st.markdown('<div class="qx-section-label">1. 데이터 및 코드북 업로드 (Survey Data)</div>', unsafe_allow_html=True)
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        df_file = st.file_uploader("가중치 조정을 수행할 데이터 업로드", type=["xlsx", "csv"], key="uploader_unit")
    with col_u2:
        cb_file = st.file_uploader("코드북 업로드 (선택 사항)", type=["xlsx"], key="cb_unit")

    if not df_file:
        st.markdown("""
<div class="qx-card" style="text-align:center; padding:2rem 2rem 2.5rem 2rem; margin-top: 1rem; margin-bottom: 2rem; min-height: 320px;">
    <div style="font-size:3rem; margin-bottom:0.5rem;">⚖️</div>
    <div style="font-size:1.1rem; font-weight:600; color:#1A2237; margin-bottom:0.5rem;">
        무응답 교정을 위한 데이터를 업로드하세요
    </div>
    <div style="font-size:0.87rem; color:#8B96A9; margin-bottom:1.5rem;">
        응답 표본과 모집단 간의 차이를 분석하고 통계적 가중치(Weighting)를 부여합니다.
    </div>
    <div style="display:flex; justify-content:center; gap:1.5rem; flex-wrap:wrap;">
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:0.8rem 1.2rem;min-width:120px;">
            <div style="font-size:1.2rem;">📊</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.3rem;">편향 진단</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:0.8rem 1.2rem;min-width:120px;">
            <div style="font-size:1.2rem;">🔢</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.3rem;">Raking 보정</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:0.8rem 1.2rem;min-width:120px;">
            <div style="font-size:1.2rem;">📉</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.3rem;">Deff 평가</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='margin-bottom: 5rem;'></div>", unsafe_allow_html=True) 
        return

    # 데이터 로드
    try:
        df = pd.read_csv(df_file) if df_file.name.endswith(".csv") else pd.read_excel(df_file)
        st.success(f"데이터 로드 완료: {len(df)} 행")
    except Exception as e:
        st.error(f"로드 중 오류: {e}")
        return

    # [v4.6] 코드북 파싱 및 매핑
    cb_parser = None
    if cb_file:
        try:
            with st.spinner("코드북 분석 중..."):
                cb_parser = CodebookParser(cb_file)
            st.success("코드북 연동 완료: 변수 및 응답값 라벨이 활성화되었습니다.")
        except Exception as e:
            st.error(f"코드북 파싱 오류: {e}")

    # 변수 선택
    st.markdown('<div class="qx-section-label">2. 가중치 보정 변수 설정</div>', unsafe_allow_html=True)
    all_col_labels = cb_parser.get_all_var_labels(df.columns) if cb_parser else df.columns.tolist()
    selected_weight_labels = st.multiselect("가중치를 부여할 기준 변수를 선택하세요 (예: 성별, 연령)", options=all_col_labels)
    weight_vars = [cb_parser.get_column_from_label(lb) for lb in selected_weight_labels] if cb_parser else selected_weight_labels

    if not weight_vars:
        st.info("변수를 선택하면 모집단 비율 입력란이 나타납니다.")
        return

    # 목표 비율 입력
    targets = {}
    st.markdown("##### 📍 모집단 목표 분포 입력 (%)")
    for i, var in enumerate(weight_vars):
        display_name = selected_weight_labels[i] if cb_parser else var
        with st.expander(f"변수: {display_name}", expanded=True):
            unique_vals = sorted(df[var].dropna().unique().tolist())
            targets[var] = {}
            
            # 코드북 라벨 적용 (응답값)
            cols = st.columns(len(unique_vals))
            for j, val in enumerate(unique_vals):
                label_val = cb_parser.get_value_label(var, val) if cb_parser else val
                with cols[j]:
                    prop = st.number_input(f"{label_val} (%)", min_value=0.0, max_value=100.0, value=100.0/len(unique_vals), key=f"target_{var}_{val}")
                    targets[var][val] = prop / 100.0
            
            # 합계 체크
            total_p = sum(targets[var].values())
            if abs(total_p - 1.0) > 0.001:
                st.warning(f"합계가 {total_p*100:.1f}%입니다. 100%가 되도록 조정하세요.")

    # [v4.7 추가] 목표 기반 데이터 증계 (Data Augmentation)
    st.markdown('<div class="qx-section-label">3. 목표 기반 데이터 증계 (Target-Driven Augmentation)</div>', unsafe_allow_html=True)
    with st.expander("🛠️ 소수 표본 및 쿼터 미달 세그먼트 데이터 생성", expanded=False):
        st.markdown("""
        표본 수가 부족한 특정 집단(Segment)에 대해 통계적 기법으로 데이터를 생성하여 목표 쿼터를 충족시킵니다.
        """)
        
        aug_cols = st.columns([2, 2, 1])
        with aug_cols[0]:
            sel_aug_vars = st.multiselect("증계 조건 변수 선택", options=all_col_labels, key="aug_vars")
            target_segment_cols = [cb_parser.get_column_from_label(lb) for lb in sel_aug_vars] if cb_parser else sel_aug_vars
        
        filter_dict = {}
        if target_segment_cols:
            st.markdown("##### 📍 세그먼트 조건 설정")
            f_cols = st.columns(len(target_segment_cols))
            for i, col in enumerate(target_segment_cols):
                unique_vals = sorted(df[col].dropna().unique().tolist())
                labels = [cb_parser.get_value_label(col, v) for v in unique_vals] if cb_parser else unique_vals
                with f_cols[i]:
                    sel_labels = st.multiselect(f"{sel_aug_vars[i]} 선택", options=labels, key=f"f_{col}")
                    if sel_labels:
                        if cb_parser:
                            rev_map = {cb_parser.get_value_label(col, v): v for v in unique_vals}
                            filter_dict[col] = [rev_map[lb] for lb in sel_labels]
                        else:
                            filter_dict[col] = sel_labels

        if filter_dict:
            mask = pd.Series([True] * len(df), index=df.index)
            for c, v in filter_dict.items():
                mask &= df[c].isin(v)
            current_count = len(df[mask])
            
            st.info(f"선택한 세그먼트의 현재 표본 수: **{current_count}**개")
            
            c1, c2 = st.columns(2)
            with c1:
                target_count = st.number_input("목표 표본 수", min_value=current_count + 1, value=max(current_count + 1, 20), key="aug_target_count")
            with c2:
                aug_method = st.selectbox("증계 기법", options=["Bootstrap", "Noise-added"], key="aug_method")
            
            if st.button("✨ 데이터 증계 실행", use_container_width=True):
                augmentor = DataAugmentor(df)
                added = augmentor.augment_by_filter(filter_dict, target_count, method=aug_method)
                if added > 0:
                    st.success(f"성공적으로 {added}개의 새로운 레코드가 생성되었습니다. (총 {len(augmentor.df)}명)")
                    st.session_state["aug_df"] = augmentor.df
                    st.session_state["aug_summary"] = augmentor.get_summary()
                    st.rerun() # 전체 UI 갱신 (가중치 섹션에도 반영되도록)
                else:
                    st.warning("증계할 데이터가 없거나 조건이 맞지 않습니다.")

        if "aug_summary" in st.session_state:
            s = st.session_state["aug_summary"]
            st.markdown(f"""
            - **전체 표본:** {s['total_count']}명 (원본: {s['original_count']}명 / 증계: {s['augmented_count']}명)
            - **증계 비율:** {s['augmented_ratio']}%
            """)
            if st.button("🗑️ 증계 취소 (원본 복구)"):
                if "aug_df" in st.session_state: del st.session_state["aug_df"]
                if "aug_summary" in st.session_state: del st.session_state["aug_summary"]
                st.rerun()

    # 증계된 데이터가 있으면 그것을 사용하여 가중치 산출 진행
    active_df = st.session_state["aug_df"] if "aug_df" in st.session_state else df

    # 4. 가중치 산출 실행
    st.markdown('<div class="qx-section-label">4. 가중치(Weighting) 산출 및 검정</div>', unsafe_allow_html=True)
    if st.button("🚀 가중치 산출(Raking) 실행", type="primary", use_container_width=True):
        calculator = WeightCalculator(active_df)
        with st.spinner("RIM Weighting 알고리즘 가동 중..."):
            iters, diff = calculator.apply_raking(targets)
            st.session_state["weighted_df"] = calculator.df
            st.session_state["weight_diag"] = calculator.get_diagnostics()
            st.success(f"가중치 산출 완료! (반복 횟수: {iters}, 최종 수렴 오차: {diff:.6f})")

    # 결과 표시
    if "weighted_df" in st.session_state:
        show_security_notice()
        st.markdown('<div class="qx-section-label">5. 분석 결과 및 다운로드</div>', unsafe_allow_html=True)
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

        # [v4.9] 리포트 및 Raw Data 분리 다운로드
        report_output = io.BytesIO()
        with pd.ExcelWriter(report_output, engine='xlsxwriter') as writer:
            st.session_state["weighted_df"].to_excel(writer, index=False, sheet_name='Weighted_Data')
            # 진단 정보 추가 (명사형 요약)
            diag_df = pd.DataFrame([st.session_state["weight_diag"]]).T
            diag_df.columns = ["통계치"]
            diag_df.to_excel(writer, index=True, sheet_name='Diagnostics')
        report_output.seek(0)
        
        raw_output = io.BytesIO()
        with pd.ExcelWriter(raw_output, engine='xlsxwriter') as writer:
            st.session_state["weighted_df"].to_excel(writer, index=False, sheet_name='Raw_Data')
        raw_output.seek(0)

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button("� 가중치 리포트 다운로드 (Excel)", data=report_output, file_name=f"가중치리포트_{df_file.name}", 
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_weight_report")
        with col_dl2:
            st.download_button("📥 최종 분석용 Raw Data 다운로드", data=raw_output, file_name=f"최종데이터_{df_file.name}", 
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_weight_raw")


def show_questionnaire_optimization_system():
    """AI 설문지 최적화 컨설턴트 UI (v5.0)"""
    st.markdown("""
    <div class="qx-topbar">
        <span class="qx-topbar-logo">AI 설문지 최적화</span>
        <span class="qx-topbar-sep"></span>
        <span class="qx-topbar-title">설문 설계 전문가 컨설팅</span>
        <span class="qx-topbar-badge">Methodology Optimization</span>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📘 AI 설문지 최적화 - 이용 방법 및 체크리스트 가이드", expanded=False):
        st.markdown("""
        ### 🛠️ AI 설문지 최적화 프로세스
        1. **설문안 입력:** 현재 작성 중인 설문지 텍스트(문항 및 보기)를 아래 입력창에 붙여넣습니다.
        2. **AI 정밀 진단:** 5대 설계 결함(유도 질문, 이중 질문, 보기 정합성, 모호성, 응답 거부 요소)을 전문가 관점에서 분석합니다.
        3. **개선안 도출:** 분석 결과에 따른 'Before & After' 개선 제언과 기대 효과를 확인합니다.
        
        ### 🔍 주요 체크리스트
        - **유도 질문:** "귀하는 성공적인 정책 A에 찬성하십니까?"와 같이 답을 정해둔 질문인가?
        - **이중 질문:** "가격과 품질에 만족하십니까?"처럼 한 문항에 두 가지를 묻는가?
        - **상호배타성:** 보기 간에 중복이 있거나 빠진 항목이 없는가?
        """)

    st.markdown('<div class="qx-section-label">1. 설문지 업로드 및 텍스트 입력</div>', unsafe_allow_html=True)
    
    q_file = st.file_uploader("설문지 파일 업로드 (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"], key="q_opt_file_up")
    
    # 새로운 파일이 업로드된 경우 텍스트 추출
    if q_file and q_file.name != st.session_state.get("q_opt_file_name"):
        with st.spinner("설문지 텍스트를 추출하는 중..."):
            from config import MAX_TEXT_CHARS
            text, _ = extract_text(q_file)
            if text:
                st.session_state["q_opt_input_text"] = truncate_text(text, MAX_TEXT_CHARS)
                st.session_state["q_opt_file_name"] = q_file.name
                st.success(f"'{q_file.name}'에서 텍스트를 성공적으로 가져왔습니다.")

    q_text = st.text_area(
        "분석할 설문 문항 (직접 입력하거나 위에서 파일을 업로드하세요)", 
        value=st.session_state.get("q_opt_input_text", ""),
        height=350, 
        placeholder="예: Q1. 귀하는 본 서비스에 대해 얼마나 만족하십니까?\n1) 매우 만족  2) 만족  3) 보통  4) 불만족  5) 매우 불만족",
        help="파일을 업로드하면 내용이 자동으로 채워집니다. 직접 수정도 가능합니다."
    )
    # 직접 수정한 내용을 세션 상태에 동기화
    st.session_state["q_opt_input_text"] = q_text

    if st.button("🚀 AI 설계 최적화 시작", type="primary", use_container_width=True):
        if not q_text.strip():
            st.warning("분석할 설문 텍스트를 입력해 주세요.")
        else:
            from prompts import QUESTIONNAIRE_ANALYSIS_PROMPT
            with st.spinner("설문 설계 전문가가 문항을 심층 분석 중입니다..."):
                prompt = QUESTIONNAIRE_ANALYSIS_PROMPT.format(questionnaire_text=q_text)
                res, err = run_analysis("설문 설계 전문가", prompt, "설문 문항 분석 및 개선안 도출 중...")
                
                if err:
                    st.error(f"분석 중 오류 발생: {err}")
                else:
                    st.session_state["q_opt_result"] = res
                    st.rerun()

    if "q_opt_result" in st.session_state:
        show_security_notice()
        st.markdown('<div class="qx-section-label">2. 전문가 진단 및 개선 제언</div>', unsafe_allow_html=True)
        st.markdown(st.session_state["q_opt_result"], unsafe_allow_html=True)
        
        # 워드 다운로드 지원
        if st.button("📝 분석 결과 워드 파일로 다운로드", use_container_width=True):
            md_content = f"# AI 설문지 최적화 분석 보고서\n\n{st.session_state['q_opt_result']}"
            docx = export_to_docx(md_content)
            st.download_button(
                "📥 클릭하여 워드 저장", 
                data=docx, 
                file_name="설문지_최적화_컨설팅.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )


def show_sample_design_system():
    """AI 표본설계 자동화 시스템 UI (v5.0)"""
    st.markdown("""
    <div class="qx-topbar">
        <span class="qx-topbar-logo">AI 표본설계</span>
        <span class="qx-topbar-sep"></span>
        <span class="qx-topbar-title">주민등록 인구 기반 표본 배분 솔루션</span>
        <span class="qx-topbar-badge">Sample Allocation Engine</span>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📘 AI 표본설계 - 주요 할당 방식 및 수식 안내", expanded=False):
        st.markdown(r"""
        ### ⚖️ 표본 할당 방식(Allocation Methods)
        
        1. **인구비례할당 (Proportional Allocation):**
           - 각 층(Strata)의 모집단 크기에 정비례하여 표본을 배분합니다. 가장 일반적인 방식입니다.
           - 산식: $n_h = n \times \frac{P_h}{\sum P_h}$
        
        2. **제곱근 비례 할당 (Square Root Proportional):**
           - 소규모 지역/계층의 대표성이 너무 낮아지는 것을 방지하기 위해 인구수의 제곱근에 비례하여 배분합니다.
           - 산식: $n_h = n \times \frac{\sqrt{P_h}}{\sum \sqrt{P_h}}$
        
        3. **최소표본 할당 후 비례할당 (Min-Proportional):**
           - 모든 계층에 최소한의 표본($Min$)을 먼저 보장하고, 남은 표본을 인구비례로 배분합니다.
           - 산식: $n_h = Min + (n - \sum Min) \times \frac{P_h}{\sum P_h}$

        ---
        ### ℹ️ 주민등록 인구 데이터 획득 방법 (행정안전부)
        정확한 표본 배분을 위해 최신 통계 데이터를 활용하십시오.
        1. **홈페이지 접속:** [행정안전부 주민등록 인구통계](https://jumin.mois.go.kr/#)
        2. **메뉴 선택:** 상단 메뉴의 **'연령별 인구현황'** 클릭
        3. **조건 설정:** 조회 조건에서 **'연령구분 단위'**를 **'1세'** 단위로 설정
        4. **데이터 다운로드:** 조회 후 엑셀 파일을 다운로드하여 활용하십시오.
        """)

    st.markdown('<div class="qx-section-label">1. 모집단 데이터 입력 (인구 현황)</div>', unsafe_allow_html=True)
    
    tab_api, tab_file, tab_manual = st.tabs(["🌐 API 실시간 조회", "📁 파일 업로드", "✍️ 직접 입력"])
    df_raw = None

    with tab_api:
        st.markdown("##### 🏛️ 행정안전부 주민등록 인구 API 연동")
        c_api1, c_api2, c_api3 = st.columns(3)
        with c_api1:
            sido_name = st.selectbox("지역(시도) 선택", options=list(api_utils.SIDO_MAP.keys()), index=1)
            sido_cd = api_utils.SIDO_MAP[sido_name]
        with c_api2:
            age_interval = st.selectbox("연령 구분 단위", options=[1, 5, 10], index=2, format_func=lambda x: f"{x}세 단위")
        with c_api3:
            age_range = st.slider("분석 연령대 설정", 0, 100, (18, 69))
        
        if st.button("🔍 실시간 인구 데이터 가져오기", use_container_width=True, type="secondary"):
            with st.spinner(f"{sido_name} 인구 데이터를 API로 수신 중..."):
                raw_api_df = api_utils.fetch_population_data(sido_cd=sido_cd)
                if raw_api_df is not None:
                    processed_df = api_utils.process_population_df(raw_api_df, min_age=age_range[0], max_age=age_range[1])
                    if processed_df is not None and not processed_df.empty:
                        st.session_state["api_pop_df"] = api_utils.aggregate_by_groups(processed_df, interval=age_interval)
                        st.success(f"{sido_name} 데이터 수신 및 {age_range[0]}세-{age_range[1]}세 필터링 완료 ({age_interval}세 단위)")
                    else:
                        st.warning("해당 조건에 맞는 인구 데이터가 없습니다.")

        if "api_pop_df" in st.session_state:
            st.dataframe(st.session_state["api_pop_df"], hide_index=True, use_container_width=True)
            if st.button("✅ 위 데이터를 모집단으로 확정", use_container_width=True):
                st.session_state["pop_source_df"] = st.session_state["api_pop_df"]
                st.rerun()

    with tab_file:
        col_u1, col_u2 = st.columns([1, 1], gap="medium")
        uploaded_pop = None
        with col_u1:
            st.markdown("##### 📁 파일 업로드 (Excel, CSV)")
            pop_file = st.file_uploader("인구 통계 파일 업로드", type=["xlsx", "csv"], key="sample_pop_file")
            if pop_file:
                try:
                    if pop_file.name.endswith(".csv"):
                        uploaded_pop = pd.read_csv(pop_file)
                    else:
                        uploaded_pop = pd.read_excel(pop_file)
                    st.success(f"'{pop_file.name}' 로드 완료 ({len(uploaded_pop)}개 행)")
                except Exception as e:
                    st.error(f"파일 로드 중 오류: {e}")

        if uploaded_pop is not None:
            st.dataframe(uploaded_pop.head(5), hide_index=True, use_container_width=True)
            if st.button("✅ 업로드 파일을 모집단으로 확정", use_container_width=True):
                st.session_state["pop_source_df"] = uploaded_pop
                st.rerun()

    with tab_manual:
        st.markdown("##### ✍️ 직접 입력 / 예시 데이터")
        default_data = "지역, 성별, 연령대, 인구수\n서울, 남, 20대, 650000\n서울, 여, 20대, 680000\n부산, 남, 20대, 210000\n부산, 여, 20대, 220000\n인천, 남, 20대, 195000\n인천, 여, 20대, 198000"
        pop_input = st.text_area(
            "데이터를 CSV 형식으로 입력하세요", 
            value=default_data,
            height=200,
            help="첫 줄에 헤더(지역, 성별 등)를 포함하여 입력하세요."
        )
        if st.button("✅ 입력 데이터를 모집단으로 확정", use_container_width=True):
            try:
                import io
                st.session_state["pop_source_df"] = pd.read_csv(io.StringIO(pop_input.strip()), skipinitialspace=True)
                st.rerun()
            except Exception as e:
                st.error(f"입력 데이터 파싱 오류: {e}")

    # 최종 모집단 데이터 확정 확인
    if "pop_source_df" not in st.session_state:
        st.info("상단 탭 중 하나를 선택하여 모집단 인구 데이터를 로드하고 '확정' 버튼을 클릭해 주세요.")
        return

    df_raw = st.session_state["pop_source_df"]

    # 컬럼 설정 (인구수 컬럼 자동 감지 또는 마지막 컬럼 사용)
    cols = df_raw.columns.tolist()
    pop_col = None
    for c in cols:
        if any(kw in str(c) for kw in ["인구", "population", "count", "N수", "N"]):
            pop_col = c
            break
    if not pop_col:
        pop_col = cols[-1]
    
    df_raw[pop_col] = pd.to_numeric(df_raw[pop_col], errors='coerce').fillna(0)
    strata_cols = [c for c in cols if c != pop_col]

    st.info(f"🧬 **층화 구조:** {' > '.join(strata_cols)} | **총 인구:** {df_raw[pop_col].sum():,}")

    st.markdown('<div class="qx-section-label">2. 표본 설계 설정</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        total_n = st.number_input("목표 전체 표본 수 (n)", min_value=1, value=1000)
    with c2:
        method = st.selectbox("할당 방식 선택", options=["인구비례할당", "제곱근 비례 할당", "최소표본 할당 후 비례할당"])
    with c3:
        min_n = st.number_input("최소 할당 표본 (Min)", min_value=1, value=30, disabled=(method != "최소표본 할당 후 비례할당"))

    if st.button("📊 표본 배분 계산 실행", type="primary", use_container_width=True):
        total_pop = df_raw[pop_col].sum()
        df_work = df_raw.copy()
        
        if method == "인구비례할당":
            df_work["allocated"] = (df_work[pop_col] / total_pop * total_n)
        elif method == "제곱근 비례 할당":
            sqrt_sum = df_work[pop_col].apply(np.sqrt).sum()
            df_work["allocated"] = (df_work[pop_col].apply(np.sqrt) / sqrt_sum * total_n)
        elif method == "최소표본 할당 후 비례할당":
            num_groups = len(df_work)
            if min_n * num_groups > total_n:
                st.error(f"최소 표본 합계({min_n * num_groups})가 전체 표본({total_n})보다 큽니다. 설정을 조정해 주세요.")
                return
            remaining_n = total_n - (min_n * num_groups)
            df_work["allocated"] = min_n + (df_work[pop_col] / total_pop * remaining_n)
        
        # 반올림 및 합계 조정
        df_work["final_n"] = df_work["allocated"].round().astype(int)
        diff = total_n - df_work["final_n"].sum()
        if diff != 0:
            df_work["remainder"] = df_work["allocated"] - df_work["final_n"]
            if diff > 0:
                idx = df_work.nlargest(diff, "remainder").index
                df_work.loc[idx, "final_n"] += 1
            else:
                idx = df_work.nsmallest(abs(diff), "remainder").index
                df_work.loc[idx, "final_n"] -= 1

        df_work["비율(%)"] = (df_work["final_n"] / total_n * 100).round(1)
        st.session_state["sample_design_df"] = df_work[cols + ["final_n", "비율(%)"]]
        st.session_state["sample_design_meta"] = {"pop_col": pop_col, "strata_cols": strata_cols}
        st.rerun()

    if "sample_design_df" in st.session_state:
        st.markdown('<div class="qx-section-label">3. 표본 할당 결과</div>', unsafe_allow_html=True)
        res_df = st.session_state["sample_design_df"]
        meta = st.session_state["sample_design_meta"]
        
        st.dataframe(
            res_df, 
            hide_index=True,
            column_config={
                meta["pop_col"]: st.column_config.NumberColumn("모집단(P)", format="%d"),
                "final_n": st.column_config.NumberColumn("확정 표본(n)", format="%d"),
            },
            use_container_width=True
        )

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("전체 표본", f"{res_df['final_n'].sum()}명")
        sc2.metric("최소 할당", f"{res_df['final_n'].min()}명")
        sc3.metric("최대 할당", f"{res_df['final_n'].max()}명")

        # 시각화 컬럼 선택
        st.markdown("##### 📈 시각화 설정")
        viz_col = st.selectbox("X축 기준 변수 선택", options=meta["strata_cols"], index=0)
        
        # 층화 변수가 여러개면 그룹화하여 표시
        viz_df = res_df.groupby(viz_col)["final_n"].sum().reset_index()
        fig = px.bar(viz_df, x=viz_col, y="final_n", text="final_n", title=f"{viz_col}별 표본 배분 합계", template="plotly_white")
        fig.update_traces(marker_color="#0F6CBD", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

        if st.button("📥 상세 표본 설계 내역 다운로드 (Excel)", use_container_width=True):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, index=False, sheet_name='Sample_Design')
            output.seek(0)
            st.download_button(
                "📥 클릭하여 엑셀 파일 저장", 
                data=output, 
                file_name="표본설계_상세배분안.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_sample_design_final"
            )


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

    # [v4.8 고도화] 실무용 이용 가이드 (명사형 어미)
    with st.expander(f"📘 AI {'이상치' if mode == 'outlier' else '결측치'} 검토 - 이용 방법 및 데이터 프로세스 가이드", expanded=False):
        st.markdown("### 🗺️ 데이터 처리 로드맵")
        show_data_roadmap(3)
        if mode == "outlier":
            st.markdown("""
            ### 🛠️ 데이터 이상치(Outlier) 검토 단계
            1. **데이터 업로드 및 연동:** 원본 시계열/조사 데이터와 코드북을 함께 업로드하여 변수 라벨을 활성화합니다.
            2. **시각적 패턴 분석:** 산점도(Scatter)와 바이올린(Violin) 플롯을 통해 통계적 분포를 벗어난 극단값을 시각적으로 확인합니다.
            3. **이상치 사전 진단:** Z-score > 3 기준의 주요 이상 변수 요약 테이블을 통해 보완 우선순위를 판단합니다.
            4. **보완 전략 수립:** 
               - **AI 추천:** 변수의 특성(수치/범주)에 따른 최적 알고리즘 추천 제안을 확인합니다.
               - **통계적 보정:** 전체/층별 평균, k-NN, MICE 등을 지정하여 이상치를 합리적인 값으로 대체합니다.
               - **재확인(Call-back):** 기입 오류가 아닌 실제 값 확인이 필요한 경우 재조사 대상으로 분류합니다.
            5. **최종 로그 검수:** 대체 전/후 값과 적용 사유가 기록된 감사 로그(Audit Log)를 최종 검토합니다.
            """)
        else:
            st.markdown("""
            ### 🛠️ 데이터 결측치(Missing) 보완 단계
            1. **결측 패턴 정밀 진단:** 
               - '결측 히트맵'을 통해 변수 간 결측 상관관계를 파악합니다.
               - AI 진단을 통해 MCAR(무작위 결측) 여부를 판별하고 보완 적합성을 평가합니다.
            2. **보완 알고리즘 엔진 가동:** 
               - **단일 대체:** 평균, 중앙값, 최빈값 등 빠른 보완이 필요한 경우 사용합니다.
               - **다중 대체(MICE):** 변수 간 회귀 관계를 활용하여 정보 손실을 최소화하는 고난도 보완에 적격입니다.
               - **최근접 이웃(k-NN):** 유사한 응답 패턴을 가진 다른 사례의 값을 참조하여 정교하게 대체합니다.
            3. **조사 가이드 생성:** 보완이 불가능한 필수 항목 결측에 대해 AI가 재조사 스크립트를 자동 생성합니다.
            4. **통합 데이터 배포:** 보완된 데이터와 원본을 대조할 수 있는 'Imputation Marker'가 포함된 리포트를 다운로드합니다.
            """)

    # [v4.5 고도화] 전문가용 가이드 (명사형 어미 및 통계 기법 확장)
    with st.expander(f"📘 AI {'이상치' if mode == 'outlier' else '결측치'} 검토 - 통계적 판별 및 보완 알고리즘 안내", expanded=False):
        if mode == "outlier":
            st.markdown("""
            ### 🔍 이상치 탐지 모델 (Outlier Detection)
            데이터의 분포 특성에 따른 두 가지 보편적 통계 기준 적용 방식

            #### **1. 표준점수 (Z-score) 기법**
            데이터가 정규분포를 따른다는 가정 하에 평균으로부터 표준편차($\sigma$)의 3배 이상 이탈한 값을 이상치로 판별하는 방식
            """)
            st.latex(r"z = \frac{x - \mu}{\sigma}")
            st.markdown("""
            - **판정 기준:** $|z| > 3.0$ 인 경우 통계적 유의수준 99.7% 범위를 벗어난 극단치로 간주함

            #### **2. IQR (Interquartile Range) 기법**
            비모수적 분포에서도 강건한(Robust) 탐지가 가능한 사분위수 기반의 격리 방식
            - **Upper Fence:** $Q3 + 1.5 \times (Q3 - Q1)$
            - **Lower Fence:** $Q1 - 1.5 \times (Q3 - Q1)$
            - 바이올린 플롯 내부 박스 구조를 통한 시각적 가중치 확인 기능 포함
            """)
        else:
            st.markdown("""
            ### 🔍 결측치 보완 알고리즘 (Imputation Techniques)
            결측 발생 기제(MCAR, MAR, MNAR)에 따른 최적 알고리즘 선택 및 적용

            #### **1. 회귀 대체 및 MICE (Multivariate Imputation by Chained Equations)**
            다변량 데이터의 상관관계 유지를 위한 최신 기법으로, 변수별 결측치를 타 변수들을 독립변수로 하는 회귀 모델을 통해 반복 예측 보완하는 방식 (연쇄 방정식 기반의 회귀 대체 고도화 모델)
            """)
            st.latex(r"Y_j = f(Y_{-j}, X, \beta) + \epsilon")
            st.markdown("""
            - **특이점:** 변수 간 상관성을 유지하며 편향을 최소화하는 하이엔드 통계 기법

            #### **2. 최근방 대체 및 k-NN (k-Nearest Neighbors) Imputation**
            유사성이 가장 높은 $k$개의 이웃 사례를 추출하여 해당 관측값들의 가중 평균으로 대체하는 최근방 이웃 방식
            - **거리 척도:** 유클리드 거리(Euclidean Distance)를 활용한 개체 간 유사도 정밀 측정

            #### **3. 기타 통계적 대체 기법**
            - **평균/최빈값 대체 (Mean/Mode Imputation):** 데이터의 중심 경향성을 활용한 단순 대체 방식
            - **유사 사례 기증법 (Hot-deck Imputation):** 현재 조사 내 유사 응답자의 값을 직접 복사하여 기증하는 실무 중심형 방식
            - **고정값 대체 (Cold-deck Imputation):** 과거 조사 결과나 외부 데이터를 기준값으로 활용하는 보수적 대체 방식
            """)

    # [v3.6 추가] 주요 기능 요약 카드 (메인 화면 스타일)

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

    # 1. 파일 업로드 (2컬럼 레이아웃)
    st.markdown('<div class="qx-section-label">1. 데이터 및 코드북 업로드 (Excel/CSV)</div>', unsafe_allow_html=True)
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        df_file = st.file_uploader(f"분석할 데이터 업로드 ({mode})", type=["xlsx", "csv"], key=f"uploader_{mode}")
    with col_up2:
        cb_file = st.file_uploader(f"코드북 업로드 (선택 사항)", type=["xlsx"], key=f"cb_{mode}")

    if not df_file:
        if mode == "outlier":
            st.markdown("""
<div class="qx-card" style="text-align:center; padding:2rem 2rem 2.5rem 2rem; margin-top: 1rem; margin-bottom: 2rem; min-height: 320px;">
    <div style="font-size:3rem; margin-bottom:0.5rem;">📈</div>
    <div style="font-size:1.1rem; font-weight:600; color:#1A2237; margin-bottom:0.5rem;">
        검토할 데이터를 업로드하세요
    </div>
    <div style="font-size:0.87rem; color:#8B96A9; margin-bottom:1.5rem;">
        Excel 또는 CSV 데이터를 업로드하면 AI가 이상치 탐지 및 시각적 진단을 수행합니다.
    </div>
    <div style="display:flex; justify-content:center; gap:1.5rem; flex-wrap:wrap;">
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:0.8rem 1.2rem;min-width:120px;">
            <div style="font-size:1.2rem;">📍</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.3rem;">시각적 진단</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:0.8rem 1.2rem;min-width:120px;">
            <div style="font-size:1.2rem;">📏</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.3rem;">통계적 탐지</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:0.8rem 1.2rem;min-width:120px;">
            <div style="font-size:1.2rem;">🧠</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.3rem;">AI 보완 방법</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown("""
<div class="qx-card" style="text-align:center; padding:2rem 2rem 2.5rem 2rem; margin-top: 1rem; margin-bottom: 2rem; min-height: 320px;">
    <div style="font-size:3rem; margin-bottom:0.5rem;">📊</div>
    <div style="font-size:1.1rem; font-weight:600; color:#1A2237; margin-bottom:0.5rem;">
        분석할 데이터를 업로드하세요
    </div>
    <div style="font-size:0.87rem; color:#8B96A9; margin-bottom:1.5rem;">
        데이터를 업로드하면 AI가 결측 패턴을 분석하고 최적의 통계적 보완을 제안합니다.
    </div>
    <div style="display:flex; justify-content:center; gap:1.5rem; flex-wrap:wrap;">
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:0.8rem 1.2rem;min-width:120px;">
            <div style="font-size:1.2rem;">🔍</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.3rem;">패턴 분석</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:0.8rem 1.2rem;min-width:120px;">
            <div style="font-size:1.2rem;">🧪</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.3rem;">고급 보완(MICE)</div>
        </div>
        <div style="background:#F4F6F9;border:1px solid #E5E9F0;border-radius:8px;padding:0.8rem 1.2rem;min-width:120px;">
            <div style="font-size:1.2rem;">🎙️</div>
            <div style="font-size:0.75rem;font-weight:600;color:#3D4F6B;margin-top:0.3rem;">조사 가이드</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='margin-bottom: 5rem;'></div>", unsafe_allow_html=True) 
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

    # [v4.6] 코드북 파킹 및 매핑
    cb_parser = None
    if cb_file:
        try:
            with st.spinner("코드북 분석 중..."):
                cb_parser = CodebookParser(cb_file)
            st.success("코드북 연동 완료: 변수 설명 및 코드표가 활성화되었습니다.")
            
            # [v4.6 추가] 코드북 미리보기 공간
            with st.expander("📘 연동 코드북 상세 정보 (변수설명 및 코드표)", expanded=False):
                tab_cb1, tab_cb2 = st.tabs(["📋 변수 리스트 및 설명", "🔢 코드/라벨 매핑 테이블"])
                with tab_cb1:
                    if cb_parser.var_map:
                        var_preview_df = pd.DataFrame([
                            {"문번호": v['no'], "변수명": k, "변수설명": v['desc']} 
                            for k, v in cb_parser.var_map.items()
                        ])
                        st.dataframe(var_preview_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("파싱된 변수 설명 정보가 없습니다.")
                with tab_cb2:
                    if cb_parser.code_map:
                        all_codes = []
                        for var, codes in cb_parser.code_map.items():
                            for c, l in codes.items():
                                all_codes.append({"변수명": var, "코드": c, "라벨": l})
                        st.dataframe(pd.DataFrame(all_codes), use_container_width=True, hide_index=True)
                    else:
                        st.info("파싱된 코드표 정보가 없습니다.")
        except Exception as e:
            st.error(f"코드북 파싱 오류: {e}")

    st.success(f"데이터 로드 완료: {len(df)} 행, {len(df.columns)} 열")
    
    # [v3.5 추가] 시각적 이상치 판별 섹션
    if mode == "outlier":
        with st.expander("📈 시각적 이상치 판별 (Scatter & Violin)", expanded=False):
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) < 1:
                st.warning("시각화할 수 있는 수치형 변수가 없습니다.")
            else:
                viz_tab1, viz_tab2 = st.tabs(["📍 산점도 (Scatter Plot)", "🎻 바이올린 플롯 (Violin Plot)"])
                
                # 라벨 맵핑 리스트
                col_labels = cb_parser.get_all_var_labels(numeric_cols) if cb_parser else numeric_cols

                with viz_tab1:
                    st.markdown("##### 두 변수 간의 관계와 극단값 확인")
                    c1, c2, c3 = st.columns([2, 2, 1])
                    with c1:
                        x_label = st.selectbox("X축 변수", options=col_labels, key="viz_x")
                        x_axis = cb_parser.get_column_from_label(x_label) if cb_parser else x_label
                    with c2:
                        y_label = st.selectbox("Y축 변수", options=col_labels, index=min(1, len(col_labels)-1), key="viz_y")
                        y_axis = cb_parser.get_column_from_label(y_label) if cb_parser else y_label
                    with c3:
                        dot_color = st.color_picker("점 색상", "#0F6CBD", key="viz_color")
                    
                    fig_scatter = px.scatter(df, x=x_axis, y=y_axis, template="plotly_white", 
                                           title=f"{x_label} vs {y_label} 산점도",
                                           labels={x_axis: x_label, y_axis: y_label})
                    fig_scatter.update_traces(marker=dict(color=dot_color, size=8, opacity=0.6))
                    st.plotly_chart(fig_scatter, use_container_width=True)
                
                with viz_tab2:
                    st.markdown("##### 데이터의 분포 밀도와 이상치 범위 확인")
                    v_label = st.selectbox("분석할 변수", options=col_labels, key="viz_v")
                    v_col = cb_parser.get_column_from_label(v_label) if cb_parser else v_label
                    fig_violin = px.violin(df, y=v_col, box=True, points="all", template="plotly_white",
                                         title=f"{v_label} 분포 분석 (Violin & Box)",
                                         labels={v_col: v_label})
                    fig_violin.update_traces(fillcolor="#0F6CBD", opacity=0.6, line=dict(color="black"))
                    st.plotly_chart(fig_violin, use_container_width=True)

        # [v4.6 추가] 데이터 이상치 사전 진단 (결측치와 동일한 테이블 형식)
        with st.expander("📊 데이터 이상치 사전 진단 (v4.6)", expanded=False):
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            outlier_stats = []
            for c in numeric_cols:
                m = df[c].mean()
                s = df[c].std()
                cnt = len(df[(df[c] < m - 3*s) | (df[c] > m + 3*s)])
                if cnt > 0:
                    outlier_stats.append({
                        "변수명": cb_parser.get_var_label(c) if cb_parser else c,
                        "원본ID": c,
                        "이상치건수(Z>3)": cnt,
                        "비중(%)": round(cnt / len(df) * 100, 1)
                    })
            
            if not outlier_stats:
                st.info("통계적 이상치(Z-score > 3)가 발견되지 않았습니다. ✨")
            else:
                outlier_df = pd.DataFrame(outlier_stats).sort_values("이상치건수(Z>3)", ascending=False)
                col_o1, col_o2 = st.columns([1, 1])
                with col_o1:
                    st.markdown("### 🔍 주요 이상 변수")
                    st.dataframe(outlier_df.drop(columns=["원본ID"]), hide_index=True, use_container_width=True)
                with col_o2:
                    st.markdown("### 🤖 AI 이상치 원인 추론")
                    if st.button("🧠 AI 이상치 진단 실행", key="diag_btn_out"):
                        diag_prompt = f"다음 변수들의 이상치 정보를 보고 단순 기입 오류 가능성인지, 실제 극단값 사례 가능성인지 추론해줘.\n{outlier_df.to_string()}"
                        res, err = run_analysis("데이터 품질 전문가", diag_prompt, "이상 패턴 분석 중...")
                        if not err: st.info(res)
                        else: st.error(f"진단 오류: {err}")

    # [v3.0 추가] 결측치 패턴 분석 섹션
    if mode == "imputation":
        with st.expander("📊 데이터 결측 패턴 분석 (v3.0)", expanded=False):
            missing_counts = df.isnull().sum()
            
            # [v4.6] 변수명 라벨링 적용
            m_labels = [cb_parser.get_var_label(c) if cb_parser else c for c in missing_counts.index]
            
            missing_df = pd.DataFrame({
                "변수명": m_labels,
                "원본ID": missing_counts.index,
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
                    st.dataframe(missing_df.drop(columns=["원본ID"]), hide_index=True, use_container_width=True)
                with col_m2:
                    st.markdown("### 🤖 AI 결측 유형 진단")
                    if st.button("🧠 AI 패턴 진단 실행", key="diag_btn_ai"):
                        diag_prompt = f"다음 데이터의 결측 현황을 보고 MCAR, MAR, MNAR 중 유형을 진단해줘.\n{missing_df.to_string()}"
                        res, err = run_analysis("데이터 품질 전문가", diag_prompt, "결측 패턴 추론 중...")
                        if not err: st.info(res)
                        else: st.error(f"진단 오류: {err}")

    # 2. 변수 선택
    st.markdown('<div class="qx-section-label">2. 검토 대상 변수 선택</div>', unsafe_allow_html=True)
    all_col_labels = cb_parser.get_all_var_labels(df.columns) if cb_parser else df.columns.tolist()
    selected_labels = st.multiselect("검토가 필요한 변수를 선택하세요", options=all_col_labels, key=f"targets_{mode}")
    target_cols = [cb_parser.get_column_from_label(lb) for lb in selected_labels] if cb_parser else selected_labels

    if not target_cols:
        st.warning("분석할 변수를 최소 하나 이상 선택해 주세요.")
        return

    # 3. 변수별 보완 설정
    st.markdown('<div class="qx-section-label">3. 변수별 보완 방법 설정</div>', unsafe_allow_html=True)
    
    impute_configs = {}
    
    for i, col in enumerate(target_cols):
        display_name = selected_labels[i] if cb_parser else col
        with st.expander(f"📍 변수: {display_name}", expanded=True):
            col_a, col_b = st.columns([2, 1])
            
            with col_b:
                if st.button(f"🪄 AI 추천", key=f"ai_rec_{mode}_{col}"):
                    # AI 추천 로직
                    prompt = f"다음 변수의 데이터 대체 방법을 추천하고 이유를 설명해줘. 변수명: {display_name}, 타입: {df[col].dtype}, 샘플: {df[col].dropna().head(5).tolist()}"
                    res, err = run_analysis("데이터 분석 전문가", prompt, "샘플 데이터 분석 중...")
                    if not err: st.session_state[f"rec_{mode}_{col}"] = res
                    else: st.session_state[f"rec_{mode}_{col}"] = f"AI 추천 생성 중 오류: {err}"
                
                if f"rec_{mode}_{col}" in st.session_state:
                    st.caption(st.session_state[f"rec_{mode}_{col}"])

            with col_a:
                methods = ["전체 평균 대체", "중앙값 대체", "최빈값 대체", "층별 평균 대체", "MICE 다중 대체", "k-NN 대체", "재확인(Call Back)", "직접 입력"]
                selected_method = st.selectbox(f"보완 방법 선택 ({col})", options=methods, key=f"method_{mode}_{col}")
                
                options = {}
                if selected_method == "층별 평균 대체":
                    # [v4.6] 층별 변수도 라벨링 적용
                    st_labels = cb_parser.get_all_var_labels([c for c in df.columns if c != col]) if cb_parser else [c for c in df.columns if c != col]
                    sel_st_labels = st.multiselect(f"층(Strata) 변수 선택 ({display_name})", options=st_labels, key=f"strata_{mode}_{col}")
                    options["strata"] = [cb_parser.get_column_from_label(lb) for lb in sel_st_labels] if cb_parser else sel_st_labels
                elif selected_method == "k-NN 대체":
                    k_val = st.slider(f"k값 설정 ({display_name})", 1, 10, 5, key=f"k_{mode}_{col}")
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
                if mode == "imputation":
                    missing_idx = df[df[col].isna()].index.tolist()
                else:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        m = df[col].mean()
                        s = df[col].std()
                        missing_idx = df[(df[col] < m - 3*s) | (df[col] > m + 3*s) | df[col].isna()].index.tolist()
                    else:
                        missing_idx = df[df[col].isna()].index.tolist()
                
                if not missing_idx: continue
                
                method = config["method"]
                opts = config["options"]
                
                if method == "전체 평균 대체": imputer.impute_grand_mean(col, missing_idx)
                elif method == "중앙값 대체": imputer.impute_median(col, missing_idx)
                elif method == "최빈값 대체": imputer.impute_mode(col, missing_idx)
                elif method == "층별 평균 대체" and opts.get("strata"): imputer.impute_stratified_mean(col, missing_idx, opts["strata"])
                elif method == "k-NN 대체": imputer.impute_knn(col, missing_idx, k=opts.get("k", 5))
                elif method == "MICE 다중 대체": imputer.impute_mice(col, missing_idx)
                elif method == "재확인(Call Back)": imputer._apply_imputation(col, missing_idx, "CALL_BACK", "재확인 대상분류")
                else: imputer.impute_grand_mean(col, missing_idx)
            
            st.session_state[f"imputed_df_{mode}"] = imputer.df
            st.session_state[f"impute_summary_{mode}"] = imputer.get_summary()
            st.session_state[f"impute_log_{mode}"] = imputer.audit_log
            
        st.success("데이터 보완 처리가 완료되었습니다!")

    # 5. 결과 확인 및 다운로드
    if f"imputed_df_{mode}" in st.session_state:
        show_security_notice()
        st.markdown('<div class="qx-section-label">4. 결과 요약 및 다운로드</div>', unsafe_allow_html=True)
        
        summary = st.session_state[f"impute_summary_{mode}"]
        if isinstance(summary, dict) and summary:
            cols_metric = st.columns(min(len(summary), 4))
            for i, (col_name, count) in enumerate(summary.items()):
                idx = i % 4
                display_name = cb_parser.get_var_label(col_name) if cb_parser else col_name
                cols_metric[idx].metric(display_name, f"{count}건")
        
        orig_df = df.copy()
        adj_df = st.session_state[f"imputed_df_{mode}"]
        log_list = st.session_state[f"impute_log_{mode}"]
        log_df = pd.DataFrame(log_list)

        # [v4.6] 로그 프레임에 라벨 추가
        if not log_df.empty:
            log_df["변수설명"] = log_df["변수명"].apply(lambda x: cb_parser.get_var_label(x) if cb_parser else x)
            # 코드값 라벨링 (기존값, 대체값)
            if cb_parser:
                log_df["기존라벨"] = log_df.apply(lambda r: cb_parser.get_value_label(r["변수명"], r["기존값"]), axis=1)
                log_df["대체라벨"] = log_df.apply(lambda r: cb_parser.get_value_label(r["변수명"], r["대체값"]), axis=1)
            
            # 컬럼 순서 조정
            cols_order = ["인덱스", "변수명", "변수설명", "기존값"]
            if "기존라벨" in log_df.columns: cols_order.append("기존라벨")
            cols_order.extend(["대체값"])
            if "대체라벨" in log_df.columns: cols_order.append("대체라벨")
            cols_order.append("적용방법")
            log_df = log_df[cols_order]

        # 결과 엑셀용 DF 구성
        export_df = orig_df.copy()
        for col in target_cols:
            export_df[f"{col}_보완"] = adj_df[col]
            method_map = {row['인덱스']: row['적용방법'] for row in log_list if row['변수명'] == col}
            export_df[f"{col}_보완방법"] = export_df.index.map(lambda x: method_map.get(x, ""))

        # [v4.9] 리포트 및 Raw Data 분리 다운로드
        report_output = io.BytesIO()
        with pd.ExcelWriter(report_output, engine='xlsxwriter') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Audit_Report')
            if not log_df.empty: 
                log_df.to_excel(writer, index=False, sheet_name='Audit_Log')
        report_output.seek(0)
        
        raw_output = io.BytesIO()
        with pd.ExcelWriter(raw_output, engine='xlsxwriter') as writer:
            adj_df.to_excel(writer, index=False, sheet_name='Raw_Data')
        raw_output.seek(0)

        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.download_button("📝 감사 리포트 다운로드 (Excel)", data=report_output, file_name=f"보완리포트_{df_file.name}", 
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"dl_report_{mode}")
        with col_exp2:
            st.download_button("📥 최종 분석용 Raw Data 다운로드", data=raw_output, file_name=f"최종데이터_{df_file.name}", 
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"dl_raw_{mode}")
        
        with st.expander("📝 상세 보완 내역 (Log)", expanded=True):
            st.dataframe(log_df, use_container_width=True, hide_index=True)
            
        callback_df = log_df[log_df["적용방법"] == "재확인 대상분류"]
        if not callback_df.empty:
            st.markdown('<div class="qx-section-label" style="color:#d32f2f;">🚨 재조사(Call-back) 필요 명단</div>', unsafe_allow_html=True)
            st.error(f"총 {len(callback_df)}건의 데이터가 재확인 대상으로 분류되었습니다.")
            
            target_callback_labels = callback_df["변수설명"].unique().tolist()
            if st.button("🎙️ AI 재조사 질문 가이드 생성", key="btn_callback_guide"):
                guide_prompt = f"다음 문항들에 대해 전화 재조사를 실시할 때의 스크립트를 작성해줘.\n문항: {', '.join(target_callback_labels)}"
                res, err = run_analysis("전화조사 슈퍼바이저", guide_prompt, "스크립트 작성 중...")
                if not err: st.info(res)
            
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
        "AI 설문지 최적화",
        "AI 표본설계",
        "AI 이상치 검토 (Call Back, Data Adjustment)", 
        "AI 결측치 검토 (Call Back, Imputation)",
        "AI 단위 무응답 검토",
        "보고서 검수 AI Tools"
    ]
    
    # [v4.14] 화이트리스트 기반 권한 제어 - 'AI 단위 무응답 검토' 섹션
    # (shjeon, metrix11 아이디만 접근 허용, 비로그인 시 숨김)
    allowed_for_nonresponse = ["shjeon", "metrix11"]
    current_user = st.session_state.get("logged_in_user", "")
    
    if current_user not in allowed_for_nonresponse:
        if "AI 단위 무응답 검토" in menu_options:
            menu_options.remove("AI 단위 무응답 검토")
    
    # [v4.12] 관리자(shjeon) 전용 메뉴 추가
    if st.session_state.get("logged_in_user") == "shjeon":
        menu_options.append("⚙️ ADMIN DASHBOARD")
    
    # 세션 상태에 저장된 메뉴가 옵션에 없으면(예: 권한으로 숨겨짐) 기본값(첫 번째) 사용
    if "menu_selection" not in st.session_state or st.session_state["menu_selection"] not in menu_options:
        st.session_state["menu_selection"] = menu_options[0]
        
    try:
        current_idx = menu_options.index(st.session_state["menu_selection"])
    except (ValueError, KeyError):
        current_idx = 0

    menu = st.radio(
        "메뉴를 선택하세요",
        menu_options,
        index=current_idx,
        label_visibility="collapsed",
    )
    
    # [v4.12] 섹션 접근 로깅 및 상태 동기화
    if st.session_state["menu_selection"] != menu:
        st.session_state["menu_selection"] = menu
        tracker.log_event(st.session_state.get("logged_in_user", "unknown"), "ACCESS", menu)
        st.rerun()
    
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

    # [v4.17] 관리자 전용 시스템 도구 (shjeon에게만 노출)
    if st.session_state.get("logged_in_user") == "shjeon":
        # API 키 상태
        _keys = get_api_keys()
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

    # [v4.16] 무단 사용 금지 경고 문구 추가 (아이콘/띠 제외)
    st.markdown("""
    <div style="
        background-color: rgba(255, 245, 245, 0.1); 
        padding: 10px; 
        margin-top: 20px; 
        border-radius: 4px;
    ">
        <p style="
            color: #FC8181; 
            font-size: 0.72rem; 
            font-weight: 500; 
            line-height: 1.5; 
            margin: 0;
        ">
            본 솔루션은 회사의 지적 재산이며, 사전 허가 없는 무단 사용 및 배포는 엄격히 금지됩니다.
        </p>
    </div>
    """, unsafe_allow_html=True)



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
    elif st.session_state["menu_selection"] == "AI 설문지 최적화":
        show_questionnaire_optimization_system()
        st.stop()
    elif st.session_state["menu_selection"] == "AI 표본설계":
        show_sample_design_system()
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
    elif st.session_state["menu_selection"] == "⚙️ ADMIN DASHBOARD":
        if st.session_state.get("logged_in_user") == "shjeon":
            show_admin_dashboard()
        else:
            st.error("이 페이지에 대한 접근 권한이 없습니다.")
        st.stop()

    # [v4.2 추가] 메인 보고서 검수 가이드
    with st.expander("📘 AI 보고서 검수 서비스 이용 안내", expanded=False):
        st.markdown("""
        ### 🛠️ 이용 방법 안내
        1. **보고서 업로드:** 검수할 리서치 보고서(PDF, DOCX, TXT)를 업로드 영역에 드래그하거나 선택합니다.
        2. **분석 단계 수행:** 하단의 **STEP 1(요약)**, **STEP 2(검수)**, **STEP 3(종합)** 버튼을 순서대로 클릭하여 AI 분석을 생성합니다.
        3. **내용 확인 및 수정:** AI가 생성한 초안을 검토하고 필요한 경우 텍스트 상자에서 직접 수정합니다.
        4. **결과 다운로드:** 모든 분석이 완료되면 상단의 **'검수 결과 다운로드(Word)'** 버튼을 통해 최종 보고서를 저장합니다.
        """)

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
        if any(st.session_state["step_results"].values()) or st.session_state["full_result"]:
            show_security_notice()
            st.markdown("<hr>", unsafe_allow_html=True)
            
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

        # [v4.13 수정] 잘못된 조건부 호출 제거 (이 부분은 하단 다운로드 영역 전 공통 노출로 대체됨)
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
