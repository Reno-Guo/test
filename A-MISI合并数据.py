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

def save_df_to_buffer(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
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

def render_app_header(emoji_title: str, subtitle: str):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: white; margin: 0; display: flex; align-items: center;">
            {emoji_title}
        </h2>
        <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

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

def read_file_merge(file_path: str) -> pd.DataFrame | None:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    engine = "openpyxl" if ext == ".xlsx" else "xlrd" if ext == ".xls" else None
    if engine:
        return _read_excel_cached(file_path, engine=engine)
    return None

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

def merge_data_app():
    render_app_header("📊 MI/SI - 合并数据表格", "将多个Excel文件合并为一个统一的数据表格")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "选择一个 .zip 文件(包含需要合并的 Excel 文件)",
            type=["zip"],
            accept_multiple_files=False,
            key="merge_files",
            help="支持包含.xlsx、.xls、.csv格式的ZIP压缩包",
        )
    with col2:
        save_filename = st.text_input(
            "输出文件名",
            value="merged_output.xlsx",
            key="merge_save",
            help="请输入合并后的文件名",
        )
    st.divider()
    execute_btn = st.button("🚀 开始合并", key="merge_button", use_container_width=True)
    if execute_btn:
        if not uploaded_file or not save_filename:
            st.warning("⚠️ 请确保已选择 .zip 文件并输入文件名")
            return
        with st.spinner("🔄 正在处理文件，请稍候..."):
            save_path = unique_tmp_path(save_filename)
            def cb_merge(df, fname, _):
                df["时间"] = os.path.splitext(fname)[0]
                return process_price_columns(df)
            df_list = process_zip_files(uploaded_file, read_file_merge, cb_merge)
            if not df_list:
                return
            status = st.empty()
            prog = st.progress(0)
            status.text("正在合并数据...")
            merged_df = pd.concat(df_list, ignore_index=True)
            merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
            prog.progress(1.0)
            status.text("合并完成")
            status.empty()
            prog.empty()
            buffer = save_df_to_buffer(merged_df)
            st.success(f"✅ 成功合并 {len(df_list)} 个文件，共 {len(merged_df)} 行数据")
            save_func = lambda: merged_df.to_excel(save_path, index=False, engine="openpyxl")
            render_download_section(
                buffer,
                os.path.basename(save_filename),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "📥 下载合并后的文件",
                "merged",
                has_save=True,
                save_func=save_func,
                save_path=save_path,
            )
