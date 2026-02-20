"""
Gemini API 분석 모듈
- 다중 API 키(GEMINI_API_KEYS) 랜덤 선택
- 자동 최적화 모드: 할당량 초과 시 AUTO_MODEL_PRIORITY 순서로 모델 순차 전환
- 병렬 실행: 4단계를 ThreadPoolExecutor로 동시 처리
- 토큰 절약: 단계별 텍스트 슬라이스 적용
"""
import random
import concurrent.futures
import threading
import streamlit as st
import google.generativeai as genai

# ──────────────────────────────────────────────
# 설정 및 상수를 config 모듈에서 직접 참조
# ──────────────────────────────────────────────
import config
from file_processor import slice_text_for_step
from prompts import (
    SYSTEM_PROMPT,
    STEP1_PROMPT,
    STEP2_PROMPT,
    STEP3_PROMPT,
    STEP4_PROMPT,
    FULL_ANALYSIS_PROMPT,
)

# genai.configure()는 전역 상태 — 초기화 시 직렬화 필요
_genai_lock = threading.Lock()


def get_api_keys() -> list[str]:
    """Streamlit Cloud secrets에서 Gemini API 키 목록을 가져옵니다."""
    try:
        keys = st.secrets["GEMINI_API_KEYS"]
        if isinstance(keys, str):
            keys = [k.strip() for k in keys.split(",") if k.strip()]
        return [k for k in keys if k]
    except (KeyError, AttributeError, FileNotFoundError):
        pass
    try:
        key = st.secrets["GEMINI_API_KEY"]
        if key:
            return [key]
    except (KeyError, AttributeError, FileNotFoundError):
        pass
    return []


def get_api_key() -> str | None:
    """API 키 목록에서 랜덤으로 하나 선택해 반환합니다."""
    keys = get_api_keys()
    return random.choice(keys) if keys else None


def _is_quota_error(error: Exception) -> bool:
    """할당량·레이트리밋 관련 에러인지 확인합니다."""
    err_str = str(error).lower()
    return any(kw in err_str for kw in config.QUOTA_ERROR_KEYWORDS)


def _make_model(api_key: str, model_name: str):
    """스레드 안전한 Gemini 모델 인스턴스 생성."""
    with _genai_lock:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
            generation_config=config.GENERATION_CONFIG,
        )
    return model


def init_model(model_name: str = None, api_key: str | None = None):
    """Gemini 모델 초기화 (스레드 안전)"""
    if model_name is None:
        model_name = config.DEFAULT_MODEL
    if api_key is None:
        api_key = get_api_key()
    if not api_key:
        return None, "❌ API 키를 찾을 수 없습니다."
    try:
        model = _make_model(api_key, model_name)
        return model, None
    except Exception as e:
        return None, f"❌ 모델 초기화 오류: {e}"


def _run_single(prompt_template: str, report_text: str, model_name: str, auto_mode: bool, step_num: int = 0) -> tuple[str, str | None]:
    """단일 프롬프트를 비스트리밍으로 실행 (병렬 호출용 내부 함수)."""
    prompt = prompt_template.format(report_text=report_text)
    
    if auto_mode:
        candidates = config.STEP_MODEL_MAP.get(step_num, config.AUTO_MODEL_PRIORITY)
    else:
        candidates = [model_name if model_name else config.DEFAULT_MODEL]

    for candidate in candidates:
        model, init_err = init_model(candidate)
        if init_err:
            continue
        try:
            response = model.generate_content(prompt)
            return response.text, None
        except Exception as e:
            if _is_quota_error(e):
                continue
            return "", f"❌ 분석 오류 ({candidate}): {e}"

    return "", "❌ 모든 모델의 할당량이 초과되었습니다."


def run_parallel_steps(
    report_text: str,
    model_name: str = None,
    auto_mode: bool = True,
    steps: list[int] | None = None,
) -> dict[int, tuple[str, str | None]]:
    """지정한 단계를 병렬 실행."""
    if model_name is None:
        model_name = config.DEFAULT_MODEL
    if steps is None:
        steps = [1, 2, 3, 4]

    step_prompts = {1: STEP1_PROMPT, 2: STEP2_PROMPT, 3: STEP3_PROMPT, 4: STEP4_PROMPT}

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(steps)) as executor:
        future_map = {
            executor.submit(
                _run_single,
                step_prompts[s],
                slice_text_for_step(report_text, s, config.STEP_TEXT_RATIO),
                model_name,
                auto_mode,
                s
            ): s
            for s in steps
        }
        for future in concurrent.futures.as_completed(future_map):
            step = future_map[future]
            try:
                results[step] = future.result()
            except Exception as e:
                results[step] = ("", f"❌ 실행 오류: {e}")

    return results


def run_analysis_stream(
    prompt_template: str,
    report_text: str,
    model_name: str = None,
    auto_mode: bool = False,
):
    """스트리밍 방식으로 분석 실행."""
    if model_name is None:
        model_name = config.DEFAULT_MODEL
    prompt = prompt_template.format(report_text=report_text)
    candidates = config.AUTO_MODEL_PRIORITY if auto_mode else [model_name]

    last_error = None
    for candidate in candidates:
        model, init_err = init_model(candidate)
        if init_err:
            last_error = init_err
            continue
        try:
            response = model.generate_content(prompt, stream=True)
            yield f"\n\n> 🤖 **사용 모델:** `{candidate}`\n\n", False, candidate
            for chunk in response:
                if chunk.text:
                    yield chunk.text, False, candidate
            return
        except Exception as e:
            if _is_quota_error(e):
                last_error = f"⚠️ `{candidate}` 할당량 초과 — 다음 모델로 전환 중..."
                yield last_error + "\n\n", False, candidate
                continue
            else:
                yield f"❌ 분석 오류 ({candidate}): {e}", True, candidate
                return

    yield f"❌ 모든 모델의 할당량이 초과되었습니다.\n마지막 오류: {last_error}", True, ""


def run_analysis(
    prompt_template: str,
    report_text: str,
    model_name: str = None,
    auto_mode: bool = False,
) -> tuple[str, str | None]:
    """비스트리밍 분석 실행."""
    if model_name is None:
        model_name = config.DEFAULT_MODEL
    text, err = _run_single(prompt_template, report_text, model_name, auto_mode)
    return text, err


STEP_PROMPTS = {
    1: STEP1_PROMPT,
    2: STEP2_PROMPT,
    3: STEP3_PROMPT,
    4: STEP4_PROMPT,
}

STEP_LABELS = {
    1: "[1\ub2e8\uacc4] \uc870\uc0ac \uc124\uacc4 \uc694\uc57d",
    2: "[2\ub2e8\uacc4] \ubd80\ubb38\ubcc4 \uc815\ubc00 \uac80\uc218",
    3: "[3\ub2e8\uacc4] \uc624\ub958 \uc2dd\ubca8",
    4: "[4\ub2e8\uacc4] \uc885\ud569 \uac80\uc218 \ubcf4\uace0\uc11c",
}
