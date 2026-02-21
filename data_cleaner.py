import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer
# MICE (IterativeImputer) 활성화
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
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

    def impute_median(self, column: str, target_indices: list):
        """중앙값 대체"""
        median_val = self.df[column].median()
        self._apply_imputation(column, target_indices, median_val, "중앙값 대체")

    def impute_mode(self, column: str, target_indices: list):
        """최빈값 대체 (범주형)"""
        mode_val = self.df[column].mode()[0]
        self._apply_imputation(column, target_indices, mode_val, "최빈값 대체")
        
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
        numeric_df = self.df.select_dtypes(include=[np.number])
        if column not in numeric_df.columns:
            return # 수치형이 아니면 스킵
            
        imputer = KNNImputer(n_neighbors=k)
        imputed_data = imputer.fit_transform(numeric_df)
        
        col_idx = list(numeric_df.columns).index(column)
        
        for idx in target_indices:
            row_pos = numeric_df.index.get_loc(idx)
            new_val = imputed_data[row_pos, col_idx]
            self._apply_imputation(column, [idx], new_val, f"k-NN 대체(k={k})")

    def impute_mice(self, column: str, target_indices: list):
        """MICE (다중 대체) 알고리즘"""
        numeric_df = self.df.select_dtypes(include=[np.number])
        if column not in numeric_df.columns:
            return
            
        imputer = IterativeImputer(random_state=42)
        imputed_data = imputer.fit_transform(numeric_df)
        
        col_idx = list(numeric_df.columns).index(column)
        
        for idx in target_indices:
            row_pos = numeric_df.index.get_loc(idx)
            new_val = imputed_data[row_pos, col_idx]
            self._apply_imputation(column, [idx], new_val, "MICE 다중 대체")

    def _apply_imputation(self, column: str, indices: list, value: any, method: str):
        """공통 보완 적용 및 로그 기록"""
        # NumPy 타입이면 기본 Python 타입으로 변환 (엑셀 저장 시 호환성)
        if isinstance(value, (np.integer, np.floating)):
            value = value.item()
            
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
            return {}
        
        log_df = pd.DataFrame(self.audit_log)
        summary = log_df.groupby("변수명")["인덱스"].count().to_dict()
        return summary

    def export_excel(self) -> io.BytesIO:
        """기존 데이터 | 대체 데이터 | 대체 방법 구조의 엑셀 생성"""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            self.df.to_excel(writer, index=False, sheet_name='AdjustedData')
            if self.audit_log:
                pd.DataFrame(self.audit_log).to_excel(writer, index=False, sheet_name='AuditLog')
        output.seek(0)
        return output

class WeightCalculator:
    """단위 무응답 교정을 위한 통계적 가중치(Weighting) 엔진"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        if 'weight' not in self.df.columns:
            self.df['weight'] = 1.0
            
    def apply_raking(self, targets: dict, max_iter=50, tolerance=1e-4):
        """
        RIM Weighting (Raking) 알고리즘 수행
        targets: { '변수명': { '값1': 목표비율1, '값2': 목표비율2 }, ... }
        """
        import pandas as pd
        curr_df = self.df.copy()
        
        for i in range(max_iter):
            max_diff = 0
            for col, target_dist in targets.items():
                if col not in curr_df.columns:
                    continue
                    
                current_weighted_sums = curr_df.groupby(col)['weight'].sum()
                total_weight = current_weighted_sums.sum()
                
                for val, target_prop in target_dist.items():
                    actual_sum = current_weighted_sums.get(val, 0)
                    if actual_sum == 0: continue
                    
                    target_sum = total_weight * target_prop
                    factor = target_sum / actual_sum
                    
                    curr_df.loc[curr_df[col] == val, 'weight'] *= factor
                    max_diff = max(max_diff, abs(1 - factor))
            
            if max_diff < tolerance:
                break
                
        curr_df['weight'] = curr_df['weight'] / curr_df['weight'].mean()
        self.df = curr_df
        return i + 1, max_diff

    def get_diagnostics(self):
        """가중치 품질 진단 데이터 산출"""
        ws = self.df['weight']
        n = len(ws)
        deff = n * (ws**2).sum() / (ws.sum()**2)
        ess = n / deff
        
        return {
            "min": ws.min(),
            "max": ws.max(),
            "mean": ws.mean(),
            "std": ws.std(),
            "deff": deff,
            "ess": ess
        }
