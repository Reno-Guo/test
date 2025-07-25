import streamlit as st
import pandas as pd
import io

# Streamlit app title
st.title("Keepa数据整理")

# File uploader
uploaded_file = st.file_uploader("选择keepa导出文件", type=['xlsx', 'xls'])

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
    st.write("Processed Data Preview:")
    st.dataframe(result_df)
    
    # Convert DataFrame to CSV
    csv_buffer = io.StringIO()
    result_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_data = csv_buffer.getvalue()
    
    # Download button
    st.download_button(
        label="Download Processed CSV",
        data=csv_data,
        file_name="monthly_last_day_ratings.csv",
        mime="text/csv"
    )
    
    # Reminder about adding sales column
    st.info("请在下载的 CSV 文件的 H 列添加 '销量' 列，以包含按月销售数据。")
else:
    st.write("Please upload an Excel file to proceed.")
