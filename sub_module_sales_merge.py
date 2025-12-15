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

def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def make_column_names_unique(cols):
    """确保列名唯一，对重复的列名添加后缀"""
    new_cols = []
    seen = {}
    for col in cols:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    return new_cols

def csv_to_dataframe(csv_path: str, header_row: int = 0) -> pd.DataFrame:
    """将CSV文件转换为DataFrame，处理重复列名"""
    # 尝试多种编码读取CSV
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=encoding, header=header_row)
            # 确保列名唯一
            df.columns = make_column_names_unique(df.columns.tolist())
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            if "encoding" in str(e).lower():
                continue
            else:
                # 如果不是编码错误，则可能是其他问题，记录但继续尝试
                continue
    
    # 如果所有编码都失败，使用默认编码并忽略错误
    df = pd.read_csv(csv_path, encoding='utf-8', header=header_row, encoding_errors='ignore')
    # 确保列名唯一
    df.columns = make_column_names_unique(df.columns.tolist())
    return df

def excel_to_dataframe(excel_path: str, header_row: int = 0) -> pd.DataFrame:
    """将Excel文件转换为DataFrame，处理重复列名"""
    df = pd.read_excel(excel_path, header=header_row)
    # 确保列名唯一
    df.columns = make_column_names_unique(df.columns.tolist())
    return df

