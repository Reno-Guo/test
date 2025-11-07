import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime

# Page config
st.set_page_config(page_title="Cohort Analysis Heatmap", layout="wide")

st.title("🧠 Cohort Analysis Heatmap Generator")
st.markdown("Upload your CSV file from the SQL query to visualize retention rates or sales in a heatmap. Rows are acquisition cohorts (months), columns are relative months since acquisition.")

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv", help="Upload the output CSV from the cohort analysis query.")

if uploaded_file is not None:
    # Read CSV
    df = pd.read_csv(uploaded_file)
    st.success(f"Uploaded file with {len(df)} rows.")
    
    # Display raw data preview
    with st.expander("View Raw Data", expanded=False):
        st.dataframe(df.head(10))
    
    # Data preprocessing
    @st.cache_data
    def preprocess_data(df):
        df = df.copy()
        # Ensure numeric columns are properly typed
        df['new_user_count'] = pd.to_numeric(df['new_user_count'], errors='coerce').fillna(0).astype(int)
        df['active_users'] = pd.to_numeric(df['active_users'], errors='coerce').fillna(0).astype(int)
        df['total_sales'] = pd.to_numeric(df['total_sales'], errors='coerce').fillna(0)
        
        df['acquisition_date'] = pd.to_datetime(df['acquisition_month'])
        df['sales_date'] = pd.to_datetime(df['sales_month'])
        df['cohort_month'] = df['acquisition_date'].dt.to_period('M')
        df['sales_period'] = df['sales_date'].dt.to_period('M')
        df['relative_month'] = (df['sales_period'] - df['cohort_month']).apply(lambda x: x.n)
        return df
    
    df = preprocess_data(df)
    
    # Metrics selection
    col1, col2 = st.columns([3, 1])
    with col1:
        metric = st.selectbox(
            "Select Metric for Heatmap",
            ["Retention Rate (%)", "Total Sales"],
            help="Retention Rate: Active users as % of new user count in cohort.\nTotal Sales: Sum of sales in the period."
        )
    with col2:
        max_months = st.slider("Max Relative Months to Display", 1, 12, 6, help="Limit columns to first N months for cleaner view.")
    
    # Prepare pivot data
    @st.cache_data
    def create_pivot(df, metric, max_months):
        cohort_sizes = df.groupby('cohort_month')['new_user_count'].first()
        
        # Use aggfunc='sum' for both to handle any potential duplicates safely
        if metric == "Retention Rate (%)":
            pivot_data = df.pivot_table(index='cohort_month', columns='relative_month', values='active_users', aggfunc='sum')
            # Fill NaN with 0 for missing months
            pivot_data = pivot_data.fillna(0)
            # Normalize to cohort size
            pivot_data = pivot_data.div(cohort_sizes.reindex(pivot_data.index), axis=0) * 100
            # Format as percentage
            pivot_data = pivot_data.round(1)
            fmt = '.1f'
            unit = '%'
        else:
            pivot_data = df.pivot_table(index='cohort_month', columns='relative_month', values='total_sales', aggfunc='sum')
            pivot_data = pivot_data.fillna(0)
            fmt = '.0f'
            unit = '$'
        
        # Limit columns
        pivot_data = pivot_data.iloc[:, :max_months]
        
        # Sort cohorts chronologically
        pivot_data = pivot_data.sort_index()
        
        return pivot_data, fmt, unit
    
    pivot_data, fmt, unit = create_pivot(df, metric, max_months)
    
    if not pivot_data.empty:
        # Create heatmap
        fig, ax = plt.subplots(figsize=(12, len(pivot_data) * 0.5 + 2))
        
        # Customize columns labels
        col_labels = [f'Month {i}' for i in range(max_months)]
        sns.heatmap(
            pivot_data, 
            annot=True, 
            fmt=fmt, 
            cmap='YlGnBu', 
            ax=ax,
            cbar_kws={'label': f'{metric} ({unit})'},
            linewidths=0.5
        )
        
        # Labels
        ax.set_title(f'{metric} Heatmap by Cohort', fontsize=16, fontweight='bold')
        ax.set_xlabel('Relative Months Since Acquisition', fontsize=12)
        ax.set_ylabel('Acquisition Cohort (Month)', fontsize=12)
        ax.set_xticklabels(col_labels, rotation=0)
        plt.xticks(rotation=0)
        plt.yticks(rotation=0)
        
        st.pyplot(fig)
        
        # Display pivot table below
        st.subheader("Pivot Table Data")
        st.dataframe(pivot_data)
        
        # Stats
        st.subheader("Quick Stats")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Cohorts", len(pivot_data))
        with col2:
            if metric == "Retention Rate (%)":
                avg_retention = pivot_data.mean().mean()
                st.metric("Avg Retention Rate", f"{avg_retention:.1f}%")
            else:
                avg_sales = pivot_data.mean().mean()
                st.metric("Avg Monthly Sales", f"${avg_sales:,.0f}")
        with col3:
            total_sales = df['total_sales'].sum()
            st.metric("Grand Total Sales", f"${total_sales:,.0f}")
    
    else:
        st.warning("No data available for the selected options. Check your CSV structure.")
else:
    st.info("👆 Please upload a CSV file to get started.")
    st.markdown("**Expected CSV Columns:** `acquisition_year`, `acquisition_month`, `new_user_count`, `sales_month`, `sales_month_num`, `active_users`, `total_sales`")

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit. Run with `streamlit run app.py`.")
