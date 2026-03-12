import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency

def calculate_cramers_v(x, y):
    """명목변수 간 연관성 지표 (Cramér's V)"""
    confusion_matrix = pd.crosstab(x, y)
    try:
        chi2 = chi2_contingency(confusion_matrix)[0]
    except Exception:
        return 0.0
    n = confusion_matrix.sum().sum()
    phi2 = chi2 / n
    r, k = confusion_matrix.shape
    phi2corr = max(0, phi2 - ((k-1)*(r-1))/(n-1))
    rcorr = r - ((r-1)**2)/(n-1)
    kcorr = k - ((k-1)**2)/(n-1)
    
    res = np.sqrt(phi2corr / min((kcorr-1), (rcorr-1)))
    return res if not np.isnan(res) else 0.0

def calculate_correlation_ratio(categories, measurements):
    """명목변수와 수치변수 간 연관성 지표 (Eta)"""
    try:
        categories = pd.Series(categories)
        measurements = pd.Series(measurements)
        
        # 그룹별 평균 및 전체 평균
        means = measurements.groupby(categories).mean()
        overall_mean = measurements.mean()
        
        # 그룹별 분산 및 전체 분산
        ss_between = ((means - overall_mean)**2 * measurements.groupby(categories).count()).sum()
        ss_total = ((measurements - overall_mean)**2).sum()
        
        if ss_total == 0:
            return 0.0
        
        res = np.sqrt(ss_between / ss_total)
        return res if not np.isnan(res) else 0.0
    except Exception:
        return 0.0

def get_association(df, target_col, other_col):
    """두 변수 간의 타입에 맞는 연관성 지수 반환 (0~1)"""
    if target_col == other_col:
        return 1.0
        
    target_data = df[target_col]
    other_data = df[other_col]
    
    is_target_num = pd.api.types.is_numeric_dtype(target_data)
    is_other_num = pd.api.types.is_numeric_dtype(other_data)
    
    if is_target_num and is_other_num:
        # 둘 다 수치형: 피어슨 상관계수 (절대값)
        val = target_data.corr(other_data)
        return abs(val) if not np.isnan(val) else 0.0
    
    elif not is_target_num and not is_other_num:
        # 둘 다 명목형: 크래머 V
        return calculate_cramers_v(target_data, other_data)
        
    else:
        # 하나는 수치형, 하나는 명목형: 상관비 (Eta)
        cat_data = other_data if is_target_num else target_data
        num_data = target_data if is_target_num else other_data
        return calculate_correlation_ratio(cat_data, num_data)
