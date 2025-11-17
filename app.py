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
from typing import Callable, List, Any, Dict

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

# === Shared UI/render helpers ===
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

def save_df_to_buffer(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    return buffer

def save_workbook_to_buffer(wb: Workbook) -> io.BytesIO:
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

def render_download_section(
    buffer: io.BytesIO,
    file_name: str,
    mime_type: str,
    download_label: str,
    key_prefix: str,
    has_save: bool = False,
    save_func: Callable[[], None] | None = None,
    save_path: str | None = None,
):
    if has_save:
        col_d, col_s = st.columns(2)
        with col_d:
            st.download_button(
                label=download_label,
                data=buffer,
                file_name=file_name,
                mime=mime_type,
                key=f"{key_prefix}_download",
                use_container_width=True,
            )
        with col_s:
            if st.checkbox("💾 同时保存到 /tmp 目录", key=f"{key_prefix}_save"):
                if save_func:
                    save_func()
                st.info(f"📁 文件已保存到 {save_path}")
    else:
        st.download_button(
            label=download_label,
            data=buffer,
            file_name=file_name,
            mime=mime_type,
            key=f"{key_prefix}_download",
            use_container_width=True,
        )

# === Shared ZIP processors ===
def read_file_merge(file_path: str) -> pd.DataFrame | None:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    engine = "openpyxl" if ext == ".xlsx" else "xlrd" if ext == ".xls" else None
    if engine:
        return _read_excel_cached(file_path, engine=engine)
    return None

def read_file_clean(file_path: str) -> pd.DataFrame | None:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path, header=None)
    engine = "openpyxl" if ext == ".xlsx" else "xlrd" if ext == ".xls" else None
    if engine:
        return pd.read_excel(file_path, header=None, engine=engine)
    return None

def write_processed_file(df: pd.DataFrame, path: str, ext: str):
    if ext == ".csv":
        df.to_csv(path, index=False)
    else:
        df.to_excel(path, index=False, engine="openpyxl")

def process_zip_files(
    uploaded_file,
    read_cb: Callable[[str], pd.DataFrame | None],
    process_cb: Callable[[pd.DataFrame, str, str], Any],
) -> List[Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(temp_dir)
        files = [f for f in os.listdir(temp_dir) if f.lower().endswith((".xlsx", ".xls", ".csv"))]
        if not files:
            st.warning("📂 压缩文件中未找到任何 Excel 或 CSV 文件")
            return []
        results = []
        pb = st.progress(0)
        status = st.empty()
        for i, f in enumerate(files):
            status.text(f"正在处理: {f} ({i+1}/{len(files)})")
            fp = os.path.join(temp_dir, f)
            try:
                df = read_cb(fp)
                if df is None:
                    raise ValueError("不支持的文件格式")
                results.append(process_cb(df, f, temp_dir))
            except Exception as e:
                st.error(f"❌ 处理文件 {f} 失败: {e}")
            pb.progress((i + 1) / len(files))
        status.empty()
        pb.empty()
        return results

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
    render_app_header("📊 MI/SI - 合并数据表格", "将多个Excel文件合并为一个统一的数据表格")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "选择一个 .zip 文件(包含需要合并的 Excel 文件)",
            type=["zip"],
            accept_multiple_files=False,
            key="merge_files",
            help="支持包含.xlsx、.xls、.csv格式的ZIP压缩包",
        )
    with col2:
        save_filename = st.text_input(
            "输出文件名",
            value="merged_output.xlsx",
            key="merge_save",
            help="请输入合并后的文件名",
        )
    st.divider()
    execute_btn = st.button("🚀 开始合并", key="merge_button", use_container_width=True)
    if execute_btn:
        if not uploaded_file or not save_filename:
            st.warning("⚠️ 请确保已选择 .zip 文件并输入文件名")
            return
        with st.spinner("🔄 正在处理文件，请稍候..."):
            save_path = unique_tmp_path(save_filename)
            def cb_merge(df, fname, _):
                df["时间"] = os.path.splitext(fname)[0]
                return process_price_columns(df)
            df_list = process_zip_files(uploaded_file, read_file_merge, cb_merge)
            if not df_list:
                return
            status = st.empty()
            prog = st.progress(0)
            status.text("正在合并数据...")
            merged_df = pd.concat(df_list, ignore_index=True)
            merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
            prog.progress(1.0)
            status.text("合并完成")
            status.empty()
            prog.empty()
            buffer = save_df_to_buffer(merged_df)
            st.success(f"✅ 成功合并 {len(df_list)} 个文件，共 {len(merged_df)} 行数据")
            save_func = lambda: merged_df.to_excel(save_path, index=False, engine="openpyxl")
            render_download_section(
                buffer,
                os.path.basename(save_filename),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "📥 下载合并后的文件",
                "merged",
                has_save=True,
                save_func=save_func,
                save_path=save_path,
            )

