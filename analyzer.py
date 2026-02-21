"""
Gemini API 분석 모듈
- 다중 API 키(GEMINI_API_KEYS) 랜덤 선택
- 자동 최적화 모드: 할당량 초과 시 AUTO_MODEL_PRIORITY 순서로 모델 순차 전환
- 병렬 실행: 3단계를 ThreadPoolExecutor로 동시 처리
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
    FULL_ANALYSIS_PROMPT,
    STEP1_SYNTHESIS_PROMPT,
    STEP2_SYNTHESIS_PROMPT,
    STEP3_SYNTHESIS_PROMPT,
)

# genai.configure()는 전역 상태 — 초기화 시 직렬화 필요
_genai_lock = threading.Lock()


def get_api_keys() -> list[str]:
    """Streamlit Cloud secrets에서 Gemini API 키 목록을 가져와 정제된 문자열 리스트로 반환"""
    try:
        raw = st.secrets.get("GEMINI_API_KEYS") or st.secrets.get("GEMINI_API_KEY")
        if not raw:
            return []
            
        # 1. 단일 문자열인 경우 (쉼표 분리)
        if isinstance(raw, str):
            return [k.strip() for k in raw.split(",") if k.strip()]
            
        # 2. 리스트나 튜플인 경우
        final_keys = []
        if isinstance(raw, (list, tuple)):
            for item in raw:
                if isinstance(item, (list, tuple)): # 중첩 리스트 대응
                    final_keys.extend([str(x).strip() for x in item if x])
                else:
                    final_keys.append(str(item).strip())
        else:
            # 기타 반복 가능한 객체 (SecretList 등) 대응
            try:
                final_keys = [str(k).strip() for k in raw if k]
            except Exception:
                final_keys = [str(raw).strip()]
        
        return [k for k in final_keys if k]
    except Exception as e:
        print(f"[ERROR] [API_KEYS_FETCH] {e}", flush=True)
        return []


def get_api_key() -> str | None:
    """API 키 목록에서 하나를 선택하여 반드시 문자열로 반환합니다."""
    keys = get_api_keys()
    if not keys:
        return None
    key = random.choice(keys)
    # 최종 결과물도 리스트일 경우 첫 번째 요소 선택 (이중 방어)
    if isinstance(key, (list, tuple)):
        key = key[0] if key else None
    return str(key).strip() if key else None


def _is_quota_error(error: Exception) -> bool:
    """할당량·레이트리밋 관련 에러인지 확인합니다."""
    err_str = str(error).lower()
    return any(kw in err_str for kw in config.QUOTA_ERROR_KEYWORDS)


# 전역 설정 중용 변수 (스레드 안전)
_last_configured_key = None
_config_lock = threading.Lock()

def _make_model(api_key: str, model_name: str):
    """Gemini 모델 인스턴스 생성 (API v1 및 세이프티 해제 적용)."""
    global _last_configured_key
    
    # 타입 안전성 확보
    if isinstance(api_key, (list, tuple)):
        api_key = str(api_key[0]).strip() if api_key else ""
    else:
        api_key = str(api_key).strip()
        
    try:
        # API 설정 부분만 락을 걸어 경합 최소화
        with _config_lock:
            if _last_configured_key != api_key:
                print(f"[DEBUG] [API_CONFIG] Key rotate -> {api_key[:8]}...", flush=True)
                genai.configure(api_key=api_key)
                _last_configured_key = api_key
        
        # 모델 생성 (세이프티 필터 BLOCK_NONE 적용)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
            generation_config=config.GENERATION_CONFIG,
            safety_settings=config.SAFETY_SETTINGS,
        )
        return model
    except Exception as e:
        print(f"[ERROR] [MODEL_INIT] {e}", flush=True)
        raise


def init_model(model_name: str = None, api_key: str | None = None):
    """Gemini 모델 초기화"""
    if model_name is None:
        model_name = config.DEFAULT_MODEL
    
    # API 키 취득 (문자열 보장)
    if api_key is None:
        api_key = get_api_key()
        
    if not api_key:
        return None, "❌ API 키를 찾을 수 없습니다."
    
    try:
        model = _make_model(api_key, model_name)
        return model, None
    except Exception as e:
        return None, f"❌ 모델 초기화 오류: {e}"


def _sanitize_text(text: str) -> str:
    """텍스트 정밀 정제 (유니코드 및 제어 문자 제거)"""
    import unicodedata
    if not text:
        return ""
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\r\t")
    return unicodedata.normalize("NFC", text)


def _resolve_text(response) -> str:
    """Gemini 응답 객체에서 텍스트를 안전하게 추출합니다 (상세 로깅 포함)."""
    try:
        # 1. 정상 텍스트 추출 시도
        if hasattr(response, "text"):
            return response.text
        
        # 2. 차단 사유 정밀 분석 (Candidates가 있을 때)
        if hasattr(response, "candidates") and response.candidates:
            cand = response.candidates[0]
            reason = cand.finish_reason
            
            # 차단된 경우 상세 정보 로깅 (콘솔 확인용)
            ratings = getattr(cand, "safety_ratings", "No ratings")
            print(f"[WARN] [BLOCKED] Candidate Blocked. Reason: {reason}, Ratings: {ratings}", flush=True)
            return f"[데이터 보호 정책에 의해 차단됨 (사유: {reason})]"
        
        # 3. 프롬프트 자체가 거부된 경우 (Prompt Feedback)
        if hasattr(response, "prompt_feedback"):
            print(f"[WARN] [REJECTED] Prompt Rejected. Feedback: {response.prompt_feedback}", flush=True)
            return "[입력 데이터가 정책에 의해 거부되었습니다.]"

        return "[응답 결과가 비어 있습니다.]"
    except Exception as e:
        # 응답 처리 중 발생하는 특수한 에러 핸들링
        err_msg = str(e)
        if "Quickly" in err_msg or "blocked" in err_msg.lower():
            print(f"[WARN] [SAFE_BLOCK] Content blocked by inner filter: {err_msg}", flush=True)
            return "[정책에 의해 응답이 차단되었습니다.]"
        print(f"[ERROR] [TEXT_RES] {e}", flush=True)
        return f"[응답 처리 중 오류 발생: {str(e)}]"


def _run_single(prompt_template: str, report_text: str, model_name: str, auto_mode: bool, step_num: int = 0, api_key: str = None) -> tuple[str, str | None]:
    """단일 프롬프트를 비스트리밍으로 실행 (속도/안정성 균형)."""
    import time
    
    # 텍스트 정제
    clean_text = _sanitize_text(report_text)
    prompt = prompt_template.replace("{report_text}", clean_text)
    
    if auto_mode:
        candidates = config.STEP_MODEL_MAP.get(step_num, config.AUTO_MODEL_PRIORITY)
    else:
        candidates = [model_name if model_name else config.DEFAULT_MODEL]

    # 초기 키 선택: 외부에서 주입되지 않았다면 랜덤하게 하나 선택
    current_api_key = api_key if api_key else get_api_key()

    for candidate in candidates:
        # 모델별 최대 키 전환 시도 횟수 (6개 키가 있으므로 충분히 기회 부여)
        for key_retry in range(3): 
            # 무리한 호출 방지를 위해 약간의 지연 시간 도입
            time.sleep(0.5)
            
            print(f"[PROCESS] [STEP {step_num}] Requesting -> {candidate} (Key: {current_api_key[:8] if current_api_key else 'None'}...)", flush=True)
            model, init_err = init_model(candidate, api_key=current_api_key)
            if init_err:
                # 초기화 실패 시 즉시 키 교체 시도
                current_api_key = get_api_key()
                continue
                
            try:
                # 타임아웃 120초로 여유 있게 설정
                response = model.generate_content(
                    prompt, 
                    request_options={"timeout": 120}
                )
                text = _resolve_text(response)
                
                if text and not text.startswith("["):
                    return text, None
                elif text and text.startswith("["):
                    # 정책 차단 등 안내 메시지인 경우, 이를 실패가 아닌 '결과값'으로 인정하여 분석 지속
                    print(f"[INFO] [STEP {step_num}] Policy/System message received: {text}", flush=True)
                    return text, None
                else:
                    print(f"[WARN] [STEP {step_num}] Empty response from {candidate}", flush=True)
                    break # 다음 모델 시도
                    
            except Exception as e:
                err_msg = str(e).lower()
                print(f"[ERROR] [STEP {step_num}] API Error ({candidate}): {err_msg}", flush=True)
                
                # 할당량 초과(Quota Error)인 경우 키를 즉시 교체하고 재시도
                if _is_quota_error(e):
                    new_key = get_api_key()
                    print(f"[INFO] [STEP {step_num}] Quota hit for {candidate}. Rotating key: {current_api_key[:8]} -> {new_key[:8]}", flush=True)
                    current_api_key = new_key
                    continue  # 동일 모델에 대해 새 키로 재시도
                
                # 서버 오류(500, 503)나 타임아웃, 404 등은 다음 후보 모델로 전환
                should_jump_model = (
                    "500" in err_msg or 
                    "503" in err_msg or 
                    "timeout" in err_msg or
                    "404" in err_msg or
                    "not found" in err_msg or
                    "overloaded" in err_msg
                )
                
                if should_jump_model:
                    print(f"[INFO] [STEP {step_num}] Jumping to next model due to server/path error...", flush=True)
                    break # 내부 키 루프 탈출 -> 다음 candidate 모델 시도
                
                return "", f"❌ 분석 오류 ({candidate}): {e}"

    return "", "❌ 모든 가용 모델 및 API 키가 응답하지 않거나 정책에 의해 차단되었습니다."


def run_step_with_chunks(
    step_num: int,
    text: str,
    prompt_template: str,
    model_name: str = None,
    auto_mode: bool = True,
    progress_callback: callable = None,
) -> tuple[str, str | None]:
    """단일 단계를 텍스트 청크 단위로 나누어 병렬 분석합니다. (API 키 경합 방지 로직 포함)"""
    from file_processor import create_chunks
    
    # 1. 텍스트를 세부 청크로 분할
    chunks = create_chunks(text, config.ANALYSIS_CHUNK_SIZE, config.CHUNK_OVERLAP)
    total_chunks = len(chunks)
    
    if not chunks:
        return "", "분석할 텍스트가 없습니다."

    # 2. 결과 저장을 위한 변수 초기화 (NameError 방지 및 상태 추적)
    chunk_results = [None] * total_chunks
    errors = []
    completed_chunks = [0]

    # 3. 각 조각별 병렬 분석 (안정성을 위해 max_workers=2로 조정)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_to_chunk = {
            executor.submit(_run_single, prompt_template, chunk, model_name, auto_mode, step_num, None): i
            for i, chunk in enumerate(chunks)
        }
        
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk_idx = future_to_chunk[future]
            completed_chunks[0] += 1
            
            if progress_callback:
                progress_callback(completed_chunks[0], total_chunks)
                
            try:
                res_text, res_err = future.result()
                if res_err:
                    errors.append(f"조각 {chunk_idx+1}: {res_err}")
                else:
                    chunk_results[chunk_idx] = res_text
            except Exception as e:
                errors.append(f"조각 {chunk_idx+1} 치명적 오류: {e}")
    
    # 4. 결과 통합 및 Synthesis (v12.0)
    # 모든 부문에 대해 여러 조각의 결과를 하나로 병합하여 중복 제거
    if len(chunk_results) > 1:
        print(f"[PROCESS] [STEP {step_num}] Synthesizing {len(chunk_results)} results into one...", flush=True)
        
        # 단계별 병합 프롬프트 매핑 (v13.0: 3단계 체제)
        synth_prompts = {
            1: STEP1_SYNTHESIS_PROMPT,
            2: STEP2_SYNTHESIS_PROMPT,
            3: STEP3_SYNTHESIS_PROMPT
        }
        synthesis_prompt_template = synth_prompts.get(step_num)
        
        if synthesis_prompt_template:
            # 모든 조각 결과 취합
            all_results_text = "\n\n".join([f"--- 조각 {i+1} ---\n{res}" for i, res in enumerate(chunk_results) if res])
            
            # 하이브리드 전략: 병합(Synthesis)은 고성능 모델(Pro)을 가급적 사용
            # 하지만 2단계 병합 시에만 Pro를 강제하고 나머지는 유연하게 적용
            synth_model = "gemini-2.5-pro" if step_num == 2 else model_name
            
            synthesis_text, synth_err = _run_single(
                synthesis_prompt_template.replace("{chunk_results}", all_results_text),
                "", 
                synth_model, # Synthesis 전용 모델 적용
                auto_mode,
                step_num,
                None
            )
            
            if not synth_err:
                combined_text = synthesis_text
            else:
                # 병합 실패 시 기존 방식(단순 나열) 유지하여 데이터 손실 방지
                combined_text = "\n\n---\n\n".join(filter(None, chunk_results))
        else:
            combined_text = "\n\n---\n\n".join(filter(None, chunk_results))
    # 5. 내결함성(Fault Tolerance): 성공한 조각이 하나라도 있으면 결과 반환
    if not any(chunk_results):
        return "", f"❌ 모든 조각 분석 실패: {'; '.join(errors[:3])}"
        
    final_err = "; ".join(errors) if errors else None
    return combined_text, final_err


def run_parallel_steps(
    report_text: str,
    model_name: str = None,
    auto_mode: bool = True,
    steps: list[int] | None = None,
) -> dict[int, tuple[str, str | None]]:
    """지정한 단계들을 청크 단위로 분석 (순차 처리 권장 - 안정성용)."""
    if steps is None:
        steps = [1, 2, 3]

    from file_processor import slice_text_for_step
    step_prompts = {1: STEP1_PROMPT, 2: STEP2_PROMPT, 3: STEP3_PROMPT}
    results = {}

    for s in steps:
        target_text = slice_text_for_step(report_text, s, config.STEP_TEXT_RATIO)
        # 각 단계를 개별적으로 분석 (내부적으로 청크 병렬 처리)
        results[s] = run_step_with_chunks(s, target_text, step_prompts[s], model_name, auto_mode)

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
    # format() 대신 replace() 사용: 보고서 내의 { } 중괄호로 인한 KeyError 방지
    prompt = prompt_template.replace("{report_text}", report_text)
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
}

STEP_LABELS = {
    1: "[1단계] 조사 설계 및 요약",
    2: "[2단계] 부문별 정밀 검수 및 오류 식별",
    3: "[3단계] 종합 검수 보고서",
}
