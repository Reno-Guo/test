import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io
import zipfile
import tempfile
import calendar

def save_df_to_buffer(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    return buffer

def render_app_header(emoji_title: str, subtitle: str):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
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
    df = pd.read_csv(csv_path, encoding='utf-8', header=header_row, encoding_errors='ignore')
    return df

def excel_to_dataframe(excel_path: str, header_row: int = 0) -> pd.DataFrame:
    return pd.read_excel(excel_path, header=header_row)

def process_zip_files_with_preview(uploaded_file, header_row: int, file_type: str):
    if uploaded_file is None:
        return pd.DataFrame()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_dir)
        
        files = [f for f in os.listdir(temp_dir) if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
        if not files:
            st.warning(f"📂 {file_type}压缩包中未找到有效文件")
            return pd.DataFrame()
        
        dfs = []
        for f in files:
            fp = os.path.join(temp_dir, f)
            try:
                if f.lower().endswith('.csv'):
                    df = csv_to_dataframe(fp, header_row=header_row)
                else:
                    df = excel_to_dataframe(fp, header_row=header_row)
                
                with st.expander(f"📄 {file_type} - {f} 预览"):
                    st.write(f"**列名:** {list(df.columns)}")
                    st.write(f"**形状:** {df.shape}")
                    st.dataframe(df.head(3), use_container_width=True)
                dfs.append(df.reset_index(drop=True))
            except Exception as e:
                st.error(f"❌ 处理 {f} 失败: {str(e)[:100]}...")
        
        if not dfs:
            return pd.DataFrame()
        
        result = pd.concat(dfs, ignore_index=True, sort=False)
        return result

def process_zip_files(uploaded_file, header_row: int):
    if uploaded_file is None:
        return pd.DataFrame()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_dir)
        
        files = [f for f in os.listdir(temp_dir) if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
        if not files:
            return pd.DataFrame()
        
        dfs = []
        for f in files:
            fp = os.path.join(temp_dir, f)
            try:
                if f.lower().endswith('.csv'):
                    df = csv_to_dataframe(fp, header_row=header_row)
                else:
                    df = excel_to_dataframe(fp, header_row=header_row)
                dfs.append(df.reset_index(drop=True))
            except:
                continue
        
        if not dfs:
            return pd.DataFrame()
        
        result = pd.concat(dfs, ignore_index=True, sort=False)
        return result

def parse_month_year_to_yyyy_mm(col_name: str) -> str:
    """将 'December 2023' 或 'December-2023' 转为 '2023-12'"""
    clean = col_name.replace(',', '').replace('-', ' ').strip()
    parts = clean.split()
    if len(parts) < 2:
        return col_name  # 无法解析则原样返回
    month_name, year_str = parts[0], parts[1]
    try:
        month_num = list(calendar.month_name).index(month_name.capitalize())
        return f"{year_str}-{month_num:02d}"
    except ValueError:
        return col_name  # 无效月份名则原样返回

def sales_data_merge_app():
    render_app_header("🔗 销售数据合并工具", "合并月度收入、单位数据与ASIN详细信息（含标准时间格式）")
    
    st.markdown("### 📥 上传数据文件")
    col1, col2, col3 = st.columns(3)
    with col1:
        rev_zip = st.file_uploader("月度收入ZIP", type=["zip"], key="rev")
    with col2:
        units_zip = st.file_uploader("月度单位ZIP", type=["zip"], key="units")
    with col3:
        asin_zip = st.file_uploader("ASIN详情ZIP", type=["zip"], key="asin")
    
    st.divider()
    preview_btn = st.button("🔍 预览各文件内容", use_container_width=True)
    execute_btn = st.button("🚀 开始合并数据", use_container_width=True)
    
    if preview_btn:
        if not all([rev_zip, units_zip, asin_zip]):
            st.warning("⚠️ 请先上传全部三个文件")
            return
        
        with st.spinner("加载预览中..."):
            process_zip_files_with_preview(rev_zip, header_row=1, file_type="月度收入")
            process_zip_files_with_preview(units_zip, header_row=1, file_type="月度单位")
            process_zip_files_with_preview(asin_zip, header_row=0, file_type="ASIN详情")
    
    if execute_btn:
        if not all([rev_zip, units_zip, asin_zip]):
            st.warning("⚠️ 请上传所有三个ZIP文件")
            return
        
        with st.spinner("处理数据中..."):
            rev_df = process_zip_files(rev_zip, header_row=1)
            units_df = process_zip_files(units_zip, header_row=1)
            asin_df = process_zip_files(asin_zip, header_row=0)
            
            if rev_df.empty or units_df.empty or asin_df.empty:
                st.error("❌ 某个文件加载失败")
                return
            
            # 构建长格式数据
            month_cols = [col for col in rev_df.columns if col not in ['Product', 'Product Name', 'Brand', 'Total']]
            
            rev_long_list = []
            for col in month_cols:
                temp = rev_df[['Product', col]].dropna(subset=[col]).copy()
                temp.columns = ['Product', 'Total Revenue']
                time_val = parse_month_year_to_yyyy_mm(col)
                temp['时间'] = time_val
                rev_long_list.append(temp.reset_index(drop=True))
            
            if rev_long_list:
                rev_long_df = pd.concat(rev_long_list, ignore_index=True)
            else:
                rev_long_df = pd.DataFrame(columns=['Product', 'Total Revenue', '时间'])
            
            units_long_list = []
            for col in month_cols:
                temp = units_df[['Product', col]].dropna(subset=[col]).copy()
                temp.columns = ['Product', 'Unit Sales']
                time_val = parse_month_year_to_yyyy_mm(col)
                temp['时间'] = time_val
                units_long_list.append(temp.reset_index(drop=True))
            
            if units_long_list:
                units_long_df = pd.concat(units_long_list, ignore_index=True)
            else:
                units_long_df = pd.DataFrame(columns=['Product', 'Unit Sales', '时间'])
            
            # 合并收入和单位数据
            if not rev_long_df.empty and not units_long_df.empty:
                combined = rev_long_df.merge(units_long_df, on=['Product', '时间'], how='inner')
            else:
                st.error("❌ 无有效月度数据")
                return
            
            # 与ASIN详情合并
            final = asin_df.merge(combined, left_on='ASIN', right_on='Product', how='inner')
            
            # === 清理 _x / _y 列 ===
            if 'Total Revenue_x' in final.columns and 'Total Revenue_y' in final.columns:
                final['Total Revenue'] = final['Total Revenue_y']
                final = final.drop(columns=['Total Revenue_x', 'Total Revenue_y'])
            elif 'Total Revenue_y' in final.columns:
                final = final.rename(columns={'Total Revenue_y': 'Total Revenue'})
            elif 'Total Revenue_x' in final.columns:
                final = final.rename(columns={'Total Revenue_x': 'Total Revenue'})

            if 'Unit Sales_x' in final.columns and 'Unit Sales_y' in final.columns:
                final['Unit Sales'] = final['Unit Sales_y']
                final = final.drop(columns=['Unit Sales_x', 'Unit Sales_y'])
            elif 'Unit Sales_y' in final.columns:
                final = final.rename(columns={'Unit Sales_y': 'Unit Sales'})
            elif 'Unit Sales_x' in final.columns:
                final = final.rename(columns={'Unit Sales_x': 'Unit Sales'})

            if 'Product_x' in final.columns and 'Product_y' in final.columns:
                final['Product'] = final['Product_x']
                final = final.drop(columns=['Product_x', 'Product_y'])
            elif 'Product_y' in final.columns:
                final = final.rename(columns={'Product_y': 'Product'})
            elif 'Product_x' in final.columns:
                final = final.rename(columns={'Product_x': 'Product'})

            # === 按指定顺序重排列 ===
            desired_order = [
                'Product', 'ASIN', 'Brand', 'Price', 'BSR', 'Number of sellers', 'Fulfillment',
                'FBA fees (USD)', 'Ratings', 'Review count', 'Images', 'Buy Box', 'Category',
                'Subcategory', 'Size tier', 'Dimensions', 'Weight', 'Creation date', 'Variation count',
                'Net price', 'Sales trend (90 days)', 'Price trend (90 days)', 'Best sales period',
                'Sales to reviews', 'Parent ASIN', 'Price per unit', 'Unit count', 'Pack form',
                'Manufacturer', 'Unit Sales', 'Unit Sales Actuals', 'Total Revenue', 'Total Revenue Actuals', '时间'
            ]
            
            existing_cols = [col for col in desired_order if col in final.columns]
            extra_cols = [col for col in final.columns if col not in desired_order]
            final = final[existing_cols + extra_cols]
            
            if final.empty:
                st.warning("⚠️ 无匹配记录")
                return
            
            # 保存结果
            buffer = save_df_to_buffer(final)
            out_name = f"merged_sales_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
            
            st.success(f"✅ 合并完成！共 {len(final)} 行数据")
            st.dataframe(final.head(10), use_container_width=True)
            
            st.download_button(
                "📥 下载合并结果",
                data=buffer,
                file_name=out_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
