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

# === Concurrency-safe session + helpers ===
if "SID" not in st.session_state:
    st.session_state.SID = uuid4().hex[:6]

def unique_tmp_path(suggest_name: str, default_ext: str = ".xlsx") -> str:
    base, ext = os.path.splitext(suggest_name or f"result{default_ext}")
    ext = ext or default_ext
    return os.path.join("/tmp", f"{base}_{st.session_state.SID}_{uuid4().hex[:8]}{ext}")

@st.cache_data(ttl=1800, show_spinner=False)
def _read_excel_cached(file_or_path, sheet_name=0, engine=None):
    return pd.read_excel(file_or_path, sheet_name=sheet_name, engine=engine)

# App configuration
APP_CONFIG = {
    "app_title": "市场洞察小程序",
    "author": "海翼IDC团队",
    "version": "v1.2.0",
    "contact": "idc@oceanwing.com",
    "company": "Anker Oceanwing Inc."
}

# 处理价格列
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

# 合并数据表格功能
def merge_data_app():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: white; margin: 0; display: flex; align-items: center;">
            📊 MI/SI - 合并数据表格
        </h2>
        <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem;">将多个Excel文件合并为一个统一的数据表格</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📁 上传文件")
        uploaded_file = st.file_uploader(
            "选择一个 .zip 文件(包含需要合并的 Excel 文件)", 
            type=["zip"], 
            accept_multiple_files=False, 
            key="merge_files",
            help="支持包含.xlsx、.xls、.csv格式的ZIP压缩包"
        )
    
    with col2:
        st.markdown("#### 💾 输出设置")
        save_filename = st.text_input(
            "输出文件名", 
            value="merged_output.xlsx",
            key="merge_save",
            help="请输入合并后的文件名"
        )
    
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    with col_btn1:
        execute_btn = st.button("🚀 开始合并", key="merge_button", use_container_width=True)
    
    if execute_btn:
        if not uploaded_file or not save_filename:
            st.warning("⚠️ 请确保已选择 .zip 文件并输入文件名")
            return
        
        with st.spinner("🔄 正在处理文件，请稍候..."):
            save_path = unique_tmp_path(save_filename)
            
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    df_list = []
                    
                    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
                    temp_file_path = os.path.join(temp_dir, uploaded_file.name)
                    
                    with open(temp_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    if file_extension == '.zip':
                        with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)
                    
                    excel_files = [f for f in os.listdir(temp_dir) if f.endswith(('.xlsx', '.xls', '.csv'))]
                    
                    if not excel_files:
                        st.warning("📂 压缩文件中未找到任何 Excel 或 CSV 文件")
                        return
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, file_name in enumerate(excel_files):
                        file_path = os.path.join(temp_dir, file_name)
                        try:
                            status_text.text(f"正在处理: {file_name} ({idx+1}/{len(excel_files)})")
                            
                            if file_name.endswith('.xlsx'):
                                df = _read_excel_cached(file_path, engine='openpyxl')
                            elif file_name.endswith('.xls'):
                                df = _read_excel_cached(file_path, engine='xlrd')
                            elif file_name.endswith('.csv'):
                                df = pd.read_csv(file_path)
                            
                            df['时间'] = os.path.splitext(file_name)[0]
                            df = process_price_columns(df)
                            df_list.append(df)
                            
                            progress_bar.progress((idx + 1) / len(excel_files))
                        except Exception as e:
                            st.error(f"❌ 读取文件 {file_name} 失败:{e}")
                            continue
                    
                    status_text.empty()
                    progress_bar.empty()
                    
                    if df_list:
                        # 添加合并进度条
                        merge_progress = st.progress(0)
                        merge_status = st.empty()
                        merge_status.text("正在合并数据...")
                        merged_df = pd.concat(df_list, ignore_index=True)
                        merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
                        merge_progress.progress(1.0)
                        merge_status.text("合并完成")
                        merge_progress.empty()
                        merge_status.empty()
                        
                        buffer = io.BytesIO()
                        merged_df.to_excel(buffer, index=False, engine='openpyxl')
                        buffer.seek(0)
                        
                        st.success(f"✅ 成功合并 {len(df_list)} 个文件，共 {len(merged_df)} 行数据")
                        
                        col_download, col_save = st.columns(2)
                        with col_download:
                            st.download_button(
                                label="📥 下载合并后的文件",
                                data=buffer,
                                file_name=os.path.basename(save_filename),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_merged",
                                use_container_width=True
                            )
                        with col_save:
                            if st.checkbox("💾 同时保存到 /tmp 目录", key="save_merged"):
                                merged_df.to_excel(save_path, index=False, engine='openpyxl')
                                st.info(f"📁 文件已保存到 {save_path}")
                    else:
                        st.warning("⚠️ 没有可合并的数据")
            except Exception as e:
                st.error(f"❌ 处理压缩文件或合并文件时发生错误:{e}")

