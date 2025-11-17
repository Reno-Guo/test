# merge_data.py
import streamlit as st
import pandas as pd
import os
from utils import render_app_header, unique_tmp_path, process_zip_files, read_file_merge, process_price_columns, save_df_to_buffer, render_download_section

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
