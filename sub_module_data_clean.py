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

# 从主程序导入共享函数
def _read_excel_cached(file_or_path, sheet_name=0, engine=None):
    return pd.read_excel(file_or_path, sheet_name=sheet_name, engine=engine)

def unique_tmp_path(suggest_name: str, default_ext: str = ".xlsx") -> str:
    base, ext = os.path.splitext(suggest_name or f"result{default_ext}")
    ext = ext or default_ext
    return os.path.join("/tmp", f"{base}_{st.session_state.SID}_{uuid4().hex[:8]}{ext}")

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

def render_app_header(emoji_title: str, subtitle: str):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: white; margin: 0; display: flex; align-items: center;">
            {emoji_title}
        </h2>
        <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

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
        df.to_excel(path, index=False, engine="openpyxl")

def process_zip_files(
    uploaded_file,
    read_cb: Callable[[str], pd.DataFrame | None],
    process_cb: Callable[[pd.DataFrame, str, str], Any],
) -> List[Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with zipfile.ZipFile(zip_path, "r") as z:
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

def data_clean_app():
    render_app_header("🧹 DC - 数据清理: 删除第一行", "批量删除Excel/CSV文件的第一行数据并重新打包")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "选择一个 .zip 文件(包含 XLSX 或 CSV 文件)",
            type=["zip"],
            key="clean_files",
        )
    with col2:
        output_filename = st.text_input("输出文件名", "cleaned_files.zip", key="clean_save")
    st.divider()
    execute_btn = st.button("🚀 开始清理", key="clean_button", use_container_width=True)
    if execute_btn:
        if not uploaded_file or not output_filename:
            st.warning("⚠️ 请确保已选择 .zip 文件并输入输出文件名")
            return
        with st.spinner("🔄 正在清理文件，请稍候..."):
            def cb_clean(df, fname, tdir):
                df = df.iloc[1:].reset_index(drop=True)
                out_path = os.path.join(tdir, f"cleaned_{fname}")
                ext = os.path.splitext(fname)[1].lower()
                write_processed_file(df, out_path, ext)
                return out_path
            processed = process_zip_files(uploaded_file, read_file_clean, cb_clean)
            if not processed:
                return
            status = st.empty()
            prog = st.progress(0)
            status.text("正在打包ZIP文件...")
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as nz:
                nz.setpassword(None)
                for i, p in enumerate(processed):
                    original_name = os.path.basename(p).replace("cleaned_", "")
                    nz.write(p, original_name, compress_type=zipfile.ZIP_DEFLATED)
                    prog.progress((i + 1) / len(processed))
            buffer.seek(0)
            status.text("打包完成")
            status.empty()
            prog.empty()
            st.success(f"✅ 成功清理 {len(processed)} 个文件")
            render_download_section(
                buffer,
                output_filename,
                "application/zip",
                "📥 下载清理后的 ZIP 文件",
                "cleaned",
                has_save=False,
            )
