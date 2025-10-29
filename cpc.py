import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="CPC计算器", page_icon="💰", layout="wide")

st.title("🔢 CPC计算器")
st.markdown("**基于SIF关键词转化率的综合CPC计算工具**")

# ==================== 计算和显示函数 ====================
def calculate_and_display(keywords_list):
    """计算并显示CPC结果"""
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
            value=f"${comprehensive_rec_cpc:.2f}"
        )
    
    with col2:
        st.metric(
            label="基于最高CPC的综合CPC",
            value=f"${comprehensive_max_cpc:.2f}"
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

# 创建选项卡
tab1, tab2 = st.tabs(["📝 手动输入", "📁 文件上传"])

# ==================== 手动输入板块 ====================
with tab1:
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
    if st.button("📊 计算综合CPC", type="primary", use_container_width=True, key="manual_calc"):
        if len(keywords_list) == 0:
            st.error("❌ 请至少输入一个关键词的完整信息！")
        else:
            calculate_and_display(keywords_list)

# ==================== 文件上传板块 ====================
with tab2:
    st.markdown("### 📂 上传Excel文件")
    st.info("💡 提示：表头可以不在第一行，程序会自动识别")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 文件1：关键词和排名")
        st.markdown("需要包含的列：")
        st.markdown("- 关键词列")
        st.markdown("- 周搜索排名列（对应ABA Rank）")
        
        file1 = st.file_uploader(
            "上传关键词文件", 
            type=['xlsx', 'xls'],
            key="file1"
        )
        
        if file1:
            st.success("✅ 文件1已上传")
    
    with col2:
        st.markdown("#### 文件2：竞价数据")
        st.markdown("需要包含的列：")
        st.markdown("- 关键词列（用于匹配文件1）")
        st.markdown("- 建议竞价-推荐列（对应推荐CPC）")
        st.markdown("- 建议竞价-最高列（对应最高CPC）")
        
        file2 = st.file_uploader(
            "上传竞价文件", 
            type=['xlsx', 'xls'],
            key="file2"
        )
        
        if file2:
            st.success("✅ 文件2已上传")
    
    st.markdown("---")
    
    if file1 and file2:
        try:
            # ========== 处理文件1 ==========
            st.markdown("### 📋 文件1预览（前10行）")
            df1_raw = pd.read_excel(file1, header=None)
            st.dataframe(df1_raw.head(10), use_container_width=True)
            
            # 让用户选择文件1的表头行和列
            st.markdown("#### 🔧 文件1配置")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                header_row_1 = st.number_input(
                    "文件1表头所在行（从0开始）",
                    min_value=0,
                    max_value=len(df1_raw)-1,
                    value=0,
                    key="header1"
                )
            
            # 重新读取文件1，指定表头行
            df1 = pd.read_excel(file1, header=header_row_1)
            
            with col2:
                keyword_col = st.selectbox(
                    "选择关键词列",
                    options=df1.columns.tolist(),
                    key="keyword_col"
                )
            
            with col3:
                rank_col = st.selectbox(
                    "选择周搜索排名列",
                    options=df1.columns.tolist(),
                    key="rank_col"
                )
            
            st.markdown("---")
            
            # ========== 处理文件2 ==========
            st.markdown("### 📋 文件2预览（前10行）")
            df2_raw = pd.read_excel(file2, header=None)
            st.dataframe(df2_raw.head(10), use_container_width=True)
            
            # 让用户选择文件2的表头行和列
            st.markdown("#### 🔧 文件2配置")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                header_row_2 = st.number_input(
                    "文件2表头所在行（从0开始）",
                    min_value=0,
                    max_value=len(df2_raw)-1,
                    value=0,
                    key="header2"
                )
            
            # 重新读取文件2，指定表头行
            df2 = pd.read_excel(file2, header=header_row_2)
            
            with col2:
                keyword_col_2 = st.selectbox(
                    "选择关键词列",
                    options=df2.columns.tolist(),
                    key="keyword_col_2"
                )
            
            with col3:
                rec_cpc_col = st.selectbox(
                    "选择建议竞价-推荐列",
                    options=df2.columns.tolist(),
                    key="rec_cpc_col"
                )
            
            with col4:
                max_cpc_col = st.selectbox(
                    "选择建议竞价-最高列",
                    options=df2.columns.tolist(),
                    key="max_cpc_col"
                )
            
            st.markdown("---")
            
            # 计算按钮
            if st.button("📊 处理文件并计算", type="primary", use_container_width=True, key="file_calc"):
                try:
                    # 提取所需数据
                    df1_filtered = df1[[keyword_col, rank_col]].copy()
                    df1_filtered.columns = ['keyword', 'aba_rank']
                    
                    df2_filtered = df2[[keyword_col_2, rec_cpc_col, max_cpc_col]].copy()
                    df2_filtered.columns = ['keyword', 'recommended_cpc', 'max_cpc']
                    
                    # 清理数据
                    df1_filtered = df1_filtered.dropna()
                    df2_filtered = df2_filtered.dropna()
                    
                    # 去重处理
                    df1_filtered = df1_filtered.drop_duplicates(subset='keyword', keep='first')
                    df2_filtered = df2_filtered.drop_duplicates(subset='keyword', keep='first')
                    
                    # 通过关键词列进行内连接（只保留两个文件都有的关键词）
                    merged_df = pd.merge(df1_filtered, df2_filtered, on='keyword', how='inner')
                    
                    if len(merged_df) == 0:
                        st.error("❌ 两个文件没有匹配的关键词！请检查关键词列是否正确。")
                    else:
                        # 显示匹配信息
                        st.info(f"📊 文件1共 {len(df1_filtered)} 个关键词，文件2共 {len(df2_filtered)} 个关键词，成功匹配 {len(merged_df)} 个关键词")
                        
                        # 转换数据类型
                        merged_df['aba_rank'] = pd.to_numeric(merged_df['aba_rank'], errors='coerce')
                        merged_df['recommended_cpc'] = pd.to_numeric(merged_df['recommended_cpc'], errors='coerce')
                        merged_df['max_cpc'] = pd.to_numeric(merged_df['max_cpc'], errors='coerce')
                        
                        # 移除无效数据
                        merged_df = merged_df.dropna()
                        merged_df = merged_df[merged_df['aba_rank'] > 0]
                        
                        if len(merged_df) == 0:
                            st.error("❌ 没有有效的数据可以计算！请检查数值列是否包含有效数字。")
                        else:
                            # 显示合并后的数据预览
                            st.markdown("### 📊 匹配成功的数据预览")
                            st.dataframe(merged_df.head(20), use_container_width=True)
                            st.success(f"✅ 共 {len(merged_df)} 条有效数据用于计算")
                            
                            # 转换为列表格式进行计算
                            keywords_list = merged_df.to_dict('records')
                            calculate_and_display(keywords_list)
                
                except Exception as e:
                    st.error(f"❌ 数据处理错误：{str(e)}")
                    st.markdown("请确保：")
                    st.markdown("- 选择了正确的列")
                    st.markdown("- 周搜索排名列包含有效的数字")
                    st.markdown("- 竞价列包含有效的数字")
        
        except Exception as e:
            st.error(f"❌ 文件读取错误：{str(e)}")
            st.markdown("请确保上传的是有效的Excel文件")

# 页面底部说明
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    💡 提示：可以选择手动输入或上传文件来计算综合CPC
</div>
""", unsafe_allow_html=True)
