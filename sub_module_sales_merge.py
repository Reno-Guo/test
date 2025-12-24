import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io
import zipfile
import tempfile
import calendar
from pathlib import Path

# =============================================================================
# 工具函数（保持原有，未做大改动）
# =============================================================================

def save_df_to_buffer(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    return buffer


def render_app_header(emoji_title: str, subtitle: str):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: white; margin: 0; display: flex; align-items: center;">
            {emoji_title}
        </h2>
        <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def csv_to_dataframe(csv_path: str, header_row: int = 0) -> pd.DataFrame:
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=encoding, header=header_row)
            return df
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    # 兜底方案
    return pd.read_csv(csv_path, encoding='utf-8', header=header_row, encoding_errors='ignore')


def excel_to_dataframe(excel_path: str, header_row: int = 0) -> pd.DataFrame:
    return pd.read_excel(excel_path, header=header_row)


def parse_month_year_to_yyyy_mm(col_name: str) -> str:
    """将 'December 2023' 或 'December-2023' 转为 '2023-12'"""
    clean = col_name.replace(',', '').replace('-', ' ').strip()
    parts = clean.split()
    if len(parts) < 2:
        return col_name
    month_name, year_str = parts[0], parts[1]
    try:
        month_num = list(calendar.month_name).index(month_name.capitalize())
        return f"{year_str}-{month_num:02d}"
    except ValueError:
        return col_name


# =============================================================================
# 分月处理核心函数
# =============================================================================

def extract_and_get_files(uploaded_zip, temp_dir: str):
    """解压 zip 并返回所有数据文件路径"""
    if uploaded_zip is None:
        return []
        
    zip_path = os.path.join(temp_dir, uploaded_zip.name)
    with open(zip_path, "wb") as f:
        f.write(uploaded_zip.getbuffer())
    
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(temp_dir)
    
    files = [
        os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
        if f.lower().endswith(('.csv', '.xlsx', '.xls'))
    ]
    return files


def read_product_df(file_path: str, header_row: int) -> pd.DataFrame:
    """读取单个产品文件"""
    try:
        if file_path.lower().endswith('.csv'):
            return csv_to_dataframe(file_path, header_row)
        else:
            return pd.read_excel(file_path, header=header_row)
    except Exception as e:
        st.warning(f"读取文件失败 {os.path.basename(file_path)}: {str(e)}")
        return pd.DataFrame()


def get_month_columns(df: pd.DataFrame) -> list[str]:
    """尝试识别月份列"""
    exclude = {
        'Product', 'Product Name', 'Brand', 'Total', 'ASIN', 'SKU',
        'Category', 'Subcategory', 'Parent ASIN'
    }
    
    candidates = [col for col in df.columns if col not in exclude]
    
    # 更智能的月份列判断
    month_like = []
    for col in candidates:
        cleaned = str(col).replace(',', '').replace('-', ' ').strip()
        parts = cleaned.split()
        if len(parts) >= 2:
            # 包含年份（2000~2099）且有月份词的可能性较高
            has_year = any(p.isdigit() and 2000 <= int(p) <= 2099 for p in parts)
            if has_year:
                month_like.append(col)
    
    return month_like if month_like else candidates[:24]  # 最多假设24个月


def get_all_month_columns(rev_files: list[str]) -> list[str]:
    """从所有 Rev 文件中收集可能的月份列"""
    all_months = set()
    
    for fp in rev_files:
        try:
            # 只读取第一行获取列名，效率最高
            if fp.lower().endswith('.csv'):
                df_header = pd.read_csv(fp, nrows=1, header=1)
            else:
                df_header = pd.read_excel(fp, nrows=1, header=1)
                
            months = get_month_columns(df_header)
            all_months.update(months)
        except Exception:
            continue
            
    return sorted(list(all_months))


def process_single_month(rev_files, units_files, asin_df, month_col, temp_dir, idx):
    """处理单个月份的数据"""
    rev_cols = ['Product', month_col]
    units_cols = ['Product', month_col]
    
    # Rev
    rev_parts = []
    for fp in rev_files:
        try:
            if fp.lower().endswith('.csv'):
                df = pd.read_csv(fp, usecols=lambda c: c in rev_cols, header=1, low_memory=False)
            else:
                df = pd.read_excel(fp, usecols=lambda c: c in rev_cols, header=1, engine='openpyxl')
            if not df.empty:
                rev_parts.append(df)
        except Exception as e:
            st.warning(f"Rev 文件读取月份 {month_col} 失败: {os.path.basename(fp)} - {str(e)}")
            continue
    
    if not rev_parts:
        return None
    rev_month = pd.concat(rev_parts, ignore_index=True).dropna(subset=[month_col], how='all')
    
    # Units
    units_parts = []
    for fp in units_files:
        try:
            if fp.lower().endswith('.csv'):
                df = pd.read_csv(fp, usecols=lambda c: c in units_cols, header=1, low_memory=False)
            else:
                df = pd.read_excel(fp, usecols=lambda c: c in units_cols, header=1, engine='openpyxl')
            if not df.empty:
                units_parts.append(df)
        except Exception as e:
            st.warning(f"Units 文件读取月份 {month_col} 失败: {os.path.basename(fp)} - {str(e)}")
            continue
    
    if not units_parts:
        return None
    units_month = pd.concat(units_parts, ignore_index=True).dropna(subset=[month_col], how='all')
    
    # 格式化
    rev_month = rev_month.rename(columns={month_col: 'Total Revenue'})
    rev_month['时间'] = parse_month_year_to_yyyy_mm(month_col)
    
    units_month = units_month.rename(columns={month_col: 'Unit Sales'})
    units_month['时间'] = parse_month_year_to_yyyy_mm(month_col)
    
    # 合并
    combined = rev_month.merge(units_month, on='Product', how='inner')
    
    if combined.empty:
        return None
        
    # 与 ASIN 表匹配
    result = asin_df.merge(combined, left_on='ASIN', right_on='Product', how='inner')
    
    if result.empty:
        return None
        
    # 保存临时 parquet
    temp_path = os.path.join(temp_dir, f"month_result_{idx:03d}.parquet")
    result.to_parquet(temp_path, index=False, compression='snappy')
    return temp_path


