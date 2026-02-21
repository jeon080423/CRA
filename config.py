"""앱 설정 상수"""

APP_TITLE = "수석 리서치 품질 검수관"
APP_ICON = "🔍"
APP_DESCRIPTION = "국가승인통계, 공공기관 만족도 조사, 정책 평가, 실태조사 및 여론조사 결과보고서 전문 AI 검수 시스템"

# ──────────────────────────────────────────────
# Gemini 모델 목록 (사용자가 수동 선택 가능한 전체 목록)
# ──────────────────────────────────────────────
AVAILABLE_MODELS = [
    "gemini-2.0-flash",                # Gemini 2.0 Flash (Stable)
    "gemini-2.5-flash",                # Gemini 2.5 Flash
    "gemini-2.0-pro-exp-02-05",        # Gemini 2.0 Pro Experimental
    "gemini-2.0-flash-lite",           # Gemini 2.0 Flash Lite (Fast)
]

# 모델 표시 이름 매핑
MODEL_DISPLAY_NAMES = {
    "gemini-2.0-flash":                 "Gemini 2.0 Flash (Stable)",
    "gemini-2.5-flash":                 "Gemini 2.5 Flash (Stable)",
    "gemini-2.0-pro-exp-02-05":         "Gemini 2.0 Pro (Experimental)",
    "gemini-2.0-flash-lite":            "Gemini 2.0 Flash Lite",
}

# ──────────────────────────────────────────────
# 자동 최적화 모드: 할당량 초과 시 순서대로 폴백
# ──────────────────────────────────────────────
AUTO_MODEL_PRIORITY = [
    "gemini-2.0-flash",                 # 1순위: 압도적 속도 및 안정성
    "gemini-2.0-pro-exp-02-05",         # 2순위: 최고 수준의 분석력 (실험적)
    "gemini-2.0-flash-lite",            # 3순위: 경량화된 고속 모델
]

# ──────────────────────────────────────────────
# 단계별 최적 모델 맵 (속도 vs 품질 밸런스)
# ──────────────────────────────────────────────
STEP_MODEL_MAP = {
    1: ["gemini-2.0-flash", "gemini-2.0-flash-lite"],
    2: ["gemini-2.0-flash", "gemini-2.0-pro-exp-02-05"], 
    3: ["gemini-2.0-pro-exp-02-05", "gemini-2.0-flash"], 
}


# 기본 모델 (수동 선택 시 초기값)
DEFAULT_MODEL = "gemini-2.0-flash"

# 자동 최적화 모드 레이블
AUTO_MODE_LABEL = "🤖 자동 최적화 (권장)"

# 생성 설정
GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 0.95,
    "max_output_tokens": 4096,   # 8192 → 4096: 속도 개선 (단계별 출력 충분)
}

# 세이프티 설정 (리서치 보고서 분석을 위해 차단 최소화)
# 주요 카테고리에 대해 필터링을 해제하여 안정적인 분석 보장
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# 파일 업로드 설정
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = ["pdf", "docx", "txt"]

# 텍스트 입력 제한
# 80,000자 제한을 풀고, 청킹(Chunking) 방식을 통해 물리적 한계 극복
MAX_TEXT_CHARS = 500_000

# ──────────────────────────────────────────────
# 정밀 분석을 위한 청킹 설정
# ──────────────────────────────────────────────
ANALYSIS_CHUNK_SIZE = 25_000  # 30,000 -> 25,000: 더 세밀하고 안정적인 검수 유도
CHUNK_OVERLAP = 3_000        # 조괄간 겹치는 구간 (문맥 유지 보강)

# 단계별 텍스트 사용 비율 (전체 텍스트 대비)
# 1단계(조사개요·표본설계)는 문서 앞부분에 집중 → 앞 40%만
# 2~3단계는 전체 필요
STEP_TEXT_RATIO = {
    1: (0.0, 0.4),   # 앞 40% (조사 설계)
    2: (0.0, 1.0),   # 전체 (정밀 검수 및 오류 식별)
    3: (0.0, 1.0),   # 전체 (종합 보고서)
}

# 할당량 초과 및 서버 오류 관련 에러 키워드 (폴백 트리거)
QUOTA_ERROR_KEYWORDS = [
    "quota", "rate limit", "429", "resource exhausted",
    "too many requests", "resourceexhausted",
    "500", "503", "overloaded", "deadline", "unavailable",
    "401", "403", "unauthorized", "api_key_invalid", "permission_denied", "invalid api key"
]