# 搜索流量洞察（源数据）
def analyze_search_rows(df: pd.DataFrame, params: List[tuple]):
    punct = str.maketrans("", "", '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
    brands = df["品牌名称"].dropna().unique()
    for p, _ in params:
        df[p] = ""
    df["品牌"] = ""
    df["特性参数"] = ""
    results = []
    brand_words = []
    pb = st.progress(0)
    status = st.empty()
    for idx, row in df.iterrows():
        status.text(f"正在分析第 {idx+1}/{len(df)} 条数据...")
        sword = str(row["搜索词"]).lower()
        vol = row["搜索量"] if pd.notna(row["搜索量"]) else 0
        m_brands = []
        for b in brands:
            b_low = str(b).lower()
            if len(b_low) <= 5:
                if re.search(rf"\b{re.escape(b_low)}\b", sword):
                    m_brands.append(b_low)
            else:
                norms = [
                    b_low,
                    b_low.translate(punct),
                    b_low.replace(" ", ""),
                    b_low.translate(punct).replace(" ", ""),
                ]
                if any(n in sword for n in norms):
                    m_brands.append(b_low)
        df.at[idx, "品牌"] = ",".join(set(m_brands))
        m_params = []
        for p_name, p_vals in params:
            m_vals = [str(v).lower() for v in p_vals if str(v).lower() in sword]
            df.at[idx, p_name] = ",".join(set(m_vals))
            m_params.extend(m_vals)
        df.at[idx, "特性参数"] = ",".join(set(m_params))
        if m_brands:
            results.append("Branded KWs")
            for b in set(m_brands):
                brand_words.append({"品牌名称": b, "搜索量": vol})
        else:
            results.append("Non-Branded KWs")
        pb.progress((idx + 1) / len(df))
    status.empty()
    pb.empty()
    df["词性"] = results
    return df, results

def search_insight_app():
    render_app_header("🔍 SI - 搜索流量洞察", "分析搜索关键词，识别品牌词与非品牌词")
    st.markdown("#### 📋 步骤 1: 下载数据模板")
    tmpl = pd.DataFrame(columns=["搜索词", "搜索量", "品牌名称"])
    buf = io.BytesIO()
    tmpl.to_excel(buf, index=False)
    buf.seek(0)
    st.download_button(
        "📥 下载Excel模板",
        buf,
        "template.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_template",
        use_container_width=True,
    )
    st.divider()
    st.markdown("#### 📤 步骤 2: 上传填写好的数据文件")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("选择数据文件", type=["xlsx", "xls"], key="data_file")
    with col2:
        save_filename = st.text_input("输出文件名", "search_insight_result.xlsx", key="save_folder")
    st.divider()
    st.markdown("#### ⚙️ 步骤 3: 输入产品参数(可选)")
    col1, col2 = st.columns(2)
    with col1:
        param_names = st.text_input("参数名(用逗号分隔)", placeholder="例如: 颜色,尺寸,材质", key="param_names")
    with col2:
        param_values = st.text_area(
            "具体参数(每行一个参数组,用逗号分隔)",
            placeholder="例如:\n红,蓝,绿\n小,中,大",
            key="param_values",
            height=100,
        )
    st.divider()
    execute_btn = st.button("🚀 开始分析", key="execute_button", use_container_width=True)
    if execute_btn:
        if not uploaded_file or not save_filename:
            st.warning("⚠️ 请确保已上传数据文件并输入输出文件名")
            return
        with st.spinner("🔄 正在分析数据，请稍候..."):
            save_path = unique_tmp_path(save_filename)
            df = _read_excel_cached(uploaded_file)
            if df.empty:
                st.warning("📂 上传的文件为空，请检查数据文件")
                return
            p_params = []
            if param_names and param_values:
                names = [n.strip() for n in re.split(r"[,\uff0c]", param_names) if n.strip()]
                vals = []
                for line in param_values.split("\n"):
                    vs = [v.strip() for v in re.split(r"[,\uff0c]", line) if v.strip()]
                    if vs:
                        vals.append(vs)
                p_params = list(zip(names, vals)) if len(names) == len(vals) else []
            df, kw_types = analyze_search_rows(df, p_params)
            branded = kw_types.count("Branded KWs")
            non_branded = len(kw_types) - branded
            status = st.empty()
            prog = st.progress(0)
            status.text("正在保存到Excel...")
            prog.progress(0.5)
            wb = Workbook()
            if "Sheet" in wb.sheetnames:
                wb.remove(wb["Sheet"])
            ws = wb.create_sheet("源数据")
            for r in dataframe_to_rows(df, index=False, header=True):
                ws.append(r)
            prog.progress(1.0)
            status.text("保存完成")
            status.empty()
            prog.empty()
            buffer = save_workbook_to_buffer(wb)
            ts = get_timestamp()
            out_name = f"result_{ts}.xlsx"
            out_path = os.path.join("/tmp", out_name)
            st.success(f"✅ 分析完成! 品牌词: {branded} 条 | 非品牌词: {non_branded} 条")
            save_func = lambda: wb.save(out_path)
            render_download_section(
                buffer,
                out_name,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "📥 下载处理结果",
                "result",
                has_save=True,
                save_func=save_func,
                save_path=out_path,
            )

# 可视化共享
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
            param_heats: Dict[str, List[Dict]] = {c: [] for c in param_cols}
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
            param_dfs: Dict[str, pd.DataFrame] = {}
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

# 数据清理
def data_clean_app():
    render_app_header("🧹 DC - 数据清理: 删除第一行", "批量删除Excel/CSV文件的第一行数据并重新打包")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "选择一个 .zip 文件(包含 XLSX 或 CSV 文件)",
            type=["zip"],
            key="clean_files",
        )
    with col2:
        output_filename = st.text_input("输出文件名", "cleaned_files.zip", key="clean_save")
    st.divider()
    execute_btn = st.button("🚀 开始清理", key="clean_button", use_container_width=True)
    if execute_btn:
        if not uploaded_file or not output_filename:
            st.warning("⚠️ 请确保已选择 .zip 文件并输入输出文件名")
            return
        with st.spinner("🔄 正在清理文件，请稍候..."):
            def cb_clean(df, fname, tdir):
                df = df.iloc[1:].reset_index(drop=True)
                out_path = os.path.join(tdir, f"cleaned_{fname}")
                ext = os.path.splitext(fname)[1].lower()
                write_processed_file(df, out_path, ext)
                return out_path
            processed = process_zip_files(uploaded_file, read_file_clean, cb_clean)
            if not processed:
                return
            status = st.empty()
            prog = st.progress(0)
            status.text("正在打包ZIP文件...")
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as nz:
                for i, p in enumerate(processed):
                    arc = os.path.basename(p).replace("cleaned_", "")
                    nz.write(p, arc)
                    prog.progress((i + 1) / len(processed))
            buffer.seek(0)
            status.text("打包完成")
            status.empty()
            prog.empty()
            st.success(f"✅ 成功清理 {len(processed)} 个文件")
            render_download_section(
                buffer,
                output_filename,
                "application/zip",
                "📥 下载清理后的 ZIP 文件",
                "cleaned",
                has_save=False,
            )

