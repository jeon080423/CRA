import pandas as pd
import numpy as np

class CodebookParser:
    """코드북 엑셀 파싱 및 데이터 매핑 엔진 (v4.6)"""
    
    def __init__(self, codebook_file):
        self.raw_cb = codebook_file
        self.var_map = {}   # { '변수명': { 'no': '문번호', 'desc': '변수설명' } }
        self.code_map = {}  # { '변수명': { 1: '남성', 2: '여성', ... } }
        self._parse()

    def _parse(self):
        try:
            # 1. 변수설명 시트 파싱
            df_var = pd.read_excel(self.raw_cb, sheet_name=0) 
            # 칼럼명 정형화 (공백 제거 등)
            df_var.columns = [str(c).strip() for c in df_var.columns]
            
            # 예상 칼럼: '문번호', '변수명', '변수설명'
            for _, row in df_var.iterrows():
                val_name = str(row.get('변수명', '')).strip()
                if val_name and val_name != 'nan':
                    self.var_map[val_name] = {
                        'no': str(row.get('문번호', '')).strip(),
                        'desc': str(row.get('변수설명', '')).strip()
                    }

            # 2. 코드표 시트 파싱
            df_code = pd.read_excel(self.raw_cb, sheet_name=1)
            df_code.columns = [str(c).strip() for c in df_code.columns]
            
            # 예상 칼럼: '변수명', '코드', '변수값'
            current_var = None
            for _, row in df_code.iterrows():
                var_name = str(row.get('변수명', '')).strip()
                if var_name and var_name != 'nan':
                    current_var = var_name
                
                if current_var:
                    if current_var not in self.code_map:
                        self.code_map[current_var] = {}
                    
                    code_val = row.get('코드')
                    label_val = str(row.get('변수값', '')).strip()
                    
                    if pd.notna(code_val) and label_val:
                        # 숫자인 경우 정수형으로 저장 시도
                        try:
                            if float(code_val) == int(code_val):
                                code_val = int(code_val)
                        except:
                            pass
                        self.code_map[current_var][code_val] = label_val
        except Exception as e:
            print(f"Codebook Parsing Error: {e}")

    def get_var_label(self, var_name):
        """변수명 -> [문번호] 변수설명 형식으로 반환"""
        info = self.var_map.get(var_name)
        if info:
            no = info['no']
            desc = info['desc']
            if no != 'nan' and no:
                return f"[{no}] {desc if desc != 'nan' else var_name}"
            return desc if desc != 'nan' else var_name
        return var_name

    def get_value_label(self, var_name, value):
        """특정 변수의 코드값 -> 라벨 텍스트 반환"""
        v_map = self.code_map.get(var_name)
        if v_map:
            # 다양한 타입 지원 (int, float, str)
            return v_map.get(value, v_map.get(str(value), v_map.get(float(value) if isinstance(value, (int, float, str)) else None, value)))
        return value

    def get_all_var_labels(self, columns):
        """데이터프레임 칼럼 리스트를 라벨 리스트로 변환 (Selectbox용)"""
        return [self.get_var_label(col) for col in columns]
    
    def get_column_from_label(self, label):
        """라벨 텍스트로부터 원래의 변수명(ID) 추출"""
        for var_name, info in self.var_map.items():
            if self.get_var_label(var_name) == label:
                return var_name
        return label
