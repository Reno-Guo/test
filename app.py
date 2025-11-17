# main.py
import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
import io
import zipfile
import tempfile
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import plotly.express as px
from uuid import uuid4
from typing import Callable, List, Any, Dict

# === Concurrency-safe session + helpers ===
if "SID" not in st.session_state:
    st.session_state.SID = uuid4().hex[:6]

def unique_tmp_path(suggest_name: str, default_ext: str = ".xlsx") -> str:
    base, ext = os.path.splitext(suggest_name or f"result{default_ext}")
    ext = ext or default_ext
    return os.path.join("/tmp", f"{base}_{st.session_state.SID}_{uuid4().hex[:8]}{ext}")

@st.cache_data(ttl=1800, show_spinner=False)
def _read_excel_cached(file_or_path, sheet_name=0, engine=None):
    return pd.read_excel(file_or_path, sheet_name=sheet_name, engine=engine)

# App configuration
APP_CONFIG = {
    "app_title": "市场洞察小程序",
    "author": "海翼IDC团队",
    "version": "v1.2.0",
    "contact": "idc@oceanwing.com",
    "company": "Anker Oceanwing Inc."
}

# === Shared UI/render helpers ===
def render_app_header(emoji_title: str, subtitle: str):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: white; margin: 0; display: flex; align-items: center;">
            {emoji_title}
        </h2>
        <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def save_df_to_buffer(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    return buffer

def save_workbook_to_buffer(wb: Workbook) -> io.BytesIO:
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

def render_download_section(
    buffer: io.BytesIO,
    file_name: str,
    mime_type: str,
    download_label: str,
    key_prefix: str,
    has_save: bool = False,
    save_func: Callable[[], None] | None = None,
    save_path: str | None = None,
):
    if has_save:
        col_d, col_s = st.columns(2)
        with col_d:
            st.download_button(
                label=download_label,
                data=buffer,
                file_name=file_name,
                mime=mime_type,
                key=f"{key_prefix}_download",
                use_container_width=True,
            )
        with col_s:
            if st.checkbox("💾 同时保存到 /tmp 目录", key=f"{key_prefix}_save"):
                if save_func:
                    save_func()
                st.info(f"📁 文件已保存到 {save_path}")
    else:
        st.download_button(
            label=download_label,
            data=buffer,
            file_name=file_name,
            mime=mime_type,
            key=f"{key_prefix}_download",
            use_container_width=True,
        )

# === Shared ZIP processors ===
def read_file_merge(file_path: str) -> pd.DataFrame | None:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    engine = "openpyxl" if ext == ".xlsx" else "xlrd" if ext == ".xls" else None
    if engine:
        return _read_excel_cached(file_path, engine=engine)
    return None

def read_file_clean(file_path: str) -> pd.DataFrame | None:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path, header=None)
    engine = "openpyxl" if ext == ".xlsx" else "xlrd" if ext == ".xls" else None
    if engine:
        return pd.read_excel(file_path, header=None, engine=engine)
    return None

def write_processed_file(df: pd.DataFrame, path: str, ext: str):
    if ext == ".csv":
        df.to_csv(path, index=False)
    else:
        df.to_excel(path, index=False, engine='openpyxl')

