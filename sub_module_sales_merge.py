import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io
import zipfile
import tempfile
from uuid import uuid4

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

def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

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
                dfs.append(df)
            except Exception as e:
                st.error(f"❌ 处理 {f} 失败: {str(e)[:100]}...")
        
        if not dfs:
            return pd.DataFrame()
        
        # 安全合并：重置索引 + 统一列名类型
        for i, df in enumerate(dfs):
            df.columns = [str(col).strip() for col in df.columns]  # 强制转为字符串
            dfs[i] = df.reset_index(drop=True)
        
        result = pd.concat(dfs, ignore_index=True, sort=False)
        return result

def sales_data_merge_app():
    render_app_header("🔗 销售数据合并工具（仅保留三表匹配项）", "支持月度收入、单位销量与ASIN详情内连接合并")
    
    st.markdown("### 📥 上传三个ZIP数据包")
    col1, col2, col3 = st.columns(3)
    with col1:
        rev_zip = st.file_uploader("📦 月度收入 (by month rev.)", type=["zip"], key="rev")
    with col2:
        units_zip = st.file_uploader("📦 月度单位 (by month units)", type=["zip"], key="units")
    with col3:
        asin_zip = st.file_uploader("📦 ASIN详情数据", type=["zip"], key="asin")
    
    st.divider()
    preview_btn = st.button("🔍 预览各文件内容", use_container_width=True)
    execute_btn = st.button("🚀 执行内连接合并", use_container_width=True)
    
    if preview_btn:
        if not all([rev_zip, units_zip, asin_zip]):
            st.warning("⚠️ 请先上传全部三个文件")
            return
        
        with st.spinner("加载预览中..."):
            rev_df = process_zip_files_with_preview(rev_zip, header_row=1, file_type="月度收入")
            units_df = process_zip_files_with_preview(units_zip, header_row=1, file_type="月度单位")
            asin_df = process_zip_files_with_preview(asin_zip, header_row=0, file_type="ASIN详情")
    
    if execute_btn:
        if not all([rev_zip, units_zip, asin_zip]):
            st.warning("⚠️ 请上传全部三个ZIP文件")
            return
        
        with st.spinner("🔄 正在处理数据..."):
            rev_df = process_zip_files_with_preview(rev_zip, header_row=1, file_type="")
            units_df = process_zip_files_with_preview(units_zip, header_row=1, file_type="")
            asin_df = process_zip_files_with_preview(asin_zip, header_row=0, file_type="")
            
            if rev_df.empty or units_df.empty or asin_df.empty:
                st.error("❌ 某个文件未能正确加载")
                return
            
            # 列检查
            for name, df, cols in [("月度收入", rev_df, ['Product']), ("月度单位", units_df, ['Product']), ("ASIN详情", asin_df, ['ASIN'])]:
                missing = [c for c in cols if c not in df.columns]
                if missing:
                    st.error(f"❌ {name} 缺少列: {missing}。现有列: {list(df.columns)}")
                    return
            
            # === 构建长格式收入数据 ===
            rev_long_list = []
            skip_cols = {'Product', 'Product Name', 'Brand', 'Total'}
            for col in rev_df.columns:
                if col in skip_cols:
                    continue
                col_str = str(col).strip()
                if not col_str:
                    continue
                temp = rev_df[['Product', col]].dropna(subset=[col]).copy()
                temp.columns = ['Product', 'Total Revenue']
                # 解析时间
                try:
                    dt = datetime.strptime(col_str, '%B %Y')
                    time_val = dt.strftime('%Y-%m')
                except:
                    try:
                        dt = datetime.strptime(col_str, '%b-%y')
                        time_val = dt.strftime('%Y-%m')
                    except:
                        time_val = col_str
                temp['时间'] = time_val
                rev_long_list.append(temp)
            
            if rev_long_list:
                rev_long_df = pd.concat([
                    df[['Product', 'Total Revenue', '时间']].reset_index(drop=True)
                    for df in rev_long_list
                ], ignore_index=True)
            else:
                rev_long_df = pd.DataFrame(columns=['Product', 'Total Revenue', '时间'])
            
            # === 构建长格式单位数据 ===
            units_long_list = []
            for col in units_df.columns:
                if col in skip_cols:
                    continue
                col_str = str(col).strip()
                if not col_str:
                    continue
                temp = units_df[['Product', col]].dropna(subset=[col]).copy()
                temp.columns = ['Product', 'Unit Sales']
                try:
                    dt = datetime.strptime(col_str, '%B %Y')
                    time_val = dt.strftime('%Y-%m')
                except:
                    try:
                        dt = datetime.strptime(col_str, '%b-%y')
                        time_val = dt.strftime('%Y-%m')
                    except:
                        time_val = col_str
                temp['时间'] = time_val
                units_long_list.append(temp)
            
            if units_long_list:
                units_long_df = pd.concat([
                    df[['Product', 'Unit Sales', '时间']].reset_index(drop=True)
                    for df in units_long_list
                ], ignore_index=True)
            else:
                units_long_df = pd.DataFrame(columns=['Product', 'Unit Sales', '时间'])
            
            # === 合并收入与单位 ===
            if not rev_long_df.empty and not units_long_df.empty:
                combined = rev_long_df.merge(
                    units_long_df,
                    on=['Product', '时间'],
                    how='inner'
                )
            elif not rev_long_df.empty:
                combined = rev_long_df.copy()
                combined['Unit Sales'] = pd.NA
            elif not units_long_df.empty:
                combined = units_long_df.copy()
                combined['Total Revenue'] = pd.NA
            else:
                st.error("❌ 无有效月度数据")
                return
            
            # === 与ASIN详情内连接 ===
            final = asin_df.merge(
                combined,
                left_on='ASIN',
                right_on='Product',
                how='inner'
            )
            
            if final.empty:
                st.warning("⚠️ 三表无共同匹配项（检查 Product 与 ASIN 是否对应）")
                return
            
            # 清理重复列
            if 'Product_x' in final.columns and 'Product_y' in final.columns:
                final = final.drop(columns=['Product_y']).rename(columns={'Product_x': 'Product'})
            elif 'Product_y' in final.columns:
                final = final.drop(columns=['Product_y'])
            
            # 输出结果
            buffer = save_df_to_buffer(final)
            out_name = f"merged_sales_{get_timestamp()}.xlsx"
            out_path = f"/tmp/{out_name}"
            final.to_excel(out_path, index=False)
            
            st.success(f"✅ 合并成功！共 {len(final)} 行匹配记录")
            st.markdown("### 📊 结果预览")
            st.dataframe(final.head(10), use_container_width=True)
            
            st.download_button(
                "📥 下载合并结果",
                data=buffer,
                file_name=out_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