# 搜索流量洞察功能(仅生成源数据工作表)
def search_insight_app():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: white; margin: 0; display: flex; align-items: center;">
            🔍 SI - 搜索流量洞察
        </h2>
        <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem;">分析搜索关键词，识别品牌词与非品牌词</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 模板下载区域
    st.markdown("#### 📋 步骤 1: 下载数据模板")
    template_df = pd.DataFrame(columns=["搜索词", "搜索量", "品牌名称"])
    buffer = io.BytesIO()
    template_df.to_excel(buffer, index=False)
    buffer.seek(0)
    
    col_template1, col_template2, col_template3 = st.columns([1, 1, 2])
    with col_template1:
        st.download_button(
            label="📥 下载Excel模板",
            data=buffer,
            file_name="template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_template",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # 数据上传区域
    st.markdown("#### 📤 步骤 2: 上传填写好的数据文件")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "选择数据文件", 
            type=["xlsx", "xls"], 
            key="data_file",
            help="请上传按模板填写的Excel文件"
        )
    
    with col2:
        save_filename = st.text_input(
            "输出文件名", 
            value="search_insight_result.xlsx",
            key="save_folder",
            help="请输入输出文件名"
        )
    
    st.markdown("---")
    
    # 产品参数输入
    st.markdown("#### ⚙️ 步骤 3: 输入产品参数(可选)")
    
    col_param1, col_param2 = st.columns(2)
    with col_param1:
        param_names = st.text_input(
            "参数名(用逗号分隔)", 
            placeholder="例如: 颜色,尺寸,材质",
            key="param_names",
            help="输入需要分析的产品参数名称"
        )
    
    with col_param2:
        param_values = st.text_area(
            "具体参数(每行一个参数组,用逗号分隔)", 
            placeholder="例如:\n红,蓝,绿\n小,中,大",
            key="param_values",
            help="每行对应一个参数的所有可能值",
            height=100
        )
    
    st.markdown("---")
    
    # 执行按钮
    col_exec1, col_exec2, col_exec3 = st.columns([1, 1, 2])
    with col_exec1:
        execute_btn = st.button("🚀 开始分析", key="execute_button", use_container_width=True)
    
    if execute_btn:
        if not uploaded_file or not save_filename:
            st.warning("⚠️ 请确保已上传数据文件并输入输出文件名")
            return
        
        with st.spinner("🔄 正在分析数据，请稍候..."):
            save_path = unique_tmp_path(save_filename)
            
            try:
                df = _read_excel_cached(uploaded_file)
                if df.empty:
                    st.warning("📂 上传的文件为空，请检查数据文件")
                    return
                
                # 处理产品参数(支持中英文逗号)
                product_parameters = []
                if param_names and param_values:
                    param_names_list = [name.strip() for name in re.split(r'[,\uff0c]', param_names) if name.strip()]
                    param_values_list = []
                    for v in param_values.split('\n'):
                        values = [val.strip() for val in re.split(r'[,\uff0c]', v) if val.strip()]
                        if values:
                            param_values_list.append(values)
                    product_parameters = list(zip(param_names_list, param_values_list)) if param_names_list and param_values_list else []
                
                # 初始化列
                df['品牌'] = ''
                df['特性参数'] = ''
                for param_name, _ in product_parameters:
                    df[param_name] = ''
                
                results = []
                brand_words_list = []
                translator_punct = str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
                
                # 处理搜索词
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for index, row in df.iterrows():
                    status_text.text(f"正在分析第 {index+1}/{len(df)} 条数据...")
                    
                    search_word = str(row['搜索词']).lower()
                    search_volumn = row['搜索量'] if pd.notna(row['搜索量']) else 0
                    
                    matched_brands = []
                    found_brand = False
                    for brand in df['品牌名称'].dropna().unique():
                        brand_str = str(brand).lower()
                        if len(brand_str) <= 5:
                            pattern = rf'\b{re.escape(brand_str)}\b'
                            if re.search(pattern, search_word):
                                matched_brands.append(brand_str)
                                found_brand = True
                        else:
                            if brand_str in search_word or \
                               brand_str.translate(translator_punct) in search_word or \
                               brand_str.replace(' ', '') in search_word or \
                               brand_str.translate(translator_punct).replace(' ', '') in search_word:
                                matched_brands.append(brand_str)
                                found_brand = True
                    
                    df.at[index, '品牌'] = ','.join(set(matched_brands))
                    
                    matched_params = []
                    for param_name, param_values in product_parameters:
                        matched_values = [str(param).lower() for param in param_values if str(param).lower() in search_word]
                        df.at[index, param_name] = ','.join(set(matched_values))
                        matched_params.extend(matched_values)
                    df.at[index, '特性参数'] = ','.join(set(matched_params))
                    
                    if found_brand:
                        results.append('Branded KWs')
                        for brand in matched_brands:
                            brand_words_list.append({'品牌名称': brand, '搜索量': search_volumn})
                    else:
                        results.append('Non-Branded KWs')
                    
                    progress_bar.progress((index + 1) / len(df))
                
                df['词性'] = results
                
                status_text.empty()
                progress_bar.empty()
                
                # 添加保存进度条
                save_progress = st.progress(0)
                save_status = st.empty()
                save_status.text("正在保存到Excel...")
                save_progress.progress(0.5)
                
                # 保存到 Excel(仅源数据工作表)
                workbook = Workbook()
                if "Sheet" in workbook.sheetnames:
                    workbook.remove(workbook["Sheet"])
                
                ws_source = workbook.create_sheet('源数据')
                for r in dataframe_to_rows(df, index=False, header=True):
                    ws_source.append(r)
                
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                output_filename = f"result_{timestamp}.xlsx"
                output_path = os.path.join("/tmp", output_filename)
                
                buffer = io.BytesIO()
                workbook.save(buffer)
                buffer.seek(0)
                save_progress.progress(1.0)
                save_status.text("保存完成")
                save_progress.empty()
                save_status.empty()
                
                branded_count = results.count('Branded KWs')
                non_branded_count = results.count('Non-Branded KWs')
                
                st.success(f"✅ 分析完成! 品牌词: {branded_count} 条 | 非品牌词: {non_branded_count} 条")
                
                col_download, col_save = st.columns(2)
                with col_download:
                    st.download_button(
                        label="📥 下载处理结果",
                        data=buffer,
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_result",
                        use_container_width=True
                    )
                with col_save:
                    if st.checkbox("💾 同时保存到 /tmp 目录", key="save_result"):
                        workbook.save(output_path)
                        st.info(f"📁 文件已保存到 {output_path}")
            
            except Exception as e:
                st.error(f"❌ 处理数据时发生错误:{e}")

