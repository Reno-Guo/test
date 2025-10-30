import streamlit as st
import pandas as pd
import io
import math

# Page configuration
st.set_page_config(
    page_title="Keepa数据整理与可视化",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with #00a6e4 as primary color
st.markdown("""
<style>
    /* 主色调变量 */
    :root {
        --primary-color: #00a6e4;
        --primary-dark: #0088ba;
        --primary-light: #33b8eb;
        --secondary-color: #f0f8ff;
        --text-dark: #1e3a5f;
        --border-radius: 12px;
    }
    
    /* 隐藏默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 整体背景 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8f4f8 100%);
    }
    
    /* 标题样式 */
    h1 {
        color: var(--primary-color) !important;
        font-weight: 700 !important;
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem !important;
        text-shadow: 2px 2px 4px rgba(0, 166, 228, 0.1);
    }
    
    h2 {
        color: var(--text-dark) !important;
        font-weight: 600 !important;
        margin-top: 2rem !important;
        padding-bottom: 0.5rem !important;
        border-bottom: 3px solid var(--primary-color) !important;
    }
    
    /* 信息卡片 */
    .info-card {
        background: white;
        padding: 1.5rem;
        border-radius: var(--border-radius);
        box-shadow: 0 4px 6px rgba(0, 166, 228, 0.1);
        margin-bottom: 1.5rem;
        border-left: 4px solid var(--primary-color);
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
        color: white;
        border: none;
        border-radius: var(--border-radius);
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 166, 228, 0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 166, 228, 0.3);
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-color) 100%);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* 文件上传器样式 */
    .stFileUploader {
        background: white;
        padding: 2rem;
        border-radius: var(--border-radius);
        border: 2px dashed var(--primary-light);
        transition: all 0.3s ease;
    }
    
    .stFileUploader:hover {
        border-color: var(--primary-color);
        background: var(--secondary-color);
    }
    
    /* 下载按钮 */
    .stDownloadButton > button {
        background: white;
        color: var(--primary-color);
        border: 2px solid var(--primary-color);
        border-radius: var(--border-radius);
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stDownloadButton > button:hover {
        background: var(--primary-color);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 166, 228, 0.3);
    }
    
    /* 信息提示框 */
    .stInfo {
        background: linear-gradient(135deg, #e3f5fc 0%, #b3e5fc 100%);
        border-left: 4px solid var(--primary-color);
        border-radius: var(--border-radius);
        padding: 1rem;
        color: var(--text-dark);
    }
    
    /* 数据表格 */
    .stDataFrame {
        border-radius: var(--border-radius);
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 166, 228, 0.1);
    }
    
    /* 分隔线 */
    hr {
        margin: 2rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
    }
    
    /* 侧边栏 */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #e8f4f8 100%);
    }
    
    /* 版本信息卡片 */
    .version-card {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
        color: white;
        padding: 1.5rem;
        border-radius: var(--border-radius);
        margin-bottom: 2rem;
        box-shadow: 0 6px 12px rgba(0, 166, 228, 0.2);
    }
    
    .version-card h3 {
        color: white !important;
        margin: 0 0 1rem 0;
        font-size: 1.3rem;
    }
    
    .version-info {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        font-size: 0.95rem;
    }
    
    .version-info div {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .version-info strong {
        min-width: 80px;
    }
    
    /* 步骤卡片 */
    .step-card {
        background: white;
        padding: 2rem;
        border-radius: var(--border-radius);
        box-shadow: 0 4px 6px rgba(0, 166, 228, 0.1);
        margin-bottom: 2rem;
        border-top: 4px solid var(--primary-color);
    }
    
    .step-number {
        display: inline-block;
        width: 40px;
        height: 40px;
        background: var(--primary-color);
        color: white;
        border-radius: 50%;
        text-align: center;
        line-height: 40px;
        font-weight: bold;
        font-size: 1.2rem;
        margin-right: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# App configuration
APP_CONFIG = {
    "app_title": "📊 Keepa数据整理与可视化",
    "author": "海翼IDC团队",
    "version": "v1.1.1",
    "contact": "idc@oceanwing.com",
    "company": "Anker Oceanwing Inc."
}

# Header
st.title(APP_CONFIG["app_title"])

# Version info card
st.markdown(f"""
<div class="version-card">
    <h3>🚀 应用信息</h3>
    <div class="version-info">
        <div><strong>版本:</strong> {APP_CONFIG["version"]}</div>
        <div><strong>作者:</strong> {APP_CONFIG["author"]}</div>
        <div><strong>公司:</strong> {APP_CONFIG["company"]}</div>
        <div><strong>联系方式:</strong> {APP_CONFIG["contact"]}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Section 1: Data Processing
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown('<span class="step-number">1</span><h2 style="display: inline-block;">数据处理</h2>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📁 选择Keepa导出的Excel文件", type=['xlsx'], key="data_processing")

if uploaded_file is not None:
    # Read Excel file
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ 无法读取Excel文件: {str(e)}")
        st.write("请确保上传的文件是有效的Excel文件(.xlsx)。")
        uploaded_file = None

if uploaded_file is not None:
    # Data cleaning: Convert date column to datetime
    df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
    
    # Group by year-month, get last day record of each month
    df['年月'] = df['日期'].dt.to_period('M')
    last_day_df = df.groupby('年月').apply(lambda x: x.loc[x['日期'].idxmax()]).reset_index(drop=True)
    
    # Calculate days with Prime, Coupon, and Deal prices
    monthly_counts = df.groupby('年月').agg({
        'Prime价格($)': lambda x: x.notna().sum(),
        'Coupon价格($)': lambda x: x.notna().sum(),
        'Deal价格($)': lambda x: x.notna().sum()
    }).reset_index()
    monthly_counts.columns = ['年月', 'Prime价格天数', 'Coupon价格天数', 'Deal价格天数']
    
    # Select required columns
    result_df = last_day_df[['日期', '评分', '评分数', '年月']].copy()
    
    # Ensure rating and review count are numeric, fill NA with 0
    result_df['评分'] = pd.to_numeric(result_df['评分'], errors='coerce').fillna(0)
    result_df['评分数'] = pd.to_numeric(result_df['评分数'], errors='coerce').fillna(0)
    
    # Calculate review count growth percentage (numeric format, no + or %)
    result_df['评分数增长%'] = result_df['评分数'].pct_change() * 100
    result_df['评分数增长%'] = result_df['评分数增长%'].fillna(0).round(1)
    
    # Format date to YYYY-MM
    result_df['日期'] = result_df['日期'].dt.strftime('%Y-%m')
    
    # Merge price days counts
    result_df = result_df.merge(
        monthly_counts[['年月', 'Prime价格天数', 'Coupon价格天数', 'Deal价格天数']],
        left_on='年月',
        right_on='年月',
        how='left'
    )
    
    # Drop temporary column
    result_df = result_df.drop(columns=['年月'])
    
    # Display the processed data with formatted percentage for display only
    display_df = result_df.copy()
    display_df['评分数增长%'] = display_df['评分数增长%'].apply(lambda x: f"{x:.1f}%")
    
    st.success("✅ 数据处理完成!")
    st.write("### 📊 处理后的数据预览")
    st.dataframe(display_df, use_container_width=True)
    
    # Convert DataFrame to Excel
    excel_buffer = io.BytesIO()
    result_df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_data = excel_buffer.getvalue()
    
    # Download button for Excel
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.download_button(
            label="⬇️ 下载处理后的Excel文件",
            data=excel_data,
            file_name="monthly_last_day_ratings.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # Reminder about adding sales column
    st.info("💡 请在下载的Excel文件的H列添加'销量'列、I列添加'销售额'列,以包含按月销售数据。")
else:
    st.info("👆 请上传Excel文件以继续处理。")

st.markdown("---")

# Section 2: Visualization
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown('<span class="step-number">2</span><h2 style="display: inline-block;">可视化</h2>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

uploaded_xlsx = st.file_uploader("📁 选择包含销量的Excel文件(在第一步生成的文件中:H列填入对应月份的销量,表头为'销量';I列填入对应月份的销售额,表头为'销售额')", type=['xlsx'], key="visualization")

if uploaded_xlsx is not None:
    # Reset file pointer
    uploaded_xlsx.seek(0)
    
    # Read Excel file
    try:
        viz_df = pd.read_excel(uploaded_xlsx, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ 无法读取Excel文件: {str(e)}")
        st.write("请确保上传的文件是有效的Excel文件(.xlsx格式)且包含正确的列。")
        uploaded_xlsx = None

if uploaded_xlsx is not None:
    # Check required columns
    required_columns = ['日期', '评分', '评分数', 'Prime价格天数', 'Coupon价格天数', 'Deal价格天数', '销量']
    missing_columns = [col for col in required_columns if col not in viz_df.columns]
    
    if missing_columns:
        st.error(f"❌ 上传的Excel文件缺少以下必要列:{', '.join(missing_columns)}")
    else:
        # Ensure data types
        viz_df['日期'] = pd.to_datetime(viz_df['日期'], errors='coerce')
        viz_df['评分'] = pd.to_numeric(viz_df['评分'], errors='coerce').fillna(0)
        viz_df['评分数'] = pd.to_numeric(viz_df['评分数'], errors='coerce').fillna(0)
        viz_df['Prime价格天数'] = pd.to_numeric(viz_df['Prime价格天数'], errors='coerce').fillna(0)
        viz_df['Coupon价格天数'] = pd.to_numeric(viz_df['Coupon价格天数'], errors='coerce').fillna(0)
        viz_df['Deal价格天数'] = pd.to_numeric(viz_df['Deal价格天数'], errors='coerce').fillna(0)
        viz_df['销量'] = pd.to_numeric(viz_df['销量'], errors='coerce').fillna(0)
        
        # Calculate cumulative sales and review rate (当月评分数 / 累积销量 * 100)
        viz_df['累积销量'] = viz_df['销量'].cumsum()
        viz_df['留评率'] = viz_df.apply(
            lambda x: round((x['评分数'] / x['累积销量'] * 100), 1) if x['累积销量'] != 0 else 0, axis=1
        )
        
        # Format date to YY/MM
        viz_df['日期'] = viz_df['日期'].dt.strftime('%y/%m')
        
        # Prepare data for charts
        labels = viz_df['日期'].tolist()
        ratings = viz_df['评分'].tolist()
        review_counts = viz_df['评分数'].tolist()
        sales = viz_df['销量'].tolist()
        prime_days = viz_df['Prime价格天数'].tolist()
        coupon_days = viz_df['Coupon价格天数'].tolist()
        deal_days = viz_df['Deal价格天数'].tolist()
        review_rates = viz_df['留评率'].tolist()
        
        # Calculate max sales and review rate for y-axis
        max_sales = max(sales) if sales else 1000
        sales_y_max = math.ceil(max_sales / 1000) * 1000
        max_review_rate = max(review_rates) * 1.1 if review_rates else 100
        
        st.success("✅ 数据加载成功!")
        
        # HTML template for charts (keeping original visualization code)
        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>产品数据趋势图</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels"></script>
    <style>
        body {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e8f4f8 100%);
        }}
        canvas {{
            margin: 20px 0;
            max-width: 900px;
            width: 100%;
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 166, 228, 0.1);
        }}
        h2 {{
            margin: 10px 0;
            color: #00a6e4;
        }}
    </style>
</head>
<body>
    <h2>评分数、评分和销量趋势</h2>
    <canvas id="lineChart" width="900" height="400"></canvas>
    <h2>Prime、Coupon、Deal价格天数和销量</h2>
    <canvas id="barChart" width="900" height="400"></canvas>
    <h2>留评率趋势</h2>
    <canvas id="reviewRateChart" width="900" height="400"></canvas>

    <script>
        // 折线图(评分数、评分和销量)
        const lineCtx = document.getElementById('lineChart').getContext('2d');
        new Chart(lineCtx, {{
            type: 'line',
            data: {{
                labels: {labels},
                datasets: [
                    {{
                        label: '评分数',
                        data: {review_counts},
                        borderColor: '#4e79a7',
                        backgroundColor: '#4e79a7',
                        fill: false,
                        tension: 0.1,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'y1'
                    }},
                    {{
                        label: '评分',
                        data: {ratings},
                        borderColor: '#f28e2b',
                        backgroundColor: '#f28e2b',
                        fill: false,
                        tension: 0.1,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'y2'
                    }},
                    {{
                        label: '销量',
                        data: {sales},
                        borderColor: '#e15759',
                        backgroundColor: '#e15759',
                        fill: false,
                        tension: 0.1,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'y3'
                    }}
                ]
            }},
            options: {{
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: '日期 (年/月)'
                        }},
                        ticks: {{
                            maxRotation: 45,
                            minRotation: 45
                        }}
                    }},
                    y1: {{
                        type: 'linear',
                        position: 'left',
                        title: {{
                            display: true,
                            text: '评分数'
                        }},
                        beginAtZero: true,
                        max: {max(review_counts) * 1.1 if review_counts else 1000}
                    }},
                    y2: {{
                        type: 'linear',
                        position: 'right',
                        title: {{
                            display: true,
                            text: '评分'
                        }},
                        beginAtZero: true,
                        max: 5,
                        ticks: {{
                            stepSize: 0.1
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }}
                    }},
                    y3: {{
                        type: 'linear',
                        position: 'right',
                        title: {{
                            display: true,
                            text: '销量'
                        }},
                        beginAtZero: true,
                        max: {sales_y_max},
                        grid: {{
                            drawOnChartArea: false
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    tooltip: {{
                        enabled: true
                    }},
                    datalabels: {{
                        display: true,
                        formatter: (value, context) => {{
                            if (context.dataset.label === '评分') return value.toFixed(1);
                            return value;
                        }},
                        align: 'top',
                        offset: 4,
                        font: {{
                            size: 10
                        }},
                        color: '#333'
                    }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});

        // 混合图(柱状图+销量折线)
        const barCtx = document.getElementById('barChart').getContext('2d');
        new Chart(barCtx, {{
            type: 'bar',
            data: {{
                labels: {labels},
                datasets: [
                    {{
                        label: 'Prime价格天数',
                        data: {prime_days},
                        backgroundColor: '#4e79a7',
                        yAxisID: 'y1'
                    }},
                    {{
                        label: 'Coupon价格天数',
                        data: {coupon_days},
                        backgroundColor: '#f28e2b',
                        yAxisID: 'y1'
                    }},
                    {{
                        label: 'Deal价格天数',
                        data: {deal_days},
                        backgroundColor: '#e15759',
                        yAxisID: 'y1'
                    }},
                    {{
                        label: '销量',
                        data: {sales},
                        type: 'line',
                        borderColor: '#76b7b2',
                        backgroundColor: '#76b7b2',
                        fill: false,
                        tension: 0.1,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'y2'
                    }}
                ]
            }},
            options: {{
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: '日期 (年/月)'
                        }},
                        ticks: {{
                            maxRotation: 45,
                            minRotation: 45
                        }}
                    }},
                    y1: {{
                        type: 'linear',
                        position: 'left',
                        title: {{
                            display: true,
                            text: '天数'
                        }},
                        beginAtZero: true,
                        max: 35
                    }},
                    y2: {{
                        type: 'linear',
                        position: 'right',
                        title: {{
                            display: true,
                            text: '销量'
                        }},
                        beginAtZero: true,
                        max: {sales_y_max},
                        grid: {{
                            drawOnChartArea: false
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    tooltip: {{
                        enabled: true
                    }},
                    datalabels: {{
                        display: (context) => context.dataset.data[context.dataIndex] !== 0,
                        formatter: (value) => value,
                        align: (context) => context.dataset.type === 'line' ? 'top' : 'end',
                        anchor: (context) => context.dataset.type === 'line' ? 'center' : 'end',
                        offset: 4,
                        font: {{
                            size: 10
                        }},
                        color: '#333'
                    }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});

        // 折线图(留评率)
        const reviewRateCtx = document.getElementById('reviewRateChart').getContext('2d');
        new Chart(reviewRateCtx, {{
            type: 'line',
            data: {{
                labels: {labels},
                datasets: [
                    {{
                        label: '留评率 (%)',
                        data: {review_rates},
                        borderColor: '#59a14f',
                        backgroundColor: '#59a14f',
                        fill: false,
                        tension: 0.1,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'y'
                    }}
                ]
            }},
            options: {{
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: '日期 (年/月)'
                        }},
                        ticks: {{
                            maxRotation: 45,
                            minRotation: 45
                        }}
                    }},
                    y: {{
                        type: 'linear',
                        position: 'left',
                        title: {{
                            display: true,
                            text: '留评率 (%)'
                        }},
                        beginAtZero: true,
                        max: {max_review_rate},
                        ticks: {{
                            stepSize: {max_review_rate / 10 if max_review_rate > 0 else 10}
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    tooltip: {{
                        enabled: true,
                        callbacks: {{
                            label: function(context) {{
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                            }}
                        }}
                    }},
                    datalabels: {{
                        display: true,
                        formatter: (value) => value.toFixed(1) + '%',
                        align: 'top',
                        offset: 4,
                        font: {{
                            size: 8
                        }},
                        color: '#333'
                    }}
                }}
            }},
            plugins: [ChartDataLabels]
        }});
    </script>
</body>
</html>
"""
        
        sales_amount = viz_df['销售额'].astype(float).fillna(0).tolist() if '销售额' in viz_df.columns else [0] * len(viz_df)

        # 绿色水平虚线阈值(基于销售额最大值,严格大于)
        max_amt = max(sales_amount) if sales_amount else 0
        _thresholds = [100000, 300000, 500000, 750000, 1000000]
        _selected = [t for t in _thresholds if max_amt > t]

        # 注解线段JS片段
        def _fmt(n):
            try:
                return f"{int(n):,}"
            except:
                return str(n)
        _annotations_js = ",\n".join([
            f"""
            "line{i+1}": {{
              "type": "line",
              "yMin": {t}, "yMax": {t},
              "yScaleID": "y2",
              "borderColor": "rgba(0,128,0,0.9)",
              "borderWidth": 2,
              "borderDash": [6,6],
              "label": {{
                "display": true,
                "content": "{_fmt(t)}",
                "position": "end",
                "backgroundColor": "rgba(0,0,0,0.06)",
                "color": "#0a0"
              }}
            }}
            """.strip()
            for i, t in enumerate(_selected)
        ])

        sales_chart_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Sales Chart</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; margin: 24px; background: linear-gradient(135deg, #f5f7fa 0%, #e8f4f8 100%); }}
  h1 {{ margin: 0 0 16px; color: #00a6e4; }}
  .chart-wrap {{ max-width: 1200px; height: 520px; background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0, 166, 228, 0.1); }}
</style>
</head>
<body>

<h1>销量 & 销售额</h1>
<div class="chart-wrap"><canvas id="salesAmountChart"></canvas></div>

<!-- Chart.js 与插件 -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@2.2.1/dist/chartjs-plugin-annotation.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2"></script>

<script>
(function(){{

  var Annotation = window['chartjs-plugin-annotation'] || window.ChartAnnotation;
  if (Annotation && window.Chart && typeof window.Chart.register === 'function') {{
    window.Chart.register(Annotation);
  }}
  if (window.Chart && typeof window.Chart.register === 'function') {{
    window.Chart.register(window.ChartDataLabels);
  }}


  const labels = {labels};
  const vol = {sales};
  const amt = {sales_amount};

  const ctx = document.getElementById('salesAmountChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels,
      datasets: [
        {{
          type: 'bar',
          label: '销量',
          data: vol,
          yAxisID: 'y1'
        }},
        {{
          type: 'line',
          label: '销售额',
          data: amt,
          yAxisID: 'y2',
          borderWidth: 2,
          tension: 0.25,
          pointRadius: 3,
          pointHoverRadius: 5
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        y1: {{
          type: 'linear',
          position: 'left',
          beginAtZero: true,
          title: {{ display: true, text: '销量' }}
        }},
        y2: {{
          type: 'linear',
          position: 'right',
          beginAtZero: true,
          title: {{ display: true, text: '销售额' }},
          grid: {{ drawOnChartArea: false }}
        }}
      }},
      plugins: {{
        legend: {{ position: 'top' }},
        tooltip: {{ mode: 'index', intersect: false }},
        annotation: {{
          annotations: {{
            {_annotations_js}
          }}
        }},
        datalabels: {{
          display: (ctx) => ctx?.dataset?.label === '销售额' && ctx.dataset.data[ctx.dataIndex] !== 0,
          align: 'top',
          anchor: 'end',
          offset: 4,
          formatter: (value) => {{
            try {{

              return Number(value).toLocaleString();
            }} catch (e) {{
              return value;
            }}
          }},
          color: '#333',
          font: {{ size: 10, weight: 'bold' }}
        }}
      }}
    }}
  }});
}})();
</script>

</body>
</html>
"""

        # Download buttons
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="⬇️ 下载可视化HTML文件",
                data=html_template,
                file_name="product_trend_charts.html",
                mime="text/html",
                use_container_width=True
            )
        
        with col2:
            st.download_button(
                label="⬇️ 下载销量-销售额单图",
                data=sales_chart_html,
                file_name="sales_chart_fixed_green.html",
                mime="text/html",
                use_container_width=True
            )
        
        st.success("🎉 可视化文件已准备好下载!")

else:
    st.info("👆 请上传包含销量的Excel文件以生成可视化图表。")
