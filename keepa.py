import streamlit as st
import pandas as pd
import io
import math

# Streamlit app title
st.title("Keepa数据整理与可视化")

# Section 1: Data Processing
st.header("数据处理")
uploaded_file = st.file_uploader("选择Keepa导出的Excel文件", type=['xlsx', 'xls'], key="data_processing")

if uploaded_file is not None:
    # Read Excel file
    df = pd.read_excel(uploaded_file, sheet_name=0)
    
    # Data cleaning: Convert date column to datetime
    df['日期'] = pd.to_datetime(df['日期'])
    
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
    
    # Calculate review count growth percentage
    result_df['评分数增长%'] = result_df['评分数'].pct_change() * 100
    result_df['评分数增长%'] = result_df['评分数增长%'].fillna(0).round(1)
    result_df['评分数增长%'] = result_df['评分数增长%'].apply(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
    
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
    
    # Display the processed data
    st.write("### 处理后的数据预览")
    st.dataframe(result_df)
    
    # Convert DataFrame to CSV
    csv_buffer = io.StringIO()
    result_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_data = csv_buffer.getvalue()
    
    # Download button for CSV
    st.download_button(
        label="下载处理后的CSV",
        data=csv_data,
        file_name="monthly_last_day_ratings.csv",
        mime="text/csv"
    )
    
    # Reminder about adding sales column
    st.info("请在下载的 CSV 文件的 H 列添加 '销量' 列，以包含按月销售数据。")
else:
    st.write("请上传Excel文件以继续处理。")

# Section 2: Visualization
st.header("可视化")
uploaded_csv = st.file_uploader("选择包含销量的CSV文件", type=['csv'], key="visualization")

if uploaded_csv is not None:
    # Read CSV file
    viz_df = pd.read_csv(uploaded_csv, encoding='utf-8-sig')
    
    # Check required columns
    required_columns = ['日期', '评分', '评分数', 'Prime价格天数', 'Coupon价格天数', 'Deal价格天数', '销量']
    missing_columns = [col for col in required_columns if col not in viz_df.columns]
    
    if missing_columns:
        st.error(f"上传的CSV文件缺少以下必要列：{', '.join(missing_columns)}")
    else:
        # Ensure data types
        viz_df['日期'] = pd.to_datetime(viz_df['日期'], errors='coerce')
        viz_df['评分'] = pd.to_numeric(viz_df['评分'], errors='coerce').fillna(0)
        viz_df['评分数'] = pd.to_numeric(viz_df['评分数'], errors='coerce').fillna(0)
        viz_df['Prime价格天数'] = pd.to_numeric(viz_df['Prime价格天数'], errors='coerce').fillna(0)
        viz_df['Coupon价格天数'] = pd.to_numeric(viz_df['Coupon价格天数'], errors='coerce').fillna(0)
        viz_df['Deal价格天数'] = pd.to_numeric(viz_df['Deal价格天数'], errors='coerce').fillna(0)
        viz_df['销量'] = pd.to_numeric(viz_df['销量'], errors='coerce').fillna(0)
        
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
        
        # Calculate max sales for y-axis
        max_sales = max(sales) if sales else 1000
        sales_y_max = math.ceil(max_sales / 1000) * 1000
        
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
else:
    st.write("请上传包含销量的CSV文件以生成可视化图表。")
