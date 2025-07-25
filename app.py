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
import json

# 合并数据表格功能
def merge_data_app():
    with st.expander("合并数据表格", expanded=False):
        st.header("合并数据表格")
        
        uploaded_file = st.file_uploader("选择一个 .zip 文件（包含需要合并的 Excel 文件）", type=["zip"], accept_multiple_files=False, key="merge_files")
        save_filename = st.text_input("请输入合并后的文件名（例如：output.xlsx）", key="merge_save")
        
        if st.button("合并文件", key="merge_button"):
            if not uploaded_file or not save_filename:
                st.warning("请确保已选择 .zip 文件并输入文件名")
                return
            
            save_path = os.path.join("/tmp", save_filename) if not save_filename.startswith("/tmp") else save_filename
            
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
                        st.warning("压缩文件中未找到任何 Excel 或 CSV 文件")
                        return
                    
                    for file_name in excel_files:
                        file_path = os.path.join(temp_dir, file_name)
                        try:
                            if file_name.endswith('.xlsx'):
                                df = pd.read_excel(file_path, engine='openpyxl')
                            elif file_name.endswith('.xls'):
                                df = pd.read_excel(file_path, engine='xlrd')
                            elif file_name.endswith('.csv'):
                                df = pd.read_csv(file_path)
                            df['时间'] = os.path.splitext(file_name)[0]
                            df = process_price_columns(df)
                            df_list.append(df)
                        except Exception as e:
                            st.error(f"读取文件 {file_name} 失败：{e}")
                            continue
                    
                    if df_list:
                        merged_df = pd.concat(df_list, ignore_index=True)
                        merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
                        
                        buffer = io.BytesIO()
                        merged_df.to_excel(buffer, index=False, engine='openpyxl')
                        buffer.seek(0)
                        st.download_button(
                            label="下载合并后的文件",
                            data=buffer,
                            file_name=os.path.basename(save_filename),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_merged"
                        )
                        st.success(f"表格已成功合并，可通过下载按钮获取文件")
                        if st.checkbox("保存到 /tmp 目录", key="save_merged"):
                            merged_df.to_excel(save_path, index=False, engine='openpyxl')
                            st.success(f"文件已保存到 {save_path}")
                    else:
                        st.warning("没有可合并的数据")
            except Exception as e:
                st.error(f"处理压缩文件或合并文件时发生错误：{e}")

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

# 搜索流量洞察功能（仅生成源数据工作表）
def search_insight_app():
    with st.expander("搜索流量洞察", expanded=False):
        st.header("搜索流量洞察")
        
        st.subheader("模板下载")
        template_df = pd.DataFrame(columns=["搜索词", "搜索量", "品牌名称"])
        buffer = io.BytesIO()
        template_df.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            label="下载模板",
            data=buffer,
            file_name="template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_template"
        )
        
        uploaded_file = st.file_uploader("选择数据文件", type=["xlsx", "xls"], key="data_file")
        save_filename = st.text_input("请输入输出文件名（例如：result.xlsx）", key="save_folder")
        
        st.subheader("输入产品参数（可选）")
        param_names = st.text_input("参数名（用逗号分隔，如 颜色,尺寸，可留空）", key="param_names")
        param_values = st.text_area("具体参数（每行一个参数组，用逗号分隔，如 红,蓝\n小,大，可留空）", key="param_values")
        
        if st.button("执行", key="execute_button"):
            if not uploaded_file or not save_filename:
                st.warning("请确保已上传数据文件并输入输出文件名")
                return
            
            save_path = os.path.join("/tmp", save_filename) if not save_filename.startswith("/tmp") else save_filename
            
            try:
                df = pd.read_excel(uploaded_file)
                if df.empty:
                    st.warning("上传的文件为空，请检查数据文件")
                    return
                
                product_parameters = []
                if param_names and param_values:
                    param_names_list = [name.strip() for name in re.split(r'[,\uff0c]', param_names) if name.strip()]
                    param_values_list = []
                    for v in param_values.split('\n'):
                        values = [val.strip() for val in re.split(r'[,\uff0c]', v) if val.strip()]
                        if values:
                            param_values_list.append(values)
                    product_parameters = list(zip(param_names_list, param_values_list)) if param_names_list and param_values_list else []
                
                df['品牌'] = ''
                df['特性参数'] = ''
                for param_name, _ in product_parameters:
                    df[param_name] = ''
                
                results = []
                brand_words_list = []
                translator_punct = str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
                
                for index, row in df.iterrows():
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
                
                df['词性'] = results
                
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
                
                st.download_button(
                    label="下载处理结果",
                    data=buffer,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_result"
                )
                st.success(f"数据处理完成，可通过下载按钮获取文件")
                if st.checkbox("保存到 /tmp 目录", key="save_result"):
                    workbook.save(output_path)
                    st.success(f"文件已保存到 {output_path}")
            
            except Exception as e:
                st.error(f"处理数据时发生错误：{e}")