# 主应用程序
def main():
    st.set_page_config(page_title=APP_CONFIG["app_title"], layout="wide", page_icon="📊", initial_sidebar_state="collapsed")
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] {font-family: 'Inter', 'Segoe UI', sans-serif;}
        .main {background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);}
        h1, h2, h3, h4, h5, h6 {color: #ffffff !important; font-weight: 600 !important;}
        .stButton > button {
            background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%);
            color: white; border: none; border-radius: 8px; padding: 0.6rem 1.5rem;
            font-weight: 600; font-size: 15px; transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 166, 228, 0.2);
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #0088c2 0%, #006a99 100%);
            box-shadow: 0 6px 12px rgba(0, 166, 228, 0.3); transform: translateY(-2px);
        }
        .stDownloadButton > button {background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%);
            color: white; border: none; border-radius: 8px; padding: 0.6rem 1.5rem;
            font-weight: 600; font-size: 15px; transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 166, 228, 0.2);
        }
        .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #0088c2 0%, #006a99 100%);
            box-shadow: 0 6px 12px rgba(0, 166, 228, 0.3); transform: translateY(-2px);
        }
        .stFileUploader {background: white; border-radius: 10px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08);}
        [data-testid="stFileUploadDropzone"] {border: 2px dashed #00a6e4; border-radius: 8px; background: #f8fcff;}
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            border: 2px solid #e0e0e0; border-radius: 8px; padding: 0.6rem; transition: all 0.3s ease; font-size: 14px;
        }
        .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
            border-color: #00a6e4; box-shadow: 0 0 0 3px rgba(0, 166, 228, 0.1);
        }
        .stProgress > div > div > div > div {background: linear-gradient(90deg, #00a6e4 0%, #0088c2 100%);}
        .stSuccess {background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); border-left: 4px solid #28a745; border-radius: 8px; padding: 1rem;}
        .stError {background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border-left: 4px solid #dc3545; border-radius: 8px; padding: 1rem;}
        .stWarning {background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); border-left: 4px solid #ffc107; border-radius: 8px; padding: 1rem;}
        .stInfo {background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); border-left: 4px solid #00a6e4; border-radius: 8px; padding: 1rem;}
        div[data-testid="column"] {background: white; padding: 1rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);}
        .js-plotly-plot {border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);}
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #00a6e4 0%, #0088c2 100%); padding: 2.5rem 2rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 8px 16px rgba(0,0,0,0.15);">
        <h1 style="color: white; margin: 0; font-size: 2.5rem; font-weight: 700;">📊 市场洞察小程序</h1>
        <div style="display: flex; gap: 2rem; margin-top: 1rem; flex-wrap: wrap;">
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;"><strong>版本:</strong> {APP_CONFIG["version"]}</span>
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;"><strong>作者:</strong> {APP_CONFIG["author"]}</span>
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;"><strong>公司:</strong> {APP_CONFIG["company"]}</span>
            <span style="color: rgba(255,255,255,0.95); font-size: 14px;"><strong>联系:</strong> {APP_CONFIG["contact"]}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h3 style="margin-top: 0; color: #333;">🎯 功能导航</h3>
        <p style="color: #666; margin-bottom: 0;">选择下方功能模块开始您的数据分析之旅</p>
    </div>
    """, unsafe_allow_html=True)
    tabs = st.tabs(["📊 合并数据表格", "🔍 搜索流量洞察", "📈 流量可视化分析", "🧹 数据清理工具"])
    with tabs[0]:
        merge_data_app()
    with tabs[1]:
        search_insight_app()
    with tabs[2]:
        search_insight_viz_app()
    with tabs[3]:
        data_clean_app()
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem 0;">
        <p style="margin: 0;">© Anker Oceanwing Inc. | 海翼IDC团队</p>
        <p style="margin: 0.5rem 0 0 0; font-size: 13px;">市场洞察小程序 v1.2.0 - 让数据分析更简单</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
