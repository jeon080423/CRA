import re

def sanitize_spaces(text):
    """Replaces non-breaking spaces and other artifacts with standard spaces."""
    if not text: return text
    return text.replace('\xa0', ' ').replace('\u200b', '').replace('\uFEFF', '').strip()

def detect_project_name(text):
    """Attempts to extract the project name from the first page of the RFP with robust logic."""
    if not text: return "미지정 사업"
    
    text = sanitize_spaces(text)
    header_text = text[:3000]
    lines = [l.strip() for l in header_text.split('\n') if l.strip()]
    
    cover_lines = lines[:30] 
    for i, line in enumerate(cover_lines):
        clean_line = re.sub(r'\s+', '', line)
        if any(line.endswith(suffix) or line.endswith(suffix + "서") for suffix in ["사업", "용역", "조사", "구축", "개발", "계획", "건"]):
            if clean_line in ["제안요청서", "과업지시서", "과업내용서", "입찰공고"]:
                continue
            if len(line) > 5 and not re.search(r'^\d{4}\.', line):
                return line

    for i, line in enumerate(cover_lines):
        if "제안요청서" in line or "과업지시서" in line:
            if i > 0:
                prev_line = cover_lines[i-1]
                if len(prev_line) > 5 and not any(x in prev_line for x in ["공고", "제출", "안내"]):
                    return prev_line
    
    keywords = ["과제명", "사업명", "조사명", "용역명", "프로젝트명", "공고명"]
    for line in lines:
        for kw in keywords:
            pattern = rf'^(?:[0-9가-힣\d\.]+\s*)?{kw}\s*[:：\s\]\)]'
            if re.search(pattern, line):
                if ':' in line: 
                    name = line.split(':', 1)[1].strip()
                    if len(name) > 3: return name
                elif '：' in line:
                    name = line.split('：', 1)[1].strip()
                    if len(name) > 3: return name
                
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    next_line = lines[idx+1].strip()
                    if len(next_line) > 3: return next_line
    
    for line in lines[:20]:
        if re.search(r'\.{3,}|\d+\s*$', line) or "..." in line: continue
        if any(x in line for x in ["주소", "일시", "일자", "연락처", "목차", "CONTENTS", "사업 개요", "과업 지시서", "제안요청서", "과업지시서"]): continue
        if 10 < len(line) < 100:
            if not re.match(r'^[-\*\(]', line):
                return sanitize_spaces(line)
    
    return "미지정 사업"

def detect_year(text, default_label):
    """Attempts to detect the year from the text (e.g., '2024년')."""
    if not text: return default_label
    match = re.search(r'20\d{2}년', text[:3000])
    if match:
        return match.group(0)
    return default_label

def get_balanced_context(text, max_chars=20000):
    if not text: return ""
    if len(text) <= max_chars: return text
    half = max_chars // 2
    return text[:half] + "\n\n... (중략) ...\n\n" + text[-half:]
