# search_insight_viz.py
import streamlit as st
import pandas as pd
import re
import plotly.express as px
import os  # Added this import
from utils import render_app_header, unique_tmp_path, _read_excel_cached, save_workbook_to_buffer, render_download_section, get_timestamp, Workbook, dataframe_to_rows

def aggregate_top_n(df, value_col, name_col, top_n=10):
    df = df.copy()
    df[name_col] = df[name_col].astype(str)
    df = df.sort_values(by=value_col, ascending=False).reset_index(drop=True)
    if len(df) > top_n:
        top_df = df.iloc[:top_n]
        others = df.iloc[top_n:][value_col].sum()
        others_row = pd.DataFrame([{name_col: "Others", value_col: others}])
        df = pd.concat([top_df[[name_col, value_col]], others_row], ignore_index=True)
    return df[[name_col, value_col]]

def pie_chart(df, value_col, name_col, title):
    df = df.copy()
    df[name_col] = df[name_col].astype(str)
    df = df.sort_values(by=value_col, ascending=False).reset_index(drop=True)
    if "Others" in df[name_col].values:
        order = [n for n in df[name_col] if n != "Others"] + ["Others"]
        df[name_col] = pd.Categorical(df[name_col], categories=order, ordered=True)
    palette = [
        "#4C8EDA", "#FFA14E", "#F25C5C", "#6BD0C1", "#58C27D", "#F7C948",
        "#B685D6", "#FF90B3", "#BC8D6E", "#C9C9C9", "#81D3EB",
    ]
    fig = px.pie(
        df,
        values=value_col,
        names=name_col,
        title=title,
        color_discrete_sequence=palette,
    )
    fig.update_traces(textinfo="label+percent", sort=False)
    fig.update_layout(
        height=900,
        legend=dict(orientation="v", x=0.8, y=0.5, font=dict(size=16)),
        margin=dict(l=20, r=150, t=50, b=50),
        font=dict(size=16),
    )
    st.plotly_chart(fig, use_container_width=True)

