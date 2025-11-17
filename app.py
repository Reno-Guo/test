# main.py
import streamlit as st
from uuid import uuid4
from utils import APP_CONFIG
from merge_data import merge_data_app
from search_insight import search_insight_app
from search_insight_viz import search_insight_viz_app
from data_clean import data_clean_app

def main():
    # Initialize SID here to ensure session_state is ready
    if "SID" not in st.session_state:
        st.session_state.SID = uuid4().hex[:6]

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
    main()
