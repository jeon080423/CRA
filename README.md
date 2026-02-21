# 🔍 수석 리서치 품질 검수관 - 보고서 분석기

국가승인통계, 공공기관 만족도 조사, 정책 평가, 실태조사 및 여론조사 결과 보고서를 AI가 전문적으로 감수하는 **Streamlit 기반 분석 시스템**입니다.

## 주요 기능

| 단계 | 기능 |
|------|------|
| 📋 1단계 | 조사 설계 요약 (조사명, 목적, 대상, 표본 등 마크다운 표 자동 추출) |
| 🔍 2단계 | 부문별 정밀 검수 및 오류 식별 (오타/비문, 수리적, 통계, 시각화 왜곡 등) |
| 📄 3단계 | 종합 검수 보고서 (총평 + 오류 현황 요약표 + 수정 권고 및 개선 제언) |

## 지원 파일 형식

- **PDF** (.pdf) — 페이지 번호 자동 태그
- **Word** (.docx)
- **텍스트** (.txt)

## 설치 및 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 배포

### Secrets 설정

Streamlit Cloud 대시보드 → 앱 메뉴 → **Settings → Secrets**에 추가:

```toml
GEMINI_API_KEY = "your-gemini-api-key-here"
```

> API 키는 [Google AI Studio](https://aistudio.google.com)에서 발급받으세요.

## 파일 구조

```
1.보고서 분석기/
├── app.py              # Streamlit 메인 앱
├── prompts.py          # 시스템 프롬프트 모음
├── analyzer.py         # Gemini API 호출 로직
├── file_processor.py   # PDF/DOCX/TXT 텍스트 추출
├── config.py           # 앱 설정 상수
├── requirements.txt    # 패키지 의존성
└── README.md
```
