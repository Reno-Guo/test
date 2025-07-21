import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
import io
import plotly.express as px
from openpyxl import Workbook
from openpyxl.chart import PieChart, Reference
from openpyxl.chart.label import DataLabelList

# 合并数据表格功能
def merge_data_app():
    st.header("合并数据表格")
    
    uploaded_files = st.file_uploader("选择需要合并的 Excel 或 CSV 文件", type=["xlsx", "xls", "csv"], accept_multiple_files=True, key="merge_files")
    save_filename = st.text_input("请输入合并后的文件名（例如：output.xlsx）", key="merge_save")
    
    if st.button("合并文件", key="merge_button"):
        if not uploaded_files or not save_filename:
            st.warning("请确保已选择文件并输入文件名")
            return
        
        save_path = os.path.join("/tmp", save_filename) if not save_filename.startswith("/tmp") else save_filename
        
        try:
            df_list = []
            for file in uploaded_files:
                try:
                    if file.name.endswith('.xlsx'):
                        df = pd.read_excel(file, engine='openpyxl')
                    elif file.name.endswith('.xls'):
                        df = pd.read_excel(file, engine='xlrd')
                    elif file.name.endswith('.csv'):
                        df = pd.read_csv(file)
                    df['时间'] = os.path.splitext(file.name)[0]
                    df = process_price_columns(df)
                    df_list.append(df)
                except Exception as e:
                    st.error(f"读取文件 {file.name} 失败：{e}")
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
            st.error(f"合并文件时发生错误：{e}")

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

