import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

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

        if pd.isna(rank) or pd.isna(bid_recommend) or pd.isna(concentration):
            return np.nan

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

    # 预估修正CVR 留白（NaN）
    result_df['预估修正CVR'] = np.nan

    # 预估单量 初始不填值
    result_df['预估单量'] = np.nan

    # 更新列顺序
    final_columns = ['关键词', '翻译', '搜索量', '点击转化率', '建议竞价-推荐', '建议竞价-最高', 'ABATop3集中度-点击', '搜索量排名', '日搜索量', '搜索量份额占比', '预估修正CVR', '预估单量']
    result_df = result_df[final_columns]

    # 显示结果表，并允许编辑（主要是预估修正CVR）
    st.subheader("结果表（请编辑预估修正CVR列）")
    edited_df = st.data_editor(
        result_df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "预估修正CVR": st.column_config.NumberColumn(
                "预估修正CVR",
                help="请输入预估修正CVR值",
                format="%.4f"
            )
        }
    )

    # 下载按钮
    def generate_excel(df):
        wb = Workbook()
        ws = wb.active
        ws.title = "结果表"

        # 写入数据（不包括预估单量数值）
        for r in dataframe_to_rows(df.drop(columns=['预估单量']), index=False, header=True):
            ws.append(r)

        # 设置表头样式：绿色
        green_fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
        for cell in ws[1]:
            cell.fill = green_fill

        # 设置预估单量列公式（L列，从行2开始）
        for row in range(2, len(df) + 2):
            # 列位置：I=日搜索量 (9), J=搜索量份额占比 (10), D=点击转化率 (4), K=预估修正CVR (11)
            formula = f'=I{row}*J{row}*(D{row}+K{row})'
            ws.cell(row=row, column=12).value = formula  # L列是12

        # 调整列宽
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        # 保存到BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    if st.button("下载结果xlsx文件"):
        excel_file = generate_excel(edited_df)
        st.download_button(
            label="点击下载结果.xlsx",
            data=excel_file,
            file_name="结果.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # 显示样式化的预览（不包括公式列数值）
    st.subheader("预览（预估单量将在Excel中自动计算）")
    preview_df = edited_df.copy()
    preview_df['预估单量'] = preview_df['日搜索量'] * preview_df['搜索量份额占比'] * (preview_df['点击转化率'] + preview_df['预估修正CVR'].fillna(0))
    st.dataframe(preview_df)

else:
    st.info("请上传两个xlsx文件以继续。")