# 搜索流量洞察可视化功能
def search_insight_viz_app():
    with st.expander("搜索流量洞察可视化", expanded=False):
        st.header("搜索流量洞察可视化")
        
        uploaded_file = st.file_uploader("选择包含源数据的 Excel 文件", type=["xlsx", "xls"], key="viz_data_file")
        save_filename = st.text_input("请输入输出文件名（例如：viz_result.xlsx）", key="viz_save_folder")
        
        if st.button("执行可视化", key="viz_execute_button"):
            if not uploaded_file or not save_filename:
                st.warning("请确保已上传数据文件并输入输出文件名")
                return
            
            save_path = os.path.join("/tmp", save_filename) if not save_filename.startswith("/tmp") else save_filename
            
            try:
                df = pd.read_excel(uploaded_file, sheet_name='源数据')
                if df.empty:
                    st.warning("上传的文件为空或不包含‘源数据’工作表，请检查数据文件")
                    return
                
                brand_words_list = []
                translator_punct = str.maketrans('', '', '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
                
                for index, row in df.iterrows():
                    search_word = str(row['搜索词']).lower()
                    search_volumn = row['搜索量'] if pd.notna(row['搜索量']) else 0
                    brand_value = str(row['品牌']) if not pd.isna(row['品牌']) else ''
                    matched_brands = brand_value.split(',') if brand_value else []
                    for brand in matched_brands:
                        if brand:
                            brand_words_list.append({'品牌名称': brand, '搜索量': search_volumn})
                
                brand_words_df = pd.DataFrame(brand_words_list)
                if not brand_words_df.empty:
                    brand_words_df = brand_words_df.groupby('品牌名称', as_index=False)['搜索量'].sum().sort_values(by='搜索量', ascending=False)
                
                param_heats = {}
                for column in df.columns:
                    if column not in ['搜索词', '搜索量', '品牌名称', '品牌', '特性参数', '词性']:
                        param_heats[column] = []
                        for index, row in df.iterrows():
                            search_word = str(row['搜索词']).lower()
                            search_volumn = row['搜索量'] if pd.notna(row['搜索量']) else 0
                            param_value = str(row[column]) if not pd.isna(row[column]) else ''
                            matched_values = param_value.split(',') if param_value else []
                            for param in matched_values:
                                if param:
                                    param_heats[column].append({'参数值': param, '搜索量': search_volumn})
                
                workbook = Workbook()
                if "Sheet" in workbook.sheetnames:
                    workbook.remove(workbook["Sheet"])
                
                ws_source = workbook.create_sheet('源数据')
                for r in dataframe_to_rows(df, index=False, header=True):
                    ws_source.append(r)
                
                if not brand_words_df.empty:
                    ws_brands = workbook.create_sheet('品牌词拆解')
                    for r in dataframe_to_rows(brand_words_df, index=False, header=True):
                        ws_brands.append(r)
                
                for param_name, heats in param_heats.items():
                    if heats:
                        param_df = pd.DataFrame(heats).groupby('参数值', as_index=False)['搜索量'].sum().sort_values(by='搜索量', ascending=False)
                        clean_sheet_name = param_name[:31].translate(str.maketrans('', '', '\/?*[]'))
                        ws_param = workbook.create_sheet(f"{clean_sheet_name}拆解")
                        for r in dataframe_to_rows(param_df, index=False, header=True):
                            ws_param.append(r)
                
                df_selected = df[['词性', '搜索量']].groupby('词性').sum().reset_index()
                if not df_selected.empty:
                    ws_traffic = workbook.create_sheet('品类流量结构')
                    for r in dataframe_to_rows(df_selected, index=False, header=True):
                        ws_traffic.append(r)
                
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                output_filename = f"viz_result_{timestamp}.xlsx"
                output_path = os.path.join("/tmp", output_filename)
                workbook.save(output_path)
                
                buffer = io.BytesIO()
                workbook.save(buffer)
                buffer.seek(0)
                
                st.subheader("数据可视化")
                
                # 品牌词拆解饼图
                if not brand_words_df.empty:
                    chart_id = f"brand_pie_{timestamp}"
                    chart_data = {
                        "labels": brand_words_df['品牌名称'].tolist(),
                        "datasets": [{
                            "data": brand_words_df['搜索量'].tolist(),
                            "backgroundColor": [
                                "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
                                "#FF9F40", "#FF5733", "#C70039", "#900C3F", "#581845"
                            ]
                        }]
                    }
                    chart_html = f"""
                    <canvas id="{chart_id}" width="400" height="400"></canvas>
                    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels"></script>
                    <script>
                        var ctx = document.getElementById('{chart_id}').getContext('2d');
                        new Chart(ctx, {{
                            type: 'pie',
                            data: {json.dumps(chart_data)},
                            options: {{
                                plugins: {{
                                    title: {{ display: true, text: '品牌词拆解' }},
                                    legend: {{ display: true, position: 'top' }},
                                    tooltip: {{
                                        callbacks: {{
                                            label: function(context) {{
                                                let label = context.label || '';
                                                let value = context.raw || 0;
                                                let sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                                let percentage = ((value / sum) * 100).toFixed(2) + '%';
                                                return `${{label}}: ${{value}} (${{percentage}})`;
                                            }}
                                        }}
                                    }},
                                    datalabels: {{
                                        formatter: (value, context) => {{
                                            let sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                            let percentage = ((value / sum) * 100).toFixed(2) + '%';
                                            return percentage;
                                        }},
                                        color: '#fff',
                                        font: {{ weight: 'bold' }}
                                    }}
                                }}
                            }}
                        }});
                    </script>
                    """
                    st.markdown(chart_html, unsafe_allow_html=True)
                
                # 参数拆解饼图
                for param_name, heats in param_heats.items():
                    if heats:
                        param_df = pd.DataFrame(heats).groupby('参数值', as_index=False)['搜索量'].sum().sort_values(by='搜索量', ascending=False)
                        chart_id = f"param_pie_{param_name}_{timestamp}"
                        chart_data = {
                            "labels": param_df['参数值'].tolist(),
                            "datasets": [{
                                "data": param_df['搜索量'].tolist(),
                                "backgroundColor": [
                                    "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
                                    "#FF9F40", "#FF5733", "#C70039", "#900C3F", "#581845"
                                ]
                            }]
                        }
                        chart_html = f"""
                        <canvas id="{chart_id}" width="400" height="400"></canvas>
                        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels"></script>
                        <script>
                            var ctx = document.getElementById('{chart_id}').getContext('2d');
                            new Chart(ctx, {{
                                type: 'pie',
                                data: {json.dumps(chart_data)},
                                options: {{
                                    plugins: {{
                                        title: {{ display: true, text: '{param_name} 参数搜索量分布' }},
                                        legend: {{ display: true, position: 'top' }},
                                        tooltip: {{
                                            callbacks: {{
                                                label: function(context) {{
                                                    let label = context.label || '';
                                                    let value = context.raw || 0;
                                                    let sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                                    let percentage = ((value / sum) * 100).toFixed(2) + '%';
                                                    return `${{label}}: ${{value}} (${{percentage}})`;
                                                }}
                                            }}
                                        }},
                                        datalabels: {{
                                            formatter: (value, context) => {{
                                                let sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                                let percentage = ((value / sum) * 100).toFixed(2) + '%';
                                                return percentage;
                                            }},
                                            color: '#fff',
                                            font: {{ weight: 'bold' }}
                                        }}
                                    }}
                                }}
                            }});
                        </script>
                        """
                        st.markdown(chart_html, unsafe_allow_html=True)
                
                # 品类流量结构饼图
                if not df_selected.empty:
                    chart_id = f"traffic_pie_{timestamp}"
                    chart_data = {
                        "labels": df_selected['词性'].tolist(),
                        "datasets": [{
                            "data": df_selected['搜索量'].tolist(),
                            "backgroundColor": [
                                "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
                                "#FF9F40", "#FF5733", "#C70039", "#900C3F", "#581845"
                            ]
                        }]
                    }
                    chart_html = f"""
                    <canvas id="{chart_id}" width="400" height="400"></canvas>
                    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels"></script>
                    <script>
                        var ctx = document.getElementById('{chart_id}').getContext('2d');
                        new Chart(ctx, {{
                            type: 'pie',
                            data: {json.dumps(chart_data)},
                            options: {{
                                plugins: {{
                                    title: {{ display: true, text: '流量结构' }},
                                    legend: {{ display: true, position: 'top' }},
                                    tooltip: {{
                                        callbacks: {{
                                            label: function(context) {{
                                                let label = context.label || '';
                                                let value = context.raw || 0;
                                                let sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                                let percentage = ((value / sum) * 100).toFixed(2) + '%';
                                                return `${{label}}: ${{value}} (${{percentage}})`;
                                            }}
                                        }}
                                    }},
                                    datalabels: {{
                                        formatter: (value, context) => {{
                                            let sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                            let percentage = ((value / sum) * 100).toFixed(2) + '%';
                                            return percentage;
                                        }},
                                        color: '#fff',
                                        font: {{ weight: 'bold' }}
                                    }}
                                }}
                            }}
                        }});
                    </script>
                    """
                    st.markdown(chart_html, unsafe_allow_html=True)
                
                st.download_button(
                    label="下载处理结果",
                    data=buffer,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="viz_download_result"
                )
                st.success(f"数据处理和可视化完成，可通过下载按钮获取文件")
                if st.checkbox("保存到 /tmp 目录", key="viz_save_result"):
                    workbook.save(output_path)
                    st.success(f"文件已保存到 {output_path}")
            
            except Exception as e:
                st.error(f"处理数据时发生错误：{e}")

# 主应用程序
def main():
    st.set_page_config(page_title="市场洞察小程序", layout="wide")
    st.title("市场洞察小程序")
    
    st.header("功能选择")
    st.write("点击以下任一功能以展开操作界面：")
    
    merge_data_app()
    search_insight_app()
    search_insight_viz_app()

if __name__ == "__main__":
    main()