# 搜索流量洞察可视化功能
def aggregate_top_n(df, value_col, name_col, top_n=10):
    df = df.copy()
    df[name_col] = df[name_col].astype(str)
    df = df.sort_values(by=value_col, ascending=False).reset_index(drop=True)

    if len(df) > top_n:
        top_df = df.iloc[:top_n]
        others_df = df.iloc[top_n:]
        others_total = others_df[value_col].sum()
        others_row = pd.DataFrame([{name_col: 'Others', value_col: others_total}])
        final_df = pd.concat([top_df[[name_col, value_col]], others_row], ignore_index=True)
    else:
        final_df = df[[name_col, value_col]]
    
    return final_df

def pie_chart(df, value_col, name_col, title):
    df = df.copy()

    df[name_col] = df[name_col].astype(str)
    df = df.sort_values(by=value_col, ascending=False).reset_index(drop=True)
    if 'Others' in df[name_col].values:
        categories = [name for name in df[name_col] if name != 'Others'] + ['Others']
        df[name_col] = pd.Categorical(df[name_col], categories=categories, ordered=True)
    else:
        df[name_col] = pd.Categorical(df[name_col], ordered=True)
    
    business_palette = [
        "#4C8EDA", "#FFA14E", "#F25C5C", "#6BD0C1", "#58C27D", "#F7C948",
        "#B685D6", "#FF90B3", "#BC8D6E", "#C9C9C9", "#81D3EB"
    ]

    fig = px.pie(
        df,
        values=value_col,
        names=name_col,
        title=title,
        category_orders={name_col: df[name_col].cat.categories.tolist()},
        color_discrete_sequence=business_palette
    )
    fig.update_traces(textinfo='label+percent', sort=False)

    fig.update_layout(
        height=900,
        legend=dict(orientation="v", x=0.8, y=0.5, font=dict(size=16)),
        margin=dict(l=20, r=150, t=50, b=50),
        font=dict(size=16)
    )

    st.plotly_chart(fig, use_container_width=True)