# 搜索流量洞察功能
def search_insight_app():
    st.header("搜索流量洞察")
    
    # 模板下载
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
    
    # 数据文件上传
    uploaded_file = st.file_uploader("选择数据文件", type=["xlsx", "xls"], key="data_file")
    save_filename = st.text_input("请输入输出文件名（例如：result.xlsx）", key="save_folder")
    
    # 输入产品参数（可选）
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
            # 处理产品参数（仅在提供参数时处理）
            product_parameters = []
            if param_names and param_values:
                param_names_list = [name.strip() for name in param_names.split(',')]
                param_values_list = [v.strip().split(',') for v in param_values.split('\n')]
                product_parameters = list(zip(param_names_list, param_values_list))
            
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
            
            brand_words_df = pd.DataFrame(brand_words_list)
            brand_words_df = brand_words_df.groupby('品牌名称', as_index=False)['搜索量'].sum().sort_values(by='搜索量', ascending=False)
            df['词性'] = results
            
            param_heats = {param_name: [] for param_name, _ in product_parameters}
            for index, row in df.iterrows():
                search_word = str(row['搜索词']).lower()
                search_volumn = row['搜索量']
                for param_name, param_values in product_parameters:
                    for param in param_values:
                        if str(param).lower() in search_word:
                            param_heats[param_name].append({'参数值': param, '搜索量': search_volumn})
            
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            output_filename = f"result_{timestamp}.xlsx"
            output_path = os.path.join("/tmp", output_filename)
            
            # Save to Excel with charts
            workbook = Workbook()
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                writer.book = workbook
                df.to_excel(writer, sheet_name='源数据', index=False)
                brand_words_df.to_excel(writer, sheet_name='品牌词拆解', index=False)
                
                for param_name, heats in param_heats.items():
                    if heats:
                        param_df = pd.DataFrame(heats).groupby('参数值', as_index=False)['搜索量'].sum().sort_values(by='搜索量', ascending=False)
                        clean_sheet_name = param_name[:31].translate(str.maketrans('', '', '\/?*[]'))
                        param_df.to_excel(writer, sheet_name=f"{clean_sheet_name}拆解", index=False)
                
                df_selected = df[['词性', '搜索量']].groupby('词性').sum().reset_index()
                df_selected.to_excel(writer, sheet_name='品类流量结构', index=False)
                
                # Add Excel charts
                if not brand_words_df.empty:
                    brand_words_sheet = workbook['品牌词拆解']
                    chart = PieChart()
                    chart.title = "品牌词拆解"
                    max_row = brand_words_df.shape[0] + 1
                    data = Reference(brand_words_sheet, min_col=2, min_row=1, max_col=2, max_row=max_row)
                    labels = Reference(brand_words_sheet, min_col=1, min_row=2, max_row=max_row)
                    chart.add_data(data, titles_from_data=True)
                    chart.set_categories(labels)
                    chart.dataLabels = DataLabelList()
                    chart.dataLabels.showCatName = True
                    chart.dataLabels.showPercent = True
                    chart.width = 12
                    chart.height = 10
                    brand_words_sheet.add_chart(chart, "G3")
                
                for param_name, heats in param_heats.items():
                    if heats:
                        param_df = pd.DataFrame(heats).groupby('参数值', as_index=False)['搜索量'].sum().sort_values(by='搜索量', ascending=False)
                        clean_sheet_name = param_name[:31].translate(str.maketrans('', '', '\/?*[]')) + "拆解"
                        param_sheet = workbook[clean_sheet_name]
                        chart = PieChart()
                        chart.title = f"{param_name} 参数搜索量分布"
                        max_row_param = len(param_df) + 1
                        data = Reference(param_sheet, min_col=2, min_row=1, max_col=2, max_row=max_row_param)
                        labels = Reference(param_sheet, min_col=1, min_row=2, max_row=max_row_param)
                        chart.add_data(data, titles_from_data=True)
                        chart.set_categories(labels)
                        chart.dataLabels = DataLabelList()
                        chart.dataLabels.showCatName = True
                        chart.dataLabels.showPercent = True
                        chart.width = 12
                        chart.height = 10
                        param_sheet.add_chart(chart, "G3")
                
                if not df_selected.empty:
                    ws = workbook['品类流量结构']
                    chart = PieChart()
                    labels = Reference(ws, min_col=1, min_row=2, max_row=len(df_selected) + 2)
                    data = Reference(ws, min_col=2, min_row=1, max_row=len(df_selected) + 1)
                    chart.add_data(data, titles_from_data=True)
                    chart.set_categories(labels)
                    chart.title = "流量结构"
                    chart.dataLabels = DataLabelList()
                    chart.dataLabels.showPercent = True
                    chart.width = 12
                    chart.height = 10
                    ws.add_chart(chart, "G2")
            
            # Display Plotly charts
            st.subheader("数据可视化")
            if not brand_words_df.empty:
                fig = px.pie(brand_words_df, values='搜索量', names='品牌名称', title="品牌词拆解")
                fig.update_traces(textinfo='label+percent')
                st.plotly_chart(fig, use_container_width=True)
            
            for param_name, heats in param_heats.items():
                if heats:
                    param_df = pd.DataFrame(heats).groupby('参数值', as_index=False)['搜索量'].sum().sort_values(by='搜索量', ascending=False)
                    fig = px.pie(param_df, values='搜索量', names='参数值', title=f"{param_name} 参数搜索量分布")
                    fig.update_traces(textinfo='label+percent')
                    st.plotly_chart(fig, use_container_width=True)
            
            if not df_selected.empty:
                fig = px.pie(df_selected, values='搜索量', names='词性', title="流量结构")
                fig.update_traces(textinfo='label+percent')
                st.plotly_chart(fig, use_container_width=True)
            
            # Provide download link
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

# 主应用程序
def main():
    st.set_page_config(page_title="市场洞察小程序", layout="wide")
    st.title("市场洞察小程序")
    
    st.sidebar.header("选择功能")
    option = st.sidebar.selectbox("功能", ["合并数据表格", "搜索流量洞察"], key="sidebar_option")
    
    if option == "合并数据表格":
        merge_data_app()
    elif option == "搜索流量洞察":
        search_insight_app()

if __name__ == "__main__":
    main()