def search_insight_viz_app():
    render_app_header("📈 SI - 搜索流量洞察: 聚合和可视化", "生成多维度数据分析报表和可视化图表")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "选择包含源数据的 Excel 文件(完成检查确认无误)",
            type=["xlsx", "xls"],
            key="viz_data_file",
        )
    with col2:
        save_filename = st.text_input("输出文件名", "viz_result.xlsx", key="viz_save_folder")
    st.divider()
    execute_btn = st.button("🚀 开始可视化", key="viz_execute_button", use_container_width=True)
    if execute_btn:
        if not uploaded_file or not save_filename:
            st.warning("⚠️ 请确保已上传数据文件并输入输出文件名")
            return
        with st.spinner("🔄 正在生成可视化报表，请稍候..."):
            save_path = unique_tmp_path(save_filename)
            df = _read_excel_cached(uploaded_file, sheet_name="源数据")
            if df.empty:
                st.warning("📂 上传的文件为空或不包含'源数据'工作表，请检查数据文件")
                return
            # Brand aggregation
            brand_words = []
            b_status = st.empty()
            b_prog = st.progress(0)
            b_status.text("正在处理品牌词...")
            step = max(1, len(df) // 10)
            for idx, row in df.iterrows():
                vol = row["搜索量"] if pd.notna(row["搜索量"]) else 0
                brands = [b.strip() for b in str(row["品牌"]).split(",") if b.strip()]
                for b in brands:
                    brand_words.append({"品牌名称": b, "搜索量": vol})
                if (idx + 1) % step == 0 or idx == len(df) - 1:
                    b_prog.progress((idx + 1) / len(df))
            brand_df = pd.DataFrame()
            if brand_words:
                brand_df = pd.DataFrame(brand_words).groupby("品牌名称", as_index=False)["搜索量"].sum()
                brand_df = aggregate_top_n(brand_df, "搜索量", "品牌名称")
            b_status.text("品牌词处理完成")
            b_prog.empty()
            b_status.empty()
            # Param aggregation (single pass)
            excluded = {"搜索词", "搜索量", "品牌名称", "品牌", "特性参数", "词性"}
            param_cols = [c for c in df.columns if c not in excluded]
            param_heats: dict[str, list[dict]] = {c: [] for c in param_cols}
            p_status = st.empty()
            p_prog = st.progress(0)
            p_status.text("正在处理参数...")
            for idx, row in df.iterrows():
                vol = row["搜索量"] if pd.notna(row["搜索量"]) else 0
                for c in param_cols:
                    val = str(row[c]) if pd.notna(row[c]) else ""
                    for v in [v.strip() for v in val.split(",") if v.strip()]:
                        param_heats[c].append({"参数值": v, "搜索量": vol})
                if (idx + 1) % step == 0 or idx == len(df) - 1:
                    p_prog.progress((idx + 1) / len(df))
            p_status.text("参数处理完成")
            p_prog.empty()
            p_status.empty()
            # Traffic structure
            traffic_df = df[["词性", "搜索量"]].groupby("词性", as_index=False)["搜索量"].sum()
            traffic_df = aggregate_top_n(traffic_df, "搜索量", "词性")
            # Workbook
            s_status = st.empty()
            s_prog = st.progress(0)
            s_status.text("正在生成Excel工作簿...")
            s_prog.progress(0.3)
            wb = Workbook()
            if "Sheet" in wb.sheetnames:
                wb.remove(wb["Sheet"])
            ws = wb.create_sheet("源数据")
            for r in dataframe_to_rows(df, index=False, header=True):
                ws.append(r)
            s_prog.progress(0.6)
            if not brand_df.empty:
                ws = wb.create_sheet("品牌词拆解")
                for r in dataframe_to_rows(brand_df, index=False, header=True):
                    ws.append(r)
            s_prog.progress(0.7)
            param_dfs: dict[str, pd.DataFrame] = {}
            active_params = [c for c in param_cols if param_heats[c]]
            for i, c in enumerate(active_params):
                heats = param_heats[c]
                if heats:
                    pdf = pd.DataFrame(heats).groupby("参数值", as_index=False)["搜索量"].sum()
                    pdf = aggregate_top_n(pdf, "搜索量", "参数值")
                    param_dfs[c] = pdf
                    clean = re.sub(r"[\/*?[\]]", "", c)[:31]
                    ws = wb.create_sheet(f"{clean}拆解")
                    for r in dataframe_to_rows(pdf, index=False, header=True):
                        ws.append(r)
                s_prog.progress(0.7 + 0.3 * (i + 1) / max(1, len(active_params)))
            if not traffic_df.empty:
                ws = wb.create_sheet("品类流量结构")
                for r in dataframe_to_rows(traffic_df, index=False, header=True):
                    ws.append(r)
            s_prog.progress(1.0)
            s_status.text("工作簿生成完成")
            s_status.empty()
            s_prog.empty()
            buffer = save_workbook_to_buffer(wb)
            st.success("✅ 数据处理完成，正在生成可视化图表...")
            st.markdown("### 📊 数据可视化")
            if not brand_df.empty:
                pie_chart(brand_df, "搜索量", "品牌名称", "品牌词拆解")
            for c in param_cols:
                if c in param_dfs:
                    pie_chart(param_dfs[c], "搜索量", "参数值", f"{c} 参数搜索量分布")
            if not traffic_df.empty:
                pie_chart(traffic_df, "搜索量", "词性", "流量结构")
            st.divider()
            ts = get_timestamp()
            out_name = f"viz_result_{ts}.xlsx"
            out_path = os.path.join("/tmp", out_name)
            save_func = lambda: wb.save(out_path)
            render_download_section(
                buffer,
                out_name,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "📥 下载完整报表",
                "viz",
                has_save=True,
                save_func=save_func,
                save_path=out_path,
            )
