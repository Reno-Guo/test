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

def csv_to_xlsx(csv_path: str, header_row: int = 0) -> pd.DataFrame:
    """将CSV文件转换为XLSX格式的DataFrame"""
    # 尝试多种编码读取CSV
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=encoding, header=header_row)
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
    return df

def process_zip_files(
    uploaded_file,
    header_row: int = 0,
    expected_cols: List[str] = None
) -> pd.DataFrame:
    """处理ZIP文件，将所有CSV/XLSX文件合并为一个DataFrame"""
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_dir)
        
        # 获取所有CSV和XLSX文件
        files = [f for f in os.listdir(temp_dir) if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
        if not files:
            st.warning("📂 压缩文件中未找到任何 CSV 或 Excel 文件")
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
                    df = csv_to_xlsx(fp, header_row=header_row)
                else:
                    # Excel文件直接读取
                    df = pd.read_excel(fp, header=header_row)
                
                # 如果指定了预期列，确保DataFrame包含这些列
                if expected_cols:
                    for col in expected_cols:
                        if col not in df.columns:
                            df[col] = pd.NA
                
                dfs.append(df)
            except Exception as e:
                st.error(f"❌ 处理文件 {f} 失败: {e}")
            
            pb.progress((i + 1) / len(files))
        
        status.empty()
        pb.empty()
        
        if dfs:
            # 合并所有DataFrame
            all_columns = set()
            for df in dfs:
                all_columns.update(df.columns.tolist())
            
            # 标准化所有DataFrame的列
            standardized_dfs = []
            for df in dfs:
                missing_cols = all_columns - set(df.columns)
                for col in missing_cols:
                    df[col] = pd.NA
                df = df.reindex(columns=sorted(all_columns))
                standardized_dfs.append(df)
            
            return pd.concat(standardized_dfs, ignore_index=True, sort=False)
        else:
            return pd.DataFrame()

def sales_data_merge_app():
    render_app_header("🔗 销售数据合并工具", "合并月度收入、单位数据与ASIN详细信息")
    
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
    
    execute_btn = st.button("🚀 开始合并数据", key="merge_execute", use_container_width=True)
    
    if execute_btn:
        if not (rev_zip_file and units_zip_file and asin_zip_file):
            st.warning("⚠️ 请上传所有三个ZIP文件")
            return
        
        with st.spinner("🔄 正在处理数据，请稍候..."):
            # 读取月度收入数据 (表头在第2行，即header=1)
            rev_df = process_zip_files(rev_zip_file, header_row=1)
            if rev_df.empty:
                st.error("❌ 无法读取月度收入数据")
                return
            
            # 读取月度单位数据 (表头在第2行，即header=1)
            units_df = process_zip_files(units_zip_file, header_row=1)
            if units_df.empty:
                st.error("❌ 无法读取月度单位数据")
                return
            
            # 读取ASIN详细信息数据 (表头在第1行，即header=0)
            asin_df = process_zip_files(asin_zip_file, header_row=0)
            if asin_df.empty:
                st.error("❌ 无法读取ASIN详细信息数据")
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
            
            # 合并所有月份的收入数据
            if rev_long_list:
                # 标准化列结构
                all_rev_columns = set()
                for df in rev_long_list:
                    all_rev_columns.update(df.columns.tolist())
                
                standardized_rev_long_list = []
                for df in rev_long_list:
                    missing_cols = all_rev_columns - set(df.columns)
                    for col in missing_cols:
                        df[col] = pd.NA
                    df = df.reindex(columns=sorted(all_rev_columns))
                    standardized_rev_long_list.append(df)
                
                rev_long_df = pd.concat(standardized_rev_long_list, ignore_index=True, sort=False)
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
                # 标准化列结构
                all_units_columns = set()
                for df in units_long_list:
                    all_units_columns.update(df.columns.tolist())
                
                standardized_units_long_list = []
                for df in units_long_list:
                    missing_cols = all_units_columns - set(df.columns)
                    for col in missing_cols:
                        df[col] = pd.NA
                    df = df.reindex(columns=sorted(all_units_columns))
                    standardized_units_long_list.append(df)
                
                units_long_df = pd.concat(standardized_units_long_list, ignore_index=True, sort=False)
            else:
                units_long_df = pd.DataFrame(columns=['Product', 'Unit Sales', '时间'])
            
            # 为了得到您示例中的结果，我们需要为每个产品-月份组合生成一行
            # 首先获取所有产品-月份组合
            if not rev_long_df.empty and not units_long_df.empty:
                # 合并收入和单位数据
                combined_data = rev_long_df.merge(
                    units_long_df[['Product', 'Unit Sales', '时间']], 
                    on=['Product', '时间'], 
                    how='outer'
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
            
            # 创建一个包含所有产品-时间组合的DataFrame
            product_time_combos = combined_data[['Product', '时间']].drop_duplicates()
            
            # 对每个产品-时间组合，复制ASIN详细信息的一行
            expanded_results = []
            
            for _, combo in product_time_combos.iterrows():
                product = combo['Product']
                time_period = combo['时间']
                
                # 获取该产品的ASIN详细信息
                product_details = asin_df[asin_df['Product'] == product].copy()
                
                if not product_details.empty:
                    # 为该时间周期添加收入和单位数据
                    rev_mask = (combined_data['Product'] == product) & (combined_data['时间'] == time_period)
                    rev_values = combined_data.loc[rev_mask, 'Total Revenue']
                    unit_mask = (combined_data['Product'] == product) & (combined_data['时间'] == time_period)
                    unit_values = combined_data.loc[unit_mask, 'Unit Sales']
                    
                    # 复制每一行并更新Total Revenue和Unit Sales列
                    for idx, row in product_details.iterrows():
                        new_row = row.copy()
                        if not rev_values.empty and pd.notna(rev_values.iloc[0]):
                            new_row['Total Revenue'] = rev_values.iloc[0]
                        if not unit_values.empty and pd.notna(unit_values.iloc[0]):
                            new_row['Unit Sales'] = unit_values.iloc[0]
                        
                        # 添加时间列
                        new_row['时间'] = time_period
                        expanded_results.append(new_row)
            
            if expanded_results:
                final_result = pd.DataFrame(expanded_results)
            else:
                final_result = asin_df.copy()
                final_result['时间'] = None
            
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
