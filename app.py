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
from datetime import timedelta

# 导入子程序模块
try:
    from sub_module_sales_merge import sales_data_merge_app
except ImportError:
    def sales_data_merge_app():
        st.error("模块 'sub_module_sales_merge' 未找到")

try:
    from sub_module_merge import merge_data_app
except ImportError:
    def merge_data_app():
        st.error("模块 'sub_module_merge' 未找到")

try:
    from sub_module_search_insight import search_insight_app
except ImportError:
    def search_insight_app():
        st.error("模块 'sub_module_search_insight' 未找到")

try:
    from sub_module_visualization import search_insight_viz_app
except ImportError:
    def search_insight_viz_app():
        st.error("模块 'sub_module_visualization' 未找到")

try:
    from sub_module_data_clean import data_clean_app
except ImportError:
    def data_clean_app():
        st.error("模块 'sub_module_data_clean' 未找到")

try:
    from sub_module_pack_form import pack_form_labeler_app
except ImportError:
    def pack_form_labeler_app():
        st.error("模块 'sub_module_pack_form' 未找到")

# App configuration
APP_CONFIG = {
    "app_title": "Data Cleansing for Market Insights",
    "author": "Developed by the IDC Team, Oceanwing",
    "version": "v1.3.0",
    "contact": "idc@oceanwing.com",
    "company": "Anker Oceanwing Inc."
}

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

def main():
    st.set_page_config(page_title=APP_CONFIG["app_title"], layout="wide", page_icon="📊", initial_sidebar_state="collapsed")
    
    if "active_users" not in st.session_state:
        st.session_state.active_users = {}

    # 记录用户进入
    user_id = st.session_state.SID
    st.session_state.active_users[user_id] = datetime.now()

    # 清理超过30分钟不活跃的
    threshold = datetime.now() - timedelta(minutes=30)
    st.session_state.active_users = {k: v for k, v in st.session_state.active_users.items() if v > threshold}

    active_count = len(st.session_state.active_users)

    if active_count > 5:
        st.warning(f"⚠️ 当前有 {active_count} 位用户正在使用，存在线程冲突风险")
    
    st.set_page_config(page_title=APP_CONFIG["app_title"], layout="wide", page_icon="📊", initial_sidebar_state="collapsed")
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] {font-family: 'Inter', 'Segoe UI', sans-serif;}
        .main {background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);}
        
        /* 修复标题显示问题：只在顶部 Banner 区域使用白色标题 */
        div[style*="linear-gradient(135deg, #00a6e4"] h1,
        div[style*="linear-gradient(135deg, #00a6e4"] h2,
        div[style*="linear-gradient(135deg, #00a6e4"] h3,
        div[style*="linear-gradient(135deg, #00a6e4"] h4,
        div[style*="linear-gradient(135deg, #00a6e4"] h5,
        div[style*="linear-gradient(135deg, #00a6e4"] h6 {
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        /* 内容区域的标题使用深色 */
        .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {
            color: #333333 !important;
            font-weight: 600 !important;
        }
        
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
        <h1 style="color: white; margin: 0; font-size: 2.5rem; font-weight: 700;">📊 Data Cleansing for Market Insights</h1>
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
    tabs = st.tabs(["🔗 销售数据合并", "📊 合并数据表格", "🔍 搜索流量洞察", "📈 流量可视化分析", "🧹 数据清理工具", "🏷️ 剂型打标工具"])
    with tabs[0]:
        sales_data_merge_app()
    with tabs[1]:
        merge_data_app()
    with tabs[2]:
        search_insight_app()
    with tabs[3]:
        search_insight_viz_app()
    with tabs[4]:
        data_clean_app()
    with tabs[5]:
        pack_form_labeler_app()
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem 0;">
        <p style="margin: 0;">© Anker Oceanwing Inc. | Developed by the IDC Team, Oceanwing</p>
        <p style="margin: 0.5rem 0 0 0; font-size: 13px;">Data Cleansing for Market Insights - Making data analysis simpler</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
