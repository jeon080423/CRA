"""앱 설정 상수"""

APP_TITLE = "수석 리서치 품질 검수관"
APP_ICON = "🔍"
APP_DESCRIPTION = "국가승인통계, 공공기관 만족도 조사, 정책 평가, 실태조사 및 여론조사 결과보고서 전문 AI 검수 시스템"

# ──────────────────────────────────────────────
# Gemini 모델 목록 (사용자가 수동 선택 가능한 전체 목록)
# ──────────────────────────────────────────────
AVAILABLE_MODELS = [
    "gemini-2.5-pro-exp-03-25",        # Gemini 2.5 Pro (Exp)
    "gemini-2.5-flash-preview-04-17",  # Gemini 2.5 Flash
    "gemini-2.0-flash",                # Gemini 2.0 Flash
    "gemini-2.0-flash-exp",            # Gemini 2.0 Flash Exp
    "gemini-2.0-flash-thinking-exp-01-21",  # Gemini 2.0 Flash Thinking
    "gemini-2.0-pro-exp-02-05",        # Gemini 2.0 Pro Exp
    "gemini-1.5-pro",                  # Gemini 1.5 Pro (안정)
    "gemini-1.5-flash",                # Gemini 1.5 Flash (안정)
]

# 모델 표시 이름 매핑
MODEL_DISPLAY_NAMES = {
    "gemini-2.5-pro-exp-03-25":         "Gemini 2.5 Pro Exp",
    "gemini-2.5-flash-preview-04-17":   "Gemini 2.5 Flash",
    "gemini-2.0-flash":                 "Gemini 2.0 Flash",
    "gemini-2.0-flash-exp":             "Gemini 2.0 Flash Exp",
    "gemini-2.0-flash-thinking-exp-01-21": "Gemini 2.0 Flash Thinking",
    "gemini-2.0-pro-exp-02-05":         "Gemini 2.0 Pro Exp",
    "gemini-1.5-pro":                   "Gemini 1.5 Pro",
    "gemini-1.5-flash":                 "Gemini 1.5 Flash",
}

# ──────────────────────────────────────────────
# 자동 최적화 모드: 할당량 초과 시 순서대로 폴백
# 품질 우선 → 속도 fallback 순
# ──────────────────────────────────────────────
AUTO_MODEL_PRIORITY = [
    "gemini-2.5-pro-exp-03-25",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-2.0-pro-exp-02-05",
    "gemini-2.0-flash-thinking-exp-01-21",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

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

# 파일 업로드 설정
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = ["pdf", "docx", "txt"]

# 텍스트 입력 제한
# 한국어 보고서 100페이지 ≈ 40,000~60,000자 / 영어는 약 2배
# 80,000자 = 약 20,000~25,000 토큰 (한국어 기준)
MAX_TEXT_CHARS = 80_000

# 단계별 텍스트 사용 비율 (전체 텍스트 대비)
# 1단계(조사개요·표본설계)는 문서 앞부분에 집중 → 앞 40%만
# 2~4단계는 전체 필요
STEP_TEXT_RATIO = {
    1: (0.0, 0.4),   # 앞 40%
    2: (0.0, 1.0),   # 전체
    3: (0.0, 1.0),   # 전체
    4: (0.0, 1.0),   # 전체
}

# 할당량 초과 관련 에러 키워드 (폴백 트리거)
QUOTA_ERROR_KEYWORDS = [
    "quota", "rate limit", "429", "resource exhausted",
    "too many requests", "resourceexhausted",
]

