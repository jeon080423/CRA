"""
수석 리서치 품질 검수관 - 보고서 분석기
Streamlit Cloud 배포용 메인 앱
"""
import streamlit as st
import concurrent.futures
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
)

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
        "step_results": {1: "", 2: "", 3: "", 4: ""},
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

    # 모델 선택
    st.markdown('<div class="qx-section-label">AI MODEL</div>', unsafe_allow_html=True)
    auto_mode = st.toggle(
        "🤖 자동 최적화 (권장)",
        value=st.session_state["auto_mode"],
        help="할당량 초과 시 최적 모델로 자동 전환합니다. 우선순위: Gemini 2.5 Pro → 2.5 Flash → 2.0 Flash → ...",
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
    st.markdown('<div class="qx-section-label">FILE STATUS</div>', unsafe_allow_html=True)
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
        st.progress(step_done / 4, text=f"단계별 분석 {step_done}/4 완료")
    else:
        st.caption("파일을 업로드하면 현황이 표시됩니다.")

    st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("초기화", use_container_width=True):
        for k in ["report_text", "file_name", "full_result"]:
            st.session_state[k] = ""
        st.session_state["step_results"] = {1: "", 2: "", 3: "", 4: ""}
        st.session_state["file_pages"] = 0
        st.rerun()

    st.caption("Powered by Google Gemini · v1.0")


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
            <span style="color:#0F6CBD;font-weight:700;">01</span><span>\uc870\uc0ac \uc124\uacc4 \uc694\uc57d</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">02</span><span>\ubd80\ubb38\ubcc4 \uc815\ubc00 \uac80\uc218</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">03</span><span>5\ub300 \ud1b5\ud569 \uc624\ub958 \uae30\uc900 \uc810\uacb8</span>
        </div>
        <div style="display:flex;align-items:center;gap:0.6rem;font-size:0.875rem;color:#2D3A50;">
            <span style="color:#0F6CBD;font-weight:700;">04</span><span>\uc885\ud569 \uac80\uc218 \ubcf4\uace0\uc11c</span>
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
                    st.session_state["step_results"] = {1: "", 2: "", 3: "", 4: ""}
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
            run_full = st.button("⚡ 전체 4단계 병렬 분석", use_container_width=True, type="primary")
        with col_hint:
            st.markdown(
                '<span style="font-size:0.82rem;color:#8B96A9;">'
                '1~4단계를 <b>동시에</b> 병렬 실행합니다. 순차 실행 대비 최대 4배 빠릅니다.'
                '</span>',
                unsafe_allow_html=True,
            )

        if run_full:
            if not api_key:
                st.error("API 키가 설정되지 않았습니다. Streamlit Secrets에 GEMINI_API_KEYS를 추가하세요.")
            else:
                _auto = st.session_state["auto_mode"]
                _model = st.session_state["selected_model"]
                st.session_state["full_result"] = ""
                st.session_state["step_results"] = {1: "", 2: "", 3: "", 4: ""}

                progress_bar = st.progress(0, text="⚡ 4단계 병렬 분석 실시간 진행 중...")
                status_cols = st.columns(4)
                placeholders = {i+1: status_cols[i].empty() for i in range(4)}
                
                # \ucd08\uae30 \uc0c1\ud0dc \ud45c\uc2dc
                step_names = [
                    "\uc870\uc0ac \uc124\uacc4 \uc694\uc57d", 
                    "\ubd80\ubb38\ubcc4 \uac80\uc218", 
                    "\uc624\ub958 \uc2dd\ubca8", 
                    "\uc885\ud569 \ubcf4\uace0\uc11c"
                ]
                for i, name in enumerate(step_names, 1):
                    placeholders[i].markdown(f"**[{i}\ub2e8\uacc4]** {name}...")

                # 실시간 병렬 처리 실행
                results = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    from file_processor import slice_text_for_step
                    from config import STEP_TEXT_RATIO
                    
                    future_to_step = {
                        executor.submit(
                            _run_single, 
                            STEP_PROMPTS[s], 
                            slice_text_for_step(st.session_state["report_text"], s, STEP_TEXT_RATIO),
                            _model, 
                            _auto,
                            s  # 단계 번호 인자 추가
                        ): s for s in range(1, 5)
                    }

                    completed_count = 0
                    for future in concurrent.futures.as_completed(future_to_step):
                        step_num = future_to_step[future]
                        completed_count += 1
                        try:
                            text, err = future.result()
                            if err:
                                placeholders[step_num].error(f"❌ {step_num}단계 실패")
                                st.session_state["step_results"][step_num] = ""
                            else:
                                placeholders[step_num].success(f"✅ {step_num}단계 완료")
                                st.session_state["step_results"][step_num] = text
                            
                            progress_bar.progress(completed_count / 4, text=f"분석 진행률: {completed_count}/4 단계 완료")
                        except Exception as e:
                            placeholders[step_num].error(f"❌ {step_num}단계 오류")

                # 결과 취합
                combined = ""
                for s in range(1, 5):
                    if st.session_state["step_results"][s]:
                        combined += f"\n\n---\n\n## {STEP_LABELS[s]}\n\n{st.session_state['step_results'][s]}"
                
                st.session_state["full_result"] = combined
                if combined:
                    st.success("⚡ 전체 병렬 분석이 완료되었습니다!")
                    st.rerun()
                else:
                    st.error("분석 결과 생성에 실패했습니다.")

        st.markdown("<hr>", unsafe_allow_html=True)

        # 탭 분석 UI
        tab1, tab2, tab3, tab4 = st.tabs([
            STEP_LABELS[1], STEP_LABELS[2], STEP_LABELS[3], STEP_LABELS[4],
        ])

        def render_step_tab(tab, step_num: int):
            with tab:
                col_hd, col_st = st.columns([3, 1])
                with col_hd:
                    st.markdown(
                        f'<div class="qx-card-title">{STEP_LABELS[step_num]}</div>',
                        unsafe_allow_html=True,
                    )
                with col_st:
                    if st.session_state["step_results"][step_num]:
                        st.markdown('<span class="badge-ok">완료</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-warn">대기</span>', unsafe_allow_html=True)

                run_btn = st.button(
                    f"{step_num}단계 분석 실행",
                    key=f"btn_step_{step_num}",
                )
                result_area = st.empty()

                if st.session_state["full_result"] and not st.session_state["step_results"][step_num]:
                    result_area.info("전체 분석 결과를 참조하세요. 단계별 독립 분석을 원하면 위 버튼을 클릭하세요.")
                elif st.session_state["step_results"][step_num]:
                    result_area.markdown(st.session_state["step_results"][step_num])

                if run_btn:
                    if not get_api_keys():
                        st.error("API 키가 설정되지 않았습니다.")
                        return
                    _auto = st.session_state["auto_mode"]
                    _model = st.session_state["selected_model"]
                    with st.spinner(f"{step_num}단계 분석 중..."):
                        full_text = ""
                        for chunk, is_error, _ in run_analysis_stream(
                            STEP_PROMPTS[step_num],
                            st.session_state["report_text"],
                            model_name=_model,
                            auto_mode=_auto,
                        ):
                            if is_error:
                                st.error(chunk)
                                return
                            full_text += chunk
                            result_area.markdown(full_text)
                    st.session_state["step_results"][step_num] = full_text
                    st.rerun()

        render_step_tab(tab1, 1)
        render_step_tab(tab2, 2)
        render_step_tab(tab3, 3)
        render_step_tab(tab4, 4)

        # 다운로드
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="qx-section-label">DOWNLOAD RESULTS</div>', unsafe_allow_html=True)

        def build_full_report() -> str:
            fname = st.session_state.get("file_name", "보고서")
            parts = [f"# 수석 리서치 품질 검수 보고서\n\n**대상 파일:** {fname}\n\n---\n"]
            if st.session_state["full_result"]:
                parts.append("## 전체 4단계 종합 분석\n\n")
                parts.append(st.session_state["full_result"])
            else:
                for step in range(1, 5):
                    result = st.session_state["step_results"].get(step, "")
                    parts.append(f"\n---\n\n## {STEP_LABELS[step]}\n\n")
                    parts.append(result if result else "*아직 분석이 실행되지 않았습니다.*")
            return "\n".join(parts)

        col_dl1, col_dl2, _ = st.columns([1, 1, 2])
        report_md = build_full_report()
        base_name = st.session_state.get("file_name", "report").rsplit(".", 1)[0]

        with col_dl1:
            st.download_button(
                label="Markdown (.md)",
                data=report_md.encode("utf-8"),
                file_name=f"{base_name}_검수보고서.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_dl2:
            st.download_button(
                label="텍스트 (.txt)",
                data=report_md.encode("utf-8"),
                file_name=f"{base_name}_검수보고서.txt",
                mime="text/plain",
                use_container_width=True,
            )

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