def process_zip_files(
    uploaded_file,
    read_cb: Callable[[str], pd.DataFrame | None],
    process_cb: Callable[[pd.DataFrame, str, str], Any],
) -> List[Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with zipfile.ZipFile(zip_path, "r", metadata_encoding="utf-8") as z:
            z.extractall(temp_dir)
        files = [f for f in os.listdir(temp_dir) if f.lower().endswith((".xlsx", ".xls", ".csv"))]
        if not files:
            st.warning("📂 压缩文件中未找到任何 Excel 或 CSV 文件")
            return []
        results = []
        pb = st.progress(0)
        status = st.empty()
        for i, f in enumerate(files):
            status.text(f"正在处理: {f} ({i+1}/{len(files)})")
            fp = os.path.join(temp_dir, f)
            try:
                df = read_cb(fp)
                if df is None:
                    raise ValueError("不支持的文件格式")
                results.append(process_cb(df, f, temp_dir))
            except Exception as e:
                st.error(f"❌ 处理文件 {f} 失败: {e}")
            pb.progress((i + 1) / len(files))
        status.empty()
        pb.empty()
        return results

# 处理价格列
def process_price_columns(df):
    df = df.copy()
    price_pattern = re.compile(r'\$(\d+\.\d+)(?:\s*-\s*\$\d+\.\d+)?')
    def extract_price(price_str):
        if not isinstance(price_str, str):
            return price_str
        price_str = price_str.replace(',', '')
        match = price_pattern.match(price_str)
        return float(match.group(1)) if match else float(price_str.replace('$', ''))
    price_columns = [col for col in df.columns if '售价' in col]
    for column in price_columns:
        df[column] = df[column].apply(extract_price)
    return df

def main():
    st.set_page_config(page_title=APP_CONFIG["app_title"], layout="wide", page_icon="📊", initial_sidebar_state="collapsed")
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] {font-family: 'Inter', 'Segoe UI', sans-serif;}
        .main {background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);}
        h1, h2, h3, h4, h5, h6 {color: #ffffff !important; font-weight: 600 !important;}
        .stButton > button {
            background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%);
            color: white; border: none; border-radius: 8px; padding: 0.6rem 1.5rem;
            font-weight: 600; font-size: 15px; transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 166, 228, 0.2);
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #0088c2 0%, #006a99 100%);
            box-shadow: 0 6px 12px rgba(0, 166, 228, 0.3); transform: translateY(-2px);
        }
        .stDownloadButton > button {background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%);
            color: white; border: none; border-radius: 8px; padding: 0.6rem 1.5rem;
            font-weight: 600; font-size: 15px; transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 166, 228, 0.2);
        }
        .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #0088c2 0%, #006a99 100%);
            box-shadow: 0 6px 12px rgba(0, 166, 228, 0.3); transform: translateY(-2px);
        }
        .stFileUploader {background: white; border-radius: 10px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08);}
        [data-testid="stFileUploadDropzone"] {border: 2px dashed #00a6e4; border-radius: 8px; background: #f8fcff;}
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            border: 2px solid #e0e0e0; border-radius: 8px; padding: 0.6rem; transition: all 0.3s ease; font-size: 14px;
        }
        .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
            border-color: #00a6e4; box-shadow: 0 0 0 3px rgba(0, 166, 228, 0.1);
        }
        .stProgress > div > div > div > div {background: linear-gradient(90deg, #00a6e4 0%, #0088c2 100%);}
        .stSuccess {background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); border-left: 4px solid #28a745; border-radius: 8px; padding: 1rem;}
        .stError {background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border-left: 4px solid #dc3545; border-radius: 8px; padding: 1rem;}
        .stWarning {background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); border-left: 4px solid #ffc107; border-radius: 8px; padding: 1rem;}
        .stInfo {background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); border-left: 4px solid #00a6e4; border-radius: 8px; padding: 1rem;}
        div[data-testid="column"] {background: white; padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);}
        .js-plotly-plot {border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);}
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2.5rem 2rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 8px 16px rgba(0,0,0,0.15);">
        <h1 style="color: white; margin: 0; font-size: 2.5rem; font-weight: 700;">📊 市场洞察小程序</h1>
        <div style="display: flex; gap: 2rem; margin-top: 1rem; flex-wrap: wrap;">
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;"><strong>版本:</strong> {APP_CONFIG["version"]}</span>
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;"><strong>作者:</strong> {APP_CONFIG["author"]}</span>
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;"><strong>公司:</strong> {APP_CONFIG["company"]}</span>
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;"><strong>联系:</strong> {APP_CONFIG["contact"]}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h3 style="margin-top: 0; color: #333;">🎯 功能导航</h3>
        <p style="color: #666; margin-bottom: 0;">选择下方功能模块开始您的数据分析之旅</p>
    </div>
    """, unsafe_allow_html=True)
    tabs = st.tabs(["📊 合并数据表格", "🔍 搜索流量洞察", "📈 流量可视化分析", "🧹 数据清理工具"])
    with tabs[0]:
        merge_data_app()
    with tabs[1]:
        search_insight_app()
    with tabs[2]:
        search_insight_viz_app()
    with tabs[3]:
        data_clean_app()
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem 0;">
        <p style="margin: 0;">© Anker Oceanwing Inc. | 海翼IDC团队</p>
        <p style="margin: 0.5rem 0 0 0; font-size: 13px;">市场洞察小程序 v1.2.0 - 让数据分析更简单</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    from merge_data import merge_data_app
    from search_insight import search_insight_app
    from search_insight_viz import search_insight_viz_app
    from data_clean import data_clean_app
    main()