# =============================================================================
# 主应用函数
# =============================================================================

def sales_data_merge_app():
    render_app_header(
        "🔗 销售数据合并工具"
    )
    
    st.markdown("### 📥 上传数据文件（ZIP 格式）")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        rev_zip = st.file_uploader("Rev. ZIP（收入）", type=["zip"], key="rev_zip")
    with col2:
        units_zip = st.file_uploader("Units ZIP（销量）", type=["zip"], key="units_zip")
    with col3:
        asin_zip = st.file_uploader("Products ZIP（产品信息）", type=["zip"], key="asin_zip")
    
    st.divider()
    
    if st.button("🚀 开始合并", type="primary", use_container_width=True):
        if not all([rev_zip, units_zip, asin_zip]):
            st.error("⚠️ 请上传全部三个 ZIP 文件")
            return
            
        with st.spinner("正在分月处理数据（内存友好模式）..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. 解压所有文件
                rev_files = extract_and_get_files(rev_zip, temp_dir)
                units_files = extract_and_get_files(units_zip, temp_dir)
                asin_files = extract_and_get_files(asin_zip, temp_dir)
                
                if not (rev_files and units_files and asin_files):
                    st.error("❌ 至少有一个压缩包中没有找到有效的 CSV/XLSX 文件")
                    return
                
                # 2. 读取完整的 ASIN 表（通常较小）
                asin_dfs = []
                for fp in asin_files:
                    df = read_product_df(fp, header_row=0)
                    if not df.empty:
                        asin_dfs.append(df)
                
                if not asin_dfs:
                    st.error("❌ 无法读取任何 Products/ASIN 数据")
                    return
                    
                asin_df = pd.concat(asin_dfs, ignore_index=True).drop_duplicates(subset=['ASIN'])
                
                # 3. 获取所有可能的月份列（从所有 Rev 文件中收集）
                month_columns = get_all_month_columns(rev_files)
                
                if not month_columns:
                    st.error("❌ 无法识别任何月份列（请检查 Rev 文件的列名格式）")
                    return
                
                st.info(f"共检测到 **{len(month_columns)}** 个月份，开始逐月处理...")
                
                temp_files = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, month_col in enumerate(month_columns):
                    status_text.text(f"处理中: {month_col} ({i+1}/{len(month_columns)})")
                    
                    temp_file = process_single_month(
                        rev_files, units_files, asin_df, month_col, temp_dir, i
                    )
                    if temp_file:
                        temp_files.append(temp_file)
                    
                    progress_bar.progress((i + 1) / len(month_columns))
                
                status_text.empty()
                
                if not temp_files:
                    st.error("❌ 所有月份处理后没有生成任何有效数据")
                    return
                
                # 4. 合并所有月份结果
                st.info("正在合并所有月份结果...")
                final_parts = [pd.read_parquet(f) for f in temp_files]
                final = pd.concat(final_parts, ignore_index=True)
                
                # 5. 期望的列顺序（请根据你的实际业务字段调整）
                desired_order = [
                    'Product', 'ASIN', 'Brand', 'Price', 'BSR', 'Number of sellers', 'Fulfillment',
                    'FBA fees (USD)', 'Ratings', 'Review count', 'Images', 'Buy Box', 'Category',
                    'Subcategory', 'Size tier', 'Dimensions', 'Weight', 'Creation date', 'Variation count',
                    'Net price', 'Sales trend (90 days)', 'Price trend (90 days)', 'Best sales period',
                    'Sales to reviews', 'Parent ASIN', 'Price per unit', 'Unit count', 'Pack form',
                    'Manufacturer', 'Unit Sales', 'Unit Sales Actuals', 'Total Revenue',
                    'Total Revenue Actuals', '时间'
                ]
                
                # 整理列顺序：先按期望顺序，再放多余的列
                existing_cols = [col for col in desired_order if col in final.columns]
                extra_cols = [col for col in final.columns if col not in desired_order]
                final = final[existing_cols + extra_cols]
                
                # 6. 输出结果
                buffer = save_df_to_buffer(final)
                out_name = f"merged_sales_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
                
                st.success(f"✅ 合并完成！\n"
                          f"总行数：{len(final):,} 行\n"
                          f"月份数：{len(month_columns)} 个月\n"
                          f"唯一 ASIN：{final['ASIN'].nunique():,}")
                
                st.dataframe(final.head(10), use_container_width=True)
                
                st.download_button(
                    label="📥 下载合并结果（Excel）",
                    data=buffer,
                    file_name=out_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