def search_insight_viz_app():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: white; margin: 0; display: flex; align-items: center;">
            📈 SI - 搜索流量洞察: 聚合和可视化
        </h2>
        <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem;">生成多维度数据分析报表和可视化图表</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📁 上传源数据文件")
        uploaded_file = st.file_uploader(
            "选择包含源数据的 Excel 文件(完成检查确认无误)", 
            type=["xlsx", "xls"], 
            key="viz_data_file",
            help="请上传包含'源数据'工作表的Excel文件"
        )
    
    with col2:
        st.markdown("#### 💾 输出设置")
        save_filename = st.text_input(
            "输出文件名", 
            value="viz_result.xlsx",
            key="viz_save_folder",
            help="请输入输出文件名"
        )

    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    with col_btn1:
        execute_btn = st.button("🚀 开始可视化", key="viz_execute_button", use_container_width=True)

    if execute_btn:
        if not uploaded_file or not save_filename:
            st.warning("⚠️ 请确保已上传数据文件并输入输出文件名")
            return

        with st.spinner("🔄 正在生成可视化报表，请稍候..."):
            save_path = unique_tmp_path(save_filename)

            try:
                df = _read_excel_cached(uploaded_file, sheet_name='源数据')
                if df.empty:
                    st.warning("📂 上传的文件为空或不包含'源数据'工作表，请检查数据文件")
                    return

                # 添加品牌词处理进度条
                brand_progress = st.progress(0)
                brand_status = st.empty()
                brand_status.text("正在处理品牌词...")
                brand_words_list = []
                for index, row in df.iterrows():
                    search_volumn = row['搜索量'] if pd.notna(row['搜索量']) else 0
                    brand_value = str(row['品牌']) if not pd.isna(row['品牌']) else ''
                    matched_brands = brand_value.split(',') if brand_value else []
                    for brand in matched_brands:
                        if brand:
                            brand_words_list.append({'品牌名称': brand, '搜索量': search_volumn})
                    if index % max(1, len(df) // 10) == 0 or index == len(df) - 1:
                        brand_progress.progress((index + 1) / len(df))
                brand_words_df = pd.DataFrame(brand_words_list)
                if not brand_words_df.empty:
                    brand_words_df = brand_words_df.groupby('品牌名称', as_index=False)['搜索量'].sum()
                    brand_words_df = aggregate_top_n(brand_words_df, value_col='搜索量', name_col='品牌名称')
                brand_status.text("品牌词处理完成")
                brand_progress.empty()
                brand_status.empty()

                # 添加参数热图处理进度条
                param_progress = st.progress(0)
                param_status = st.empty()
                param_status.text("正在处理参数...")
                param_heats = {}
                param_columns = [col for col in df.columns if col not in ['搜索词', '搜索量', '品牌名称', '品牌', '特性参数', '词性']]
                for col_idx, column in enumerate(param_columns):
                    param_heats[column] = []
                    for index, row in df.iterrows():
                        search_volumn = row['搜索量'] if pd.notna(row['搜索量']) else 0
                        param_value = str(row[column]) if not pd.isna(row[column]) else ''
                        matched_values = param_value.split(',') if param_value else []
                        for param in matched_values:
                            if param:
                                param_heats[column].append({'参数值': param, '搜索量': search_volumn})
                    param_progress.progress((col_idx + 1) / len(param_columns))
                param_status.text("参数处理完成")
                param_progress.empty()
                param_status.empty()

                # 添加工作簿保存进度条
                save_progress = st.progress(0)
                save_status = st.empty()
                save_status.text("正在生成Excel工作簿...")
                save_progress.progress(0.3)

                workbook = Workbook()
                if "Sheet" in workbook.sheetnames:
                    workbook.remove(workbook["Sheet"])

                ws_source = workbook.create_sheet('源数据')
                for r in dataframe_to_rows(df, index=False, header=True):
                    ws_source.append(r)
                save_progress.progress(0.6)

                if not brand_words_df.empty:
                    ws_brands = workbook.create_sheet('品牌词拆解')
                    for r in dataframe_to_rows(brand_words_df, index=False, header=True):
                        ws_brands.append(r)
                save_progress.progress(0.7)

                for param_idx, (param_name, heats) in enumerate(param_heats.items()):
                    if heats:
                        param_df = pd.DataFrame(heats).groupby('参数值', as_index=False)['搜索量'].sum()
                        param_df = aggregate_top_n(param_df, value_col='搜索量', name_col='参数值')
                        clean_sheet_name = param_name[:31].translate(str.maketrans('', '', '\/?*[]'))
                        ws_param = workbook.create_sheet(f"{clean_sheet_name}拆解")
                        for r in dataframe_to_rows(param_df, index=False, header=True):
                            ws_param.append(r)
                    if param_idx % max(1, len(param_heats) // 5) == 0 or param_idx == len(param_heats) - 1:
                        save_progress.progress(0.7 + (0.3 * (param_idx + 1) / len(param_heats)))
                save_progress.progress(1.0)

                df_selected = df[['词性', '搜索量']].groupby('词性').sum().reset_index()
                if not df_selected.empty:
                    df_selected = aggregate_top_n(df_selected, value_col='搜索量', name_col='词性')
                    ws_traffic = workbook.create_sheet('品类流量结构')
                    for r in dataframe_to_rows(df_selected, index=False, header=True):
                        ws_traffic.append(r)

                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                output_filename = f"viz_result_{timestamp}.xlsx"
                output_path = os.path.join("/tmp", output_filename)

                buffer = io.BytesIO()
                workbook.save(buffer)
                buffer.seek(0)
                save_status.text("工作簿生成完成")
                save_progress.empty()
                save_status.empty()

                st.success("✅ 数据处理完成，正在生成可视化图表...")

                st.markdown("### 📊 数据可视化")

                if not brand_words_df.empty:
                    with st.container():
                        pie_chart(brand_words_df, '搜索量', '品牌名称', "品牌词拆解")

                for param_name, heats in param_heats.items():
                    if heats:
                        param_df = pd.DataFrame(heats).groupby('参数值', as_index=False)['搜索量'].sum()
                        param_df = aggregate_top_n(param_df, value_col='搜索量', name_col='参数值')
                        with st.container():
                            pie_chart(param_df, '搜索量', '参数值', f"{param_name} 参数搜索量分布")

                if not df_selected.empty:
                    with st.container():
                        pie_chart(df_selected, '搜索量', '词性', "流量结构")

                st.markdown("---")
                
                col_download, col_save = st.columns(2)
                with col_download:
                    st.download_button(
                        label="📥 下载完整报表",
                        data=buffer,
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="viz_download_result",
                        use_container_width=True
                    )
                with col_save:
                    if st.checkbox("💾 同时保存到 /tmp 目录", key="viz_save_result"):
                        workbook.save(output_path)
                        st.info(f"📁 文件已保存到 {output_path}")

            except Exception as e:
                st.error(f"❌ 处理数据时发生错误:{e}")

# 新功能:删除第一行并重新打包ZIP
def data_clean_app():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: white; margin: 0; display: flex; align-items: center;">
            🧹 DC - 数据清理: 删除第一行
        </h2>
        <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem;">批量删除Excel/CSV文件的第一行数据并重新打包</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📁 上传文件")
        uploaded_file = st.file_uploader(
            "选择一个 .zip 文件(包含 XLSX 或 CSV 文件)", 
            type=["zip"], 
            accept_multiple_files=False, 
            key="clean_files",
            help="支持包含.xlsx、.xls、.csv格式的ZIP压缩包"
        )
    
    with col2:
        st.markdown("#### 💾 输出设置")
        output_filename = st.text_input(
            "输出文件名", 
            value="cleaned_files.zip", 
            key="clean_save",
            help="请输入输出ZIP文件名"
        )
    
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    with col_btn1:
        execute_btn = st.button("🚀 开始清理", key="clean_button", use_container_width=True)
    
    if execute_btn:
        if not uploaded_file or not output_filename:
            st.warning("⚠️ 请确保已选择 .zip 文件并输入输出文件名")
            return
        
        with st.spinner("🔄 正在清理文件，请稍候..."):
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_zip_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_zip_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    data_files = [f for f in os.listdir(temp_dir) if f.endswith(('.xlsx', '.xls', '.csv'))]
                    
                    if not data_files:
                        st.warning("📂 压缩文件中未找到任何 XLSX、XLS 或 CSV 文件")
                        return
                    
                    processed_files = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, file_name in enumerate(data_files):
                        file_path = os.path.join(temp_dir, file_name)
                        try:
                            status_text.text(f"正在处理: {file_name} ({idx+1}/{len(data_files)})")
                            
                            if file_name.endswith(('.xlsx', '.xls')):
                                df = pd.read_excel(file_path, engine='openpyxl' if file_name.endswith('.xlsx') else 'xlrd')
                            elif file_name.endswith('.csv'):
                                df = pd.read_csv(file_path, header=None)
                            
                            df = df.iloc[1:].reset_index(drop=True)
                            
                            processed_path = os.path.join(temp_dir, f"cleaned_{file_name}")
                            if file_name.endswith(('.xlsx', '.xls')):
                                df.to_excel(processed_path, index=False, engine='openpyxl')
                            elif file_name.endswith('.csv'):
                                df.to_csv(processed_path, index=False)
                            
                            processed_files.append(processed_path)
                            progress_bar.progress((idx + 1) / len(data_files))
                        except Exception as e:
                            st.error(f"❌ 处理文件 {file_name} 失败:{e}")
                            continue
                    
                    status_text.empty()
                    progress_bar.empty()
                    
                    if processed_files:
                        # 添加打包进度条
                        zip_progress = st.progress(0)
                        zip_status = st.empty()
                        zip_status.text("正在打包ZIP文件...")
                        buffer = io.BytesIO()
                        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                            for proc_idx, proc_path in enumerate(processed_files):
                                arcname = os.path.basename(proc_path).replace("cleaned_", "")
                                new_zip.write(proc_path, arcname=arcname)
                                zip_progress.progress((proc_idx + 1) / len(processed_files))
                        buffer.seek(0)
                        zip_status.text("打包完成")
                        zip_progress.empty()
                        zip_status.empty()
                        
                        st.success(f"✅ 成功清理 {len(processed_files)} 个文件")
                        
                        st.download_button(
                            label="📥 下载清理后的 ZIP 文件",
                            data=buffer,
                            file_name=output_filename,
                            mime="application/zip",
                            key="download_cleaned",
                            use_container_width=True
                        )
                    else:
                        st.warning("⚠️ 没有可清理的文件")
            except Exception as e:
                st.error(f"❌ 处理 ZIP 文件时发生错误:{e}")

# 主应用程序
def main():
    st.set_page_config(
        page_title=APP_CONFIG["app_title"], 
        layout="wide",
        page_icon="📊",
        initial_sidebar_state="collapsed"
    )
    
    # 自定义CSS优化UI,主色调 #00a6e4
    st.markdown("""
    <style>
        /* 全局字体和背景 */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }
        
        .main {
            background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
        }
        
        /* 标题颜色 */
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
            font-weight: 600 !important;
        }
        
        /* 按钮样式 */
        .stButton > button {
            background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            font-size: 15px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 166, 228, 0.2);
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #0088c2 0%, #006a99 100%);
            box-shadow: 0 6px 12px rgba(0, 166, 228, 0.3);
            transform: translateY(-2px);
        }
        
        /* 下载按钮样式 */
        .stDownloadButton > button {
            background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            font-size: 15px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 166, 228, 0.2);
        }
        
        .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #0088c2 0%, #006a99 100%);
            box-shadow: 0 6px 12px rgba(0, 166, 228, 0.3);
            transform: translateY(-2px);
        }
        
        /* 文件上传器样式 */
        .stFileUploader {
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        
        [data-testid="stFileUploadDropzone"] {
            border: 2px dashed #00a6e4;
            border-radius: 8px;
            background: #f8fcff;
        }
        
        /* 输入框样式 */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 0.6rem;
            transition: all 0.3s ease;
            font-size: 14px;
        }
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #00a6e4;
            box-shadow: 0 0 0 3px rgba(0, 166, 228, 0.1);
        }
        
        /* 进度条样式 */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #00a6e4 0%, #0088c2 100%);
        }
        
        /* 成功/错误/警告消息样式 */
        .stSuccess {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            border-left: 4px solid #28a745;
            border-radius: 8px;
            padding: 1rem;
        }
        
        .stError {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border-left: 4px solid #dc3545;
            border-radius: 8px;
            padding: 1rem;
        }
        
        .stWarning {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            border-left: 4px solid #ffc107;
            border-radius: 8px;
            padding: 1rem;
        }
        
        .stInfo {
            background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
            border-left: 4px solid #00a6e4;
            border-radius: 8px;
            padding: 1rem;
        }
        
        /* 复选框样式 */
        .stCheckbox {
            font-size: 14px;
        }
        
        /* 分隔线样式 */
        hr {
            margin: 2rem 0;
            border: none;
            border-top: 2px solid #e0e0e0;
        }
        
        /* 卡片效果 */
        div[data-testid="column"] {
            background: white;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        /* Plotly图表容器 */
        .js-plotly-plot {
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 页面头部
    st.markdown("""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2.5rem 2rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 8px 16px rgba(0,0,0,0.15);">
        <h1 style="color: white; margin: 0; font-size: 2.5rem; font-weight: 700;">
            📊 市场洞察小程序
        </h1>
        <div style="display: flex; gap: 2rem; margin-top: 1rem; flex-wrap: wrap;">
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;">
                <strong>版本:</strong> v1.2.0
            </span>
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;">
                <strong>作者:</strong> 海翼IDC团队
            </span>
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;">
                <strong>公司:</strong> Anker Oceanwing Inc.
            </span>
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;">
                <strong>联系:</strong> idc@oceanwing.com
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 功能导航
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h3 style="margin-top: 0; color: #333;">🎯 功能导航</h3>
        <p style="color: #666; margin-bottom: 0;">选择下方功能模块开始您的数据分析之旅</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 功能模块
    tabs = st.tabs([
        "📊 合并数据表格",
        "🔍 搜索流量洞察",
        "📈 流量可视化分析",
        "🧹 数据清理工具"
    ])
    
    with tabs[0]:
        merge_data_app()
    
    with tabs[1]:
        search_insight_app()
    
    with tabs[2]:
        search_insight_viz_app()
    
    with tabs[3]:
        data_clean_app()
    
    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem 0;">
        <p style="margin: 0;">© Anker Oceanwing Inc. | 海翼IDC团队</p>
        <p style="margin: 0.5rem 0 0 0; font-size: 13px;">市场洞察小程序 v1.2.0 - 让数据分析更简单</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
