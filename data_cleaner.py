import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer
from sklearn.linear_model import LinearRegression
import io

class DataImputer:
    """통계적 데이터 보완 및 이상치 처리 엔진"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.audit_log = [] # (Variable, CaseID, Old, New, Method)
        
    def impute_grand_mean(self, column: str, target_indices: list):
        """전체 평균 대체"""
        mean_val = self.df[column].mean()
        self._apply_imputation(column, target_indices, mean_val, "전체 평균 대체")
        
    def impute_stratified_mean(self, column: str, target_indices: list, strata_columns: list):
        """층별 대응 평균 대체 (서울 20대 등)"""
        # 층별 그룹화 후 평균 계산
        grouped = self.df.groupby(strata_columns)[column].transform('mean')
        
        # 만약 해당 층의 사례수가 적어 NaN이 나오면 전체 평균으로 포백
        grand_mean = self.df[column].mean()
        fill_values = grouped.fillna(grand_mean)
        
        for idx in target_indices:
            new_val = fill_values.loc[idx]
            self._apply_imputation(column, [idx], new_val, f"층별 평균 대체({', '.join(strata_columns)})")

    def impute_knn(self, column: str, target_indices: list, k=5):
        """k-NN (최근접 이웃) 대체"""
        # 수치형 변수만 사용하여 거리 계산 (간단 구현 버전)
        numeric_df = self.df.select_dtypes(include=[np.number])
        imputer = KNNImputer(n_neighbors=k)
        imputed_data = imputer.fit_transform(numeric_df)
        
        col_idx = list(numeric_df.columns).index(column)
        
        for idx in target_indices:
            # 보간된 데이터 프레임의 인덱스는 원본과 다를 수 있으므로 매핑 필요
            row_pos = numeric_df.index.get_loc(idx)
            new_val = imputed_data[row_pos, col_idx]
            self._apply_imputation(column, [idx], new_val, f"k-NN 대체(k={k})")

    def _apply_imputation(self, column: str, indices: list, value: any, method: str):
        """공통 보완 적용 및 로그 기록"""
        for idx in indices:
            old_val = self.df.at[idx, column]
            self.df.at[idx, column] = value
            self.audit_log.append({
                "인덱스": idx,
                "변수명": column,
                "기존값": old_val,
                "대체값": value,
                "적용방법": method
            })

    def get_summary(self):
        """보완 통계 요약"""
        if not self.audit_log:
            return "보완된 내역이 없습니다."
        
        log_df = pd.DataFrame(self.audit_log)
        summary = log_df.groupby("변수명")["인덱스"].count().to_dict()
        return summary

    def export_excel(self) -> io.BytesIO:
        """기존 데이터 | 대체 데이터 | 대체 방법 구조의 엑셀 생성"""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 1. 메인 데이터 시트
            # 여기서는 원본 보존을 위해 별도 컬럼 생성이 필요함
            # 실제 구현 시에는 UI에서 선택한 변수별로 [원본] [보완] [방법] 3개 컬럼을 붙여서 생성
            self.df.to_excel(writer, index=False, sheet_name='AdjustedData')
            
            # 2. 보완 로그 시트
            if self.audit_log:
                pd.DataFrame(self.audit_log).to_excel(writer, index=False, sheet_name='AuditLog')
                
        output.seek(0)
        return output
