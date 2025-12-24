import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io
import zipfile
import tempfile
import calendar
from pathlib import Path

# ... (保持原有的 save_df_to_buffer, render_app_header, csv_to_dataframe, 
# excel_to_dataframe, parse_month_year_to_yyyy_mm 函数不变)

def extract_and_get_files(uploaded_zip, temp_dir: str):
    """解压 zip 并返回所有数据文件路径"""
    zip_path = os.path.join(temp_dir, uploaded_zip.name)
    with open(zip_path, "wb") as f:
        f.write(uploaded_zip.getbuffer())
    
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(temp_dir)
    
    files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) 
             if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
    return files

def read_product_df(file_path: str, header_row: int) -> pd.DataFrame:
    """读取单个产品文件"""
    if file_path.lower().endswith('.csv'):
        return csv_to_dataframe(file_path, header_row)
    else:
        return pd.read_excel(file_path, header=header_row)

def get_month_columns(df: pd.DataFrame) -> list:
    """获取所有月份列（排除常见非月份列）"""
    exclude = {'Product', 'Product Name', 'Brand', 'Total', 'ASIN'}
    return [col for col in df.columns if col not in exclude]

def process_single_month(rev_files, units_files, asin_df, month_col, temp_dir, idx):
    """处理单个月份的数据"""
    # 1. 只读取当前月份需要的列
    rev_cols = ['Product', month_col]
    units_cols = ['Product', month_col]
    
    rev_parts = []
    for fp in rev_files:
        try:
            if fp.lower().endswith('.csv'):
                df = pd.read_csv(fp, usecols=lambda c: c in rev_cols, header=1)
            else:
                df = pd.read_excel(fp, usecols=rev_cols, header=1)
            rev_parts.append(df)
        except:
            continue
    
    if not rev_parts:
        return None
    rev_month = pd.concat(rev_parts, ignore_index=True).dropna(subset=[month_col])
    
    # 2. Units 同理
    units_parts = []
    for fp in units_files:
        try:
            if fp.lower().endswith('.csv'):
                df = pd.read_csv(fp, usecols=lambda c: c in units_cols, header=1)
            else:
                df = pd.read_excel(fp, usecols=units_cols, header=1)
            units_parts.append(df)
        except:
            continue
    
    if not units_parts:
        return None
    units_month = pd.concat(units_parts, ignore_index=True).dropna(subset=[month_col])
    
    # 3. 转成规范格式
    rev_month = rev_month.rename(columns={month_col: 'Total Revenue'})
    rev_month['时间'] = parse_month_year_to_yyyy_mm(month_col)
    
    units_month = units_month.rename(columns={month_col: 'Unit Sales'})
    units_month['时间'] = parse_month_year_to_yyyy_mm(month_col)
    
    # 4. 合并 Rev + Units
    combined = rev_month.merge(units_month, on='Product', how='inner')
    
    # 5. 匹配 ASIN 信息
    result = asin_df.merge(combined, left_on='ASIN', right_on='Product', how='inner')
    
    # 6. 立即保存到临时文件（parquet 更省空间且快）
    if not result.empty:
        temp_path = os.path.join(temp_dir, f"month_result_{idx:03d}.parquet")
        result.to_parquet(temp_path, index=False, compression='snappy')
        return temp_path
    return None

def sales_data_merge_app():
    render_app_header("🔗 销售数据合并工具（分月低内存版）", "逐月处理，内存占用大幅降低")
    
    # ... 上传控件部分保持不变 ...
    
    col1, col2, col3 = st.columns(3)
    with col1:
        rev_zip = st.file_uploader("Rev. ZIP", type=["zip"], key="rev")
    with col2:
        units_zip = st.file_uploader("Units ZIP", type=["zip"], key="units")
    with col3:
        asin_zip = st.file_uploader("Products ZIP", type=["zip"], key="asin")
    
    # ... 预览按钮部分可保留或简化 ...
    
    if st.button("🚀 开始分月合并（低内存）", use_container_width=True):
        if not all([rev_zip, units_zip, asin_zip]):
            st.warning("⚠️ 请上传所有三个ZIP文件")
            return
            
        with st.spinner("正在分月处理数据（内存友好模式）..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. 解压所有文件
                rev_files = extract_and_get_files(rev_zip, temp_dir)
                units_files = extract_and_get_files(units_zip, temp_dir)
                asin_files = extract_and_get_files(asin_zip, temp_dir)
                
                if not (rev_files and units_files and asin_files):
                    st.error("❌ 某些压缩包中没有有效数据文件")
                    return
                
                # 2. 读取完整的 ASIN 表（一般比较小）
                asin_dfs = [read_product_df(fp, header_row=0) for fp in asin_files]
                asin_df = pd.concat(asin_dfs, ignore_index=True).drop_duplicates(subset=['ASIN'])
                
                # 3. 获取所有月份（以 Rev 的列为准）
                sample_rev = read_product_df(rev_files[0], header_row=1)
                month_columns = get_month_columns(sample_rev)
                
                if not month_columns:
                    st.error("❌ 无法识别任何月份列")
                    return
                
                st.info(f"检测到 {len(month_columns)} 个月份，开始逐月处理...")
                
                temp_files = []
                progress_bar = st.progress(0)
                
                for i, month_col in enumerate(month_columns):
                    temp_file = process_single_month(
                        rev_files, units_files, asin_df, month_col, temp_dir, i
                    )
                    if temp_file:
                        temp_files.append(temp_file)
                    
                    progress_bar.progress((i + 1) / len(month_columns))
                
                if not temp_files:
                    st.error("❌ 所有月份处理后无有效数据")
                    return
                
                # 4. 合并所有临时 parquet 文件
                final_parts = [pd.read_parquet(f) for f in temp_files]
                final = pd.concat(final_parts, ignore_index=True)
                
                # 5. 列排序（保持原顺序逻辑）
                desired_order = [...]  # 你原来的 desired_order 列表
                existing_cols = [col for col in desired_order if col in final.columns]
                extra_cols = [col for col in final.columns if col not in desired_order]
                final = final[existing_cols + extra_cols]
                
                # 6. 输出结果
                buffer = save_df_to_buffer(final)
                out_name = f"merged_sales_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
                
                st.success(f"✅ 合并完成！共 {len(final):,} 行数据（{len(month_columns)} 个月）")
                st.dataframe(final.head(10), use_container_width=True)
                
                st.download_button(
                    "📥 下载合并结果",
                    data=buffer,
                    file_name=out_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