def process_zip_files_with_preview(
    uploaded_file,
    header_row: int = 0,
    file_type: str = "unknown"
) -> pd.DataFrame:
    """处理ZIP文件，将所有CSV/XLSX文件合并为一个DataFrame，并提供预览"""
    if uploaded_file is None:
        return pd.DataFrame()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_dir)
        
        # 获取所有CSV和XLSX文件
        files = [f for f in os.listdir(temp_dir) if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
        if not files:
            st.warning(f"📂 {file_type}压缩文件中未找到任何 CSV 或 Excel 文件")
            return pd.DataFrame()
        
        dfs = []
        pb = st.progress(0)
        status = st.empty()
        
        for i, f in enumerate(files):
            status.text(f"正在处理: {f} ({i+1}/{len(files)})")
            fp = os.path.join(temp_dir, f)
            
            try:
                if f.lower().endswith('.csv'):
                    # CSV文件转换为DataFrame
                    df = csv_to_dataframe(fp, header_row=header_row)
                else:
                    # Excel文件转换为DataFrame
                    df = excel_to_dataframe(fp, header_row=header_row)
                
                # 显示单个文件的预览
                with st.expander(f"📄 {file_type} - {f} 预览"):
                    st.write(f"**列名:** {list(df.columns)}")
                    st.write(f"**形状:** {df.shape}")
                    st.dataframe(df.head(5), use_container_width=True)
                
                dfs.append(df)
            except Exception as e:
                st.error(f"❌ 处理文件 {f} 失败: {e}")
            
            pb.progress((i + 1) / len(files))
        
        status.empty()
        pb.empty()
        
        if dfs:
            # 合并所有DataFrame，使用concat的ignore_index=True和sort=False参数
            # 为了避免重复索引问题，我们先重置每个DataFrame的索引
            for df in dfs:
                df.reset_index(drop=True, inplace=True)
            
            # 合并DataFrame
            result_df = pd.concat(dfs, ignore_index=True, sort=False)
            return result_df
        else:
            return pd.DataFrame()

def sales_data_merge_app():
    render_app_header("🔗 销售数据合并工具", "合并月度收入、单位数据与ASIN详细信息（含预览功能）")
    
    st.markdown("### 📥 上传数据文件")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rev_zip_file = st.file_uploader("选择月度收入ZIP文件 (by month rev.)", type=["zip"], key="rev_zip")
    with col2:
        units_zip_file = st.file_uploader("选择月度单位ZIP文件 (by month units)", type=["zip"], key="units_zip")
    with col3:
        asin_zip_file = st.file_uploader("选择ASIN详细信息ZIP文件", type=["zip"], key="asin_zip")
    
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        output_filename = st.text_input("输出文件名", "merged_sales_data.xlsx", key="merge_output_filename")
    with col2:
        st.write("")  # 空白列，保持对齐
        st.write("")  # 空白列，保持对齐
    
    st.divider()
    
    preview_btn = st.button("🔍 预览数据", key="preview", use_container_width=True)
    execute_btn = st.button("🚀 开始合并数据", key="merge_execute", use_container_width=True)
    
    if preview_btn:
        if not (rev_zip_file and units_zip_file and asin_zip_file):
            st.warning("⚠️ 请上传所有三个ZIP文件")
            return
        
        with st.spinner("🔄 正在加载预览数据，请稍候..."):
            # 预览月度收入数据 (表头在第2行，即header=1)
            rev_df = process_zip_files_with_preview(rev_zip_file, header_row=1, file_type="月度收入")
            if not rev_df.empty:
                st.success(f"✅ 月度收入数据已加载，共 {len(rev_df)} 行")
                with st.expander("📊 月度收入整体预览"):
                    st.write(f"**列名:** {list(rev_df.columns)}")
                    st.write(f"**形状:** {rev_df.shape}")
                    st.dataframe(rev_df.head(5), use_container_width=True)
            else:
                st.warning("❌ 无法加载月度收入数据")
            
            # 预览月度单位数据 (表头在第2行，即header=1)
            units_df = process_zip_files_with_preview(units_zip_file, header_row=1, file_type="月度单位")
            if not units_df.empty:
                st.success(f"✅ 月度单位数据已加载，共 {len(units_df)} 行")
                with st.expander("📊 月度单位整体预览"):
                    st.write(f"**列名:** {list(units_df.columns)}")
                    st.write(f"**形状:** {units_df.shape}")
                    st.dataframe(units_df.head(5), use_container_width=True)
            else:
                st.warning("❌ 无法加载月度单位数据")
            
            # 预览ASIN详细信息数据 (表头在第1行，即header=0)
            asin_df = process_zip_files_with_preview(asin_zip_file, header_row=0, file_type="ASIN详情")
            if not asin_df.empty:
                st.success(f"✅ ASIN详细信息数据已加载，共 {len(asin_df)} 行")
                with st.expander("📊 ASIN详情整体预览"):
                    st.write(f"**列名:** {list(asin_df.columns)}")
                    st.write(f"**形状:** {asin_df.shape}")
                    st.dataframe(asin_df.head(5), use_container_width=True)
            else:
                st.warning("❌ 无法加载ASIN详细信息数据")
    
    if execute_btn:
        if not (rev_zip_file and units_zip_file and asin_zip_file):
            st.warning("⚠️ 请上传所有三个ZIP文件")
            return
        
        with st.spinner("🔄 正在处理数据，请稍候..."):
            # 读取月度收入数据 (表头在第2行，即header=1)
            rev_df = process_zip_files_with_preview(rev_zip_file, header_row=1, file_type="")
            if rev_df.empty:
                st.error("❌ 无法读取月度收入数据")
                return
            
            # 读取月度单位数据 (表头在第2行，即header=1)
            units_df = process_zip_files_with_preview(units_zip_file, header_row=1, file_type="")
            if units_df.empty:
                st.error("❌ 无法读取月度单位数据")
                return
            
            # 读取ASIN详细信息数据 (表头在第1行，即header=0)
            asin_df = process_zip_files_with_preview(asin_zip_file, header_row=0, file_type="")
            if asin_df.empty:
                st.error("❌ 无法读取ASIN详细信息数据")
                return
            
            # 检查是否有所需的列
            if 'Product' not in rev_df.columns:
                st.error(f"❌ 月度收入文件中缺少 'Product' 列。现有列: {list(rev_df.columns)}")
                return
            
            if 'Product' not in units_df.columns:
                st.error(f"❌ 月度单位文件中缺少 'Product' 列。现有列: {list(units_df.columns)}")
                return
            
            if 'ASIN' not in asin_df.columns:
                st.error(f"❌ ASIN详细信息文件中缺少 'ASIN' 列。现有列: {list(asin_df.columns)}")
                return
            
            # 获取除Product Name、Brand、Total之外的月份列
            month_cols = [col for col in rev_df.columns if col not in ['Product Name', 'Brand', 'Total'] and col in units_df.columns]
            
            # 处理月度收入数据，将其转换为长格式
            rev_long_list = []
            for month_col in month_cols:
                if month_col in rev_df.columns:
                    month_data = rev_df[['Product', month_col]].copy()
                    month_data = month_data.dropna(subset=[month_col])  # 移除空值
                    month_data = month_data.rename(columns={month_col: 'Total Revenue'})
                    # 解析月份列名，转换为日期格式
                    try:
                        # 尝试解析月份格式，如 "Dec-23" -> "2023-12"
                        month_year = datetime.strptime(month_col, '%b-%y')
                        month_str = month_year.strftime('%Y-%m')
                    except:
                        # 如果无法解析，使用列名作为时间
                        month_str = month_col
                    month_data['时间'] = month_str
                    rev_long_list.append(month_data)
            
            # 合并所有月份的收入数据 - 使用更安全的方式合并
            if rev_long_list:
                # 重置每个DataFrame的索引以避免重复索引错误
                for df in rev_long_list:
                    df.reset_index(drop=True, inplace=True)
                rev_long_df = pd.concat(rev_long_list, ignore_index=True, sort=False)
            else:
                rev_long_df = pd.DataFrame(columns=['Product', 'Total Revenue', '时间'])
            
            # 处理月度单位数据，将其转换为长格式
            units_long_list = []
            for month_col in month_cols:
                if month_col in units_df.columns:
                    month_data = units_df[['Product', month_col]].copy()
                    month_data = month_data.dropna(subset=[month_col])  # 移除空值
                    month_data = month_data.rename(columns={month_col: 'Unit Sales'})
                    # 解析月份列名，转换为日期格式
                    try:
                        month_year = datetime.strptime(month_col, '%b-%y')
                        month_str = month_year.strftime('%Y-%m')
                    except:
                        month_str = month_col
                    month_data['时间'] = month_str
                    units_long_list.append(month_data)
            
            # 合并所有月份的单位数据
            if units_long_list:
                # 重置每个DataFrame的索引以避免重复索引错误
                for df in units_long_list:
                    df.reset_index(drop=True, inplace=True)
                units_long_df = pd.concat(units_long_list, ignore_index=True, sort=False)
            else:
                units_long_df = pd.DataFrame(columns=['Product', 'Unit Sales', '时间'])
            
            # 合并收入和单位数据
            if not rev_long_df.empty and not units_long_df.empty:
                combined_data = rev_long_df.merge(
                    units_long_df[['Product', 'Unit Sales', '时间']], 
                    on=['Product', '时间'], 
                    how='inner'  # 内连接，只保留两个数据框都有的记录
                )
            elif not rev_long_df.empty:
                combined_data = rev_long_df.copy()
                combined_data['Unit Sales'] = None
            elif not units_long_df.empty:
                combined_data = units_long_df.copy()
                combined_data['Total Revenue'] = None
            else:
                st.error("❌ 没有可用的月度数据进行合并")
                return
            
            # 通过rev文件的Product列和asin详情文件的ASIN列进行内连接（只保留匹配的记录）
            if not combined_data.empty:
                # 将合并的数据与ASIN详细信息按Product和ASIN列进行内连接
                final_result = asin_df.merge(
                    combined_data,
                    left_on='ASIN',  # ASIN详细信息的ASIN列
                    right_on='Product',  # 月度数据的Product列
                    how='inner'  # 内连接，只保留三者都匹配的记录
                )
                
                # 删除重复的Product列（因为ASIN和Product应该是同一列）
                if 'Product_y' in final_result.columns:
                    final_result = final_result.drop(columns=['Product_y'])
                    final_result = final_result.rename(columns={'Product_x': 'Product'})
                elif 'Product' in final_result.columns and 'ASIN' in final_result.columns:
                    # 如果只有一边有Product列，保留ASIN作为主键
                    pass
            else:
                st.error("❌ 没有匹配的记录可以合并")
                return
            
            if final_result.empty:
                st.warning("⚠️ 没有任何匹配的记录，请检查Product和ASIN列的值是否对应")
                return
            
            # 保存结果
            buffer = save_df_to_buffer(final_result)
            ts = get_timestamp()
            out_name = f"merged_sales_data_{ts}.xlsx"
            out_path = os.path.join("/tmp", out_name)
            
            st.success(f"✅ 数据合并完成！共处理 {len(final_result)} 行数据")
            
            # 显示结果预览
            st.markdown("### 📊 合并结果预览")
            st.dataframe(final_result.head(10), use_container_width=True)
            
            save_func = lambda: final_result.to_excel(out_path, index=False, engine="openpyxl")
            render_download_section(
                buffer,
                out_name,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "📥 下载合并后的Excel文件",
                "sales_merge",
                has_save=True,
                save_func=save_func,
                save_path=out_path,
            )
