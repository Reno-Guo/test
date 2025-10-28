import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="CPC计算器", page_icon="💰", layout="wide")

st.title("🔢 CPC计算器")
st.markdown("**基于SIF关键词转化率的综合CPC计算工具**")

# 初始化session state
if 'keyword_count' not in st.session_state:
    st.session_state.keyword_count = 1

if 'keywords_data' not in st.session_state:
    st.session_state.keywords_data = {}

# 添加关键词按钮
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("➕ 添加关键词", use_container_width=True):
        st.session_state.keyword_count += 1

# 删除关键词按钮（当有多于1个关键词时显示）
if st.session_state.keyword_count > 1:
    with col1:
        if st.button("➖ 删除最后一个关键词", use_container_width=True):
            st.session_state.keyword_count -= 1
            # 删除最后一个关键词的数据
            if f'keyword_{st.session_state.keyword_count}' in st.session_state.keywords_data:
                del st.session_state.keywords_data[f'keyword_{st.session_state.keyword_count}']

st.markdown("---")

# 数据输入区域
keywords_list = []

for i in range(st.session_state.keyword_count):
    st.subheader(f"关键词 {i+1}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        keyword = st.text_input(
            "关键词名称", 
            key=f"keyword_name_{i}",
            placeholder="输入关键词"
        )
    
    with col2:
        aba_rank = st.number_input(
            "ABA Rank", 
            min_value=1,
            value=1,
            step=1,
            key=f"aba_rank_{i}"
        )
    
    with col3:
        recommended_cpc = st.number_input(
            "推荐CPC ($)", 
            min_value=0.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            key=f"rec_cpc_{i}"
        )
    
    with col4:
        max_cpc = st.number_input(
            "最高CPC ($)", 
            min_value=0.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            key=f"max_cpc_{i}"
        )
    
    if keyword:
        keywords_list.append({
            'keyword': keyword,
            'aba_rank': aba_rank,
            'recommended_cpc': recommended_cpc,
            'max_cpc': max_cpc
        })
    
    st.markdown("---")

# 计算按钮
if st.button("📊 计算综合CPC", type="primary", use_container_width=True):
    if len(keywords_list) == 0:
        st.error("❌ 请至少输入一个关键词的完整信息！")
    else:
        # 创建DataFrame
        df = pd.DataFrame(keywords_list)
        
        # 计算价值分数 S = 1 / [ln(ABA_Rank)]²
        df['score_S'] = 1 / (np.log(df['aba_rank']) ** 2)
        
        # 计算权重 W = S / ∑S
        total_score = df['score_S'].sum()
        df['weight_W'] = df['score_S'] / total_score
        
        # 计算加权CPC
        df['weighted_rec_cpc'] = df['weight_W'] * df['recommended_cpc']
        df['weighted_max_cpc'] = df['weight_W'] * df['max_cpc']
        
        # 计算综合CPC
        comprehensive_rec_cpc = df['weighted_rec_cpc'].sum()
        comprehensive_max_cpc = df['weighted_max_cpc'].sum()
        
        # 显示结果
        st.success("✅ 计算完成！")
        
        # 显示综合CPC结果
        st.markdown("## 📈 计算结果")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                label="基于推荐CPC的综合CPC",
                value=f"${comprehensive_rec_cpc:.4f}"
            )
        
        with col2:
            st.metric(
                label="基于最高CPC的综合CPC",
                value=f"${comprehensive_max_cpc:.4f}"
            )
        
        # 显示详细数据表格
        st.markdown("## 📋 详细计算数据")
        
        # 准备显示的DataFrame
        display_df = df.copy()
        display_df['价值分数 (S)'] = display_df['score_S'].round(6)
        display_df['权重 (W)'] = (display_df['weight_W'] * 100).round(2).astype(str) + '%'
        display_df['加权推荐CPC'] = display_df['weighted_rec_cpc'].round(4)
        display_df['加权最高CPC'] = display_df['weighted_max_cpc'].round(4)
        
        final_display = display_df[[
            'keyword', 'aba_rank', 'recommended_cpc', 'max_cpc',
            '价值分数 (S)', '权重 (W)', '加权推荐CPC', '加权最高CPC'
        ]]
        
        final_display.columns = [
            '关键词', 'ABA Rank', '推荐CPC', '最高CPC',
            '价值分数 (S)', '权重 (W)', '加权推荐CPC', '加权最高CPC'
        ]
        
        st.dataframe(final_display, use_container_width=True, hide_index=True)
        
        # 显示计算公式说明
        with st.expander("📐 计算公式说明"):
            st.markdown("""
            ### 计算方法：
            
            1. **价值分数 (S)**  
               `S = 1 / [ln(ABA_Rank)]²`
            
            2. **权重 (W)**  
               `W = S / ∑S`
            
            3. **综合CPC**  
               `综合CPC = ∑(W × CPC)`
            
            ---
            
            - 价值分数越高，表示该关键词在排名上的价值越大
            - 权重表示每个关键词对综合CPC的贡献比例
            - 最终综合CPC是所有关键词加权平均的结果
            """)

# 页面底部说明
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    💡 提示：输入关键词数据后点击"计算综合CPC"按钮查看结果
</div>
""", unsafe_allow_html=True)
