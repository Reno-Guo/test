import streamlit as st
import pandas as pd
import io
import math

# App configuration
APP_CONFIG = {
    "app_title": "Keepa数据整理与可视化",
    "author": "海翼IDC团队",
    "version": "v1.1.0",
    "contact": "idc@oceanwing.com",
    "company": "Anker Oceanwing Inc."
}

# Streamlit app title
st.title(APP_CONFIG["app_title"])

# Display app configuration
st.markdown(f"""
**版本**: {APP_CONFIG["version"]}  
**作者**: {APP_CONFIG["author"]}  
**公司**: {APP_CONFIG["company"]}  
**联系方式**: {APP_CONFIG["contact"]}  
""")

# Section 1: Data Processing
st.header("数据处理")
uploaded_file = st.file_uploader("选择Keepa导出的Excel文件", type=['xlsx'], key="data_processing")

if uploaded_file is not None:
    # Read Excel file
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0, engine='openpyxl')
    except Exception as e:
        st.error(f"无法读取Excel文件: {str(e)}")
        st.write("请确保上传的文件是有效的Excel文件（.xlsx）。")
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
    st.write("### 处理后的数据预览")
    st.dataframe(display_df)
    
    # Convert DataFrame to Excel
    excel_buffer = io.BytesIO()
    result_df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_data = excel_buffer.getvalue()
    
    # Download button for Excel
    st.download_button(
        label="下载处理后的Excel文件",
        data=excel_data,
        file_name="monthly_last_day_ratings.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Reminder about adding sales column
    st.info("请在下载的Excel文件的H列添加'销量'列、I列添加'销售额'列，以包含按月销售数据。")
else:
    st.write("请上传Excel文件以继续处理。")

# Section 2: Visualization
st.header("可视化")
uploaded_xlsx = st.file_uploader("选择包含销量的Excel文件(在第一步生成的文件中：H列填入对应月份的销量，表头为“销量”；I列填入对应月份的销售额，表头为“销售额”)", type=['xlsx'], key="visualization")

if uploaded_xlsx is not None:
    # Reset file pointer
    uploaded_xlsx.seek(0)
    
    # Read Excel file
    try:
        viz_df = pd.read_excel(uploaded_xlsx, engine='openpyxl')
    except Exception as e:
        st.error(f"无法读取Excel文件: {str(e)}")
        st.write("请确保上传的文件是有效的Excel文件（.xlsx格式）且包含正确的列。")
        uploaded_xlsx = None

if uploaded_xlsx is not None:
    # Check required columns
    required_columns = ['日期', '评分', '评分数', 'Prime价格天数', 'Coupon价格天数', 'Deal价格天数', '销量']
    missing_columns = [col for col in required_columns if col not in viz_df.columns]
    
    if missing_columns:
        st.error(f"上传的Excel文件缺少以下必要列：{', '.join(missing_columns)}")
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
        
        # HTML template for charts
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
        }}
        canvas {{
            margin: 20px 0;
            max-width: 900px;
            width: 100%;
        }}
        h2 {{
            margin: 10px 0;
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
        // 折线图（评分数、评分和销量）
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

        // 混合图（柱状图+销量折线）
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

        // 折线图（留评率）
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
        # Download button for HTML
        st.download_button(
            label="下载可视化HTML文件",
            data=html_template,
            file_name="product_trend_charts.html",
            mime="text/html"
        )
        # ===== 新增：导出“销量+销售额（绿色水平虚线）”的单独HTML =====
        # 销售额列若不存在则以0填充
        sales_amount = viz_df['销售额'].astype(float).fillna(0).tolist() if '销售额' in viz_df.columns else [0] * len(viz_df)

        # 绿色水平虚线阈值（基于销售额最大值，严格大于）
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
            \"line{i+1}\": {{
              \"type\": \"line\",
              \"yMin\": {t}, \"yMax\": {t},
              \"yScaleID\": \"y2\",
              \"borderColor\": \"rgba(0,128,0,0.9)\",
              \"borderWidth\": 2,
              \"borderDash\": [6,6],
              \"label\": {{
                \"display\": true,
                \"content\": \"{_fmt(t)}\",
                \"position\": \"end\",
                \"backgroundColor\": \"rgba(0,0,0,0.06)\",
                \"color\": \"#0a0\"
              }}
            }}
            """.strip()
            for i, t in enumerate(_selected)
        ])

        sales_chart_html = f"""
<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\">
<title>Sales Chart</title>
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; margin: 24px; }}
  h1 {{ margin: 0 0 16px; }}
  .chart-wrap {{ max-width: 1200px; height: 520px; }}
</style>
</head>
<body>

<h1>销量 & 销售额</h1>
<div class=\"chart-wrap\"><canvas id=\"salesAmountChart\"></canvas></div>

<script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js\"></script>
<script src=\"https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@2.2.1/dist/chartjs-plugin-annotation.min.js\"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>

<script>
(function(){
  var Annotation = window['chartjs-plugin-annotation'] || window.ChartAnnotation;
  if (Annotation && window.Chart && typeof window.Chart.register === 'function') {
    window.Chart.register(Annotation);
  }
  if (window.ChartDataLabels && window.Chart && typeof window.Chart.register === 'function') {
    window.Chart.register(window.ChartDataLabels);
  }

  const labels = {labels};
  const vol = {sales};
  const amt = {sales_amount};

  const ctx = document.getElementById('salesAmountChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          type: 'bar',
          label: '销量',
          data: vol,
          yAxisID: 'y1',
          datalabels: {
            display: false
          }
        },
        {
          type: 'line',
          label: '销售额',
          data: amt,
          yAxisID: 'y2',
          borderWidth: 2,
          tension: 0.25,
          datalabels: {
            display: false
          }
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        y1: {
          type: 'linear',
          position: 'left',
          beginAtZero: true,
          title: { display: true, text: '销量' }
        },
        y2: {
          type: 'linear',
          position: 'right',
          beginAtZero: true,
          title: { display: true, text: '销售额' },
          grid: { drawOnChartArea: false }
        }
      },
      plugins: {
        legend: { position: 'top' },
        tooltip: { mode: 'index', intersect: false },
        annotation: {
          annotations: {
            {_annotations_js}
          }
        },
        datalabels: {
          display: function(context) {
            return context.dataset.type === 'bar';
          },
          anchor: 'end',
          align: 'top',
          formatter: function(value, context) {
            return amt[context.dataIndex];
          },
          color: '#000',
          font: {
            weight: 'bold'
          }
        }
      }
    }
  });
})();
</script>

</body>
</html>
"""

        st.download_button(
            label="下载销量-销售额单图（sales_chart_fixed_green.html）",
            data=sales_chart_html,
            file_name="sales_chart_fixed_green.html",
            mime="text/html"
        )

else:
    st.write("请上传包含销量的Excel文件以生成可视化图表。")
