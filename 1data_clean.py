# data_clean.py
import streamlit as st
import io
import zipfile
from utils import render_app_header, process_zip_files, read_file_clean, write_processed_file, render_download_section

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
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as nz:
                for i, p in enumerate(processed):
                    arc = os.path.basename(p).replace("cleaned_", "")
                    nz.write(p, arc)
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
