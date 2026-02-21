"""
수석 리서치 품질 검수관 - 보고서 분석기
Streamlit Cloud 배포용 메인 앱
"""
import streamlit as st
import concurrent.futures
import datetime
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
import io
try:
    from docx import Document
    from docx.shared import Pt
except ImportError:
    Document = None

# ── 페이지 설정
st.set_page_config(
    page_title="Research Auditor · 보고서 분석기",
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

hr { border-color: #E5E9F0 !important; margin: 1rem 0 !important; }
[data-testid="stAlert"] { border-radius: 8px !important; font-size: 0.875rem !important; }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
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


# ── 사이드바
with st.sidebar:
    st.markdown("### Research Auditor")
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
                    st.success(f"진단 완료: 총 {len(results)}개 조합 중 {ok_count}개 정상")
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
        # 표시 이름 목록 생성
        display_options = [MODEL_DISPLAY_NAMES.get(m, m) for m in AVAILABLE_MODELS]
        display_default = MODEL_DISPLAY_NAMES.get(DEFAULT_MODEL, DEFAULT_MODEL)
        selected_display = st.selectbox(
            "모델 선택",
            display_options,
            index=display_options.index(display_default),
            label_visibility="collapsed",
        )
        # 표시 이름 → 실제 모델 ID 역매핑
        reverse_map = {v: k for k, v in MODEL_DISPLAY_NAMES.items()}
        selected_model = reverse_map.get(selected_display, DEFAULT_MODEL)
        st.session_state["selected_model"] = selected_model
        st.caption(f"`{selected_model}`")

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
        for k in ["report_text", "file_name", "full_result"]:
            st.session_state[k] = ""
        st.session_state["step_results"] = {1: "", 2: "", 3: ""}
        st.session_state["file_pages"] = 0
        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    st.caption("개발: ㅈㅅㅎ")
    st.caption("문의: jeon080423@gmail.com")
    st.caption("Powered by Google Gemini · v2.9")


# ── 로그인 가드
if not st.session_state["is_logged_in"]:
    st.markdown("""
<div class="qx-topbar">
    <span class="qx-topbar-logo">Research Auditor</span>
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
    # 상단 헤더 바
    st.markdown("""
<div class="qx-topbar">
    <span class="qx-topbar-logo">Research Auditor</span>
    <span class="qx-topbar-sep"></span>
    <span class="qx-topbar-title">수석 리서치 품질 검수관</span>
    <span class="qx-topbar-badge">AI-Powered Quality Check</span>
</div>
""", unsafe_allow_html=True)

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

            for line in lines:
                line_strip = line.strip()
                
                # 표 행 감지 (| 로 시작하거나 포함된 경우)
                if '|' in line_strip:
                    # 구분선 (|---|) 인 경우 무시
                    if re.match(r'^[|\s\-:]+$', line_strip):
                        continue
                    # 데이터 행 추출
                    parts = [p.strip() for p in line_strip.split('|') if p.strip()]
                    if parts:
                        table_buffer.append(parts)
                        continue
                
                # 표가 끝나면 출력
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
                    def add_formatted_text(paragraph, text):
                        """정규표현식을 사용하여 마크다운 볼드(**)와 span 태그 처리"""
                        # 1. 빨간색 강조(<span...>)와 볼드(**...**)를 식별하기 위한 정규식
                        # 순서: span 태그 우선 감지 후 일반 볼드 감지
                        pattern = r"(<span style='color:red'>.*?</span>|\*\*.*?\*\*)"
                        parts = re.split(pattern, text)
                        
                        for part in parts:
                            if part.startswith("<span style='color:red'>"):
                                inner = re.sub(r"<span style='color:red'>(.*?)</span>", r"\1", part)
                                # 내부의 ** 제거 (중첩 처리)
                                inner = inner.replace("**", "")
                                run = paragraph.add_run(inner)
                                run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
                                run.bold = True
                            elif part.startswith("**") and part.endswith("**"):
                                inner = part[2:-2]
                                run = paragraph.add_run(inner)
                                run.bold = True
                            else:
                                if part:
                                    paragraph.add_run(part)

                    if is_bullet:
                        p = doc.add_paragraph(style='List Bullet')
                    else:
                        p = doc.add_paragraph()
                    
                    add_formatted_text(p, text_content)
            
            # 마지막 남은 표 출력
            flush_table()
            
            bio = io.BytesIO()
            doc.save(bio)
            bio.seek(0)
            return bio

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

# Last forced sync: 2026-02-21 05:25:30
