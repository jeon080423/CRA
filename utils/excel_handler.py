"""
엑셀 파일 업로드/다운로드 처리 유틸리티
"""
import io
import pandas as pd


def load_excel(uploaded_file) -> pd.DataFrame:
    """
    업로드된 엑셀 파일을 DataFrame으로 읽기

    Args:
        uploaded_file: Streamlit file_uploader 반환 객체

    Returns:
        pd.DataFrame: 엑셀 데이터
    """
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".xls"):
        return pd.read_excel(uploaded_file, engine="xlrd")
    else:
        return pd.read_excel(uploaded_file, engine="openpyxl")


def export_result_excel(df: pd.DataFrame) -> io.BytesIO:
    """
    DataFrame을 엑셀 파일(BytesIO)로 변환

    Args:
        df: 결과 DataFrame

    Returns:
        io.BytesIO: 다운로드 가능한 바이트 스트림
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="조회결과")
    output.seek(0)
    return output
