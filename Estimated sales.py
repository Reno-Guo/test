import streamlit as st
import pandas as pd
import numpy as np

# 标题
st.title("表格处理工具")

# 上传第一个xlsx文件
file1 = st.file_uploader("上传第一个xlsx文件（表头在第二行，取关键词和搜索量排名列）", type=["xlsx"])

# 上传第二个xlsx文件
file2 = st.file_uploader("上传第二个xlsx文件（表头在第二行，取关键词、翻译、搜索量、点击转化率、建议竞价-推荐、建议竞价-最高、ABATop3集中度-点击）", type=["xlsx"])

if file1 and file2:
    # 读取第一个文件，跳过第一行（表头在第二行）
    df1 = pd.read_excel(file1, skiprows=1)
    # 假设列名为'关键词'和'搜索量排名'，如果不同，请调整
    df1 = df1[['关键词', '搜索量排名']]

    # 读取第二个文件，跳过第一行
    df2 = pd.read_excel(file2, skiprows=1)
    # 假设列名为指定名称，如果不同，请调整
    columns_to_keep = ['关键词', '翻译', '搜索量', '点击转化率', '建议竞价-推荐', '建议竞价-最高', 'ABATop3集中度-点击']
    df2 = df2[columns_to_keep]

    # 基于'关键词'合并搜索量排名
    result_df = pd.merge(df2, df1, on='关键词', how='left')

    # 重新排列列顺序
    result_columns = ['关键词', '翻译', '搜索量', '点击转化率', '建议竞价-推荐', '建议竞价-最高', 'ABATop3集中度-点击', '搜索量排名']
    result_df = result_df[result_columns]

    # 添加新列
    result_df['日搜索量'] = result_df['搜索量'] / 7

    # 计算搜索量份额占比
    def calculate_share(row):
        rank = row['搜索量排名']
        bid_recommend = row['建议竞价-推荐']
        concentration = row['ABATop3集中度-点击']

        if rank <= 5000 or bid_recommend > 5:
            return 0.02  # 2%
        elif 5000 < rank <= 10000:
            return 0.035  # 3.5%
        else:
            if concentration < 0.4:
                return 0.05  # 5%
            elif 0.4 <= concentration < 0.5:
                return 0.03  # 3%
            elif 0.5 <= concentration < 0.6:
                return 0.02  # 2%
            else:
                return 0.01  # 1%

    result_df['搜索量份额占比'] = result_df.apply(calculate_share, axis=1)

    # 预估修正CVR 留白（初始设为0，用户可编辑）
    result_df['预估修正CVR'] = 0.0

    # 预估单量
    result_df['预估单量'] = result_df['日搜索量'] * result_df['搜索量份额占比'] * (result_df['点击转化率'] + result_df['预估修正CVR'])

    # 显示结果表，并允许编辑预估修正CVR
    st.subheader("结果表")
    edited_df = st.data_editor(result_df, num_rows="dynamic", use_container_width=True)

    # 如果编辑了预估修正CVR，重新计算预估单量
    if not edited_df.equals(result_df):
        edited_df['预估单量'] = edited_df['日搜索量'] * edited_df['搜索量份额占比'] * (edited_df['点击转化率'] + edited_df['预估修正CVR'])
        st.data_editor(edited_df, num_rows="dynamic", use_container_width=True)  # 重新显示更新后的表

    # 自定义样式使表头绿色
    def style_header(df):
        styler = df.style.set_table_styles([{'selector': 'th', 'props': [('background-color', 'lightgreen')]}])
        return styler

    st.dataframe(style_header(result_df))
else:
    st.info("请上传两个xlsx文件以继续。")
