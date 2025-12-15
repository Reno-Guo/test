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

# 从主程序导入共享函数
def _read_excel_cached(file_or_path, sheet_name=0, engine=None):
    return pd.read_excel(file_or_path, sheet_name=sheet_name, engine=engine)

def unique_tmp_path(suggest_name: str, default_ext: str = ".xlsx") -> str:
    base, ext = os.path.splitext(suggest_name or f"result{default_ext}")
    ext = ext or default_ext
    return os.path.join("/tmp", f"{base}_{st.session_state.SID}_{uuid4().hex[:8]}{ext}")

def save_df_to_buffer(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
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

class PackFormLabeler:
    def __init__(self):
        """初始化剂型分类和正则表达式模式"""
        self.pack_forms = {
            'Capsule': [
                # 英文
                r'\bcapsule\b', r'\bcapsules\b', r'\bcap\b', r'\bcaps\b',
                r'\bgelcap\b', r'\bgelcaps\b', 
                # 中文
                r'\b胶囊\b', r'\b软胶囊\b', r'\b硬胶囊\b', r'\b肠溶胶囊\b',
                r'\b缓释胶囊\b', r'\b控释胶囊\b'
            ],
            'Tablet': [
                # 英文
                r'\btablet\b',r'\bcaplet\b', r'\btablets\b', r'\btab\b', r'\btabs\b',
                r'\bchewable\b',    r'\bchewables\b', r'\bsublingual\b', r'\benteric\b', r'\bCaplets\b', 
                # 中文
                r'\b片剂\b', r'\b片\b', r'\b咀嚼片\b', r'\b含片\b',
                r'\b舌下片\b', r'\b肠溶片\b', r'\b缓释片\b', r'\b控释片\b'
            ],
            'Powder': [
                # 英文
                r'\bpowder\b', r'\bpowders\b', r'\bpwd\b', r'\bgranule\b',
                r'\bgranules\b', r'\bdrink\b', r'\bdrinks\b',r'\bCrystal\b',
                # 中文
                r'\b粉剂\b', r'\b粉末\b', r'\b冲剂\b', r'\b散剂\b',
                r'\b颗粒剂\b', r'\b冲饮\b', r'\b饮品\b'
            ],
            'Gummy': [
                # 英文
                r'\bgummy\b', r'\bgummies\b',r'\bGummy\b', r'\bGummies\b',
                r'\bcandy\b', r'\bcandies\b', r'\bjelly\b', r'\bjellies\b',
                # 中文
                r'软糖', r'咀嚼糖', r'果冻', r'糖果',
                r'口香糖', r'咀嚼片'
            ],
            'Drop': [
                # 英文
                r'\bdrop\b', r'\bdrops\b', r'\btincture\b', r'\btinctures\b',
                r'\bessence\b', r'\bessences\b', r'\bFL OZs\b',
                r'\bliquid\s*drop\b', r'\bliquid\s*drops\b',
                # 中文
                r'滴剂', r'滴液', r'酊剂', r'精华',
                r'精华液', r'液体滴剂', r'液体滴液'
            ],
            'Softgel': [
                # 英文
                r'\bsoftgel\b', r'\bsoftgels\b', r'\bsoft\s*gel\b',
                r'\bgel\b', r'\bgels\b', r'\bgelatin\b',
                # 中文
                r'软胶囊', r'软胶', r'明胶'
            ],
            'Liquid': [
                # 英文
                r'\bliquid\b', r'\bliquids\b', r'\bsyrup\b', r'\bsyrups\b',
                r'\bsuspension\b', r'\bsuspensions\b', r'\belixir\b',
                r'\bsolution\b', r'\bsolutions\b', r'\bemulsion\b',
                # 中文
                r'液体', r'口服液', r'糖浆', r'混悬液',
                r'溶液', r'乳剂', r'水剂'
            ],
            'Cream': [
                # 英文
                r'\bcream\b', r'\bcreams\b', r'\bointment\b', r'\bointments\b',
                # 中文
                r'乳膏', r'霜剂', r'软膏', r'膏剂'
            ],
            'Spray': [
                # 英文
                r'\bspray\b', r'\bsprays\b', r'\binhaler\b', r'\binhalers\b',
                # 中文
                r'喷雾', r'喷剂', r'吸入器', r'吸入剂'
            ],
            'Lotion': [
                # 英文
                r'\blotion\b', r'\blotions\b',
                # 中文
                r'乳液', r'洗剂'
            ],
            'Patch': [
                # 英文
                r'\bpatch\b', r'\bpatches\b',
                # 中文
                r'贴剂', r'贴片', r'贴膏'
            ],
            'Suppository': [
                # 英文
                r'\bsuppository\b', r'\bsuppositories\b',
                # 中文
                r'栓剂', r'坐药'
            ],
            'Oil': [
                # 英文
                r'\boil\b', r'\boils\b', r'\boils\b',
                r'\bessential\s*oil\b', r'\bessential\s*oils\b',
                r'\bfish\s*oil\b', r'\bomega\s*oil\b',
                r'\bcarrier\s*oil\b', r'\bcarrier\s*oils\b',
                # 中文
                r'油', r'精油', r'鱼油', r'植物油', r'橄榄油',
                r'椰子油', r'亚麻籽油', r'月见草油'
            ]
        }
        
        # 标准化映射表 
        self.standardization_map = {
    # ========================================
    # Capsule 相关
    # ========================================
    'capsule': 'Capsule', 'capsules': 'Capsule',
    'cap': 'Capsule', 'caps': 'Capsule', 'capsu': 'Capsule',
    'gelcaps': 'Capsule', 'gelcap': 'Capsule',
    # 首字母大写
    'Capsule': 'Capsule', 'Capsules': 'Capsule','VegCap': 'Capsule',
    'Cap': 'Capsule', 'Caps': 'Capsule', 'Capsu': 'Capsule',
    'Gelcaps': 'Capsule', 'Gelcap': 'Capsule',
    # 全大写
    'CAPSULE': 'Capsule', 'CAPSULES': 'Capsule',
    'CAP': 'Capsule', 'CAPS': 'Capsule', 'CAPSU': 'Capsule',
    'GELCAPS': 'Capsule', 'GELCAP': 'Capsule',

    # ========================================
    # Tablet 相关（包含 caplet）
    # ========================================
    'tablet': 'Tablet', 'tablets': 'Tablet',
    'tab': 'Tablet', 'tabs': 'Tablet',
    'caplet': 'Tablet', 'caplets': 'Tablet',  # ✅ 正确归类到 Tablet
    'chewable': 'Tablet', 'chewables': 'Tablet',
    'chew': 'Tablet', 'chews': 'Tablet',
    'sublingual': 'Tablet', 'enteric': 'Tablet',
    # 首字母大写
    'Tablet': 'Tablet', 'Tablets': 'Tablet',
    'Tab': 'Tablet', 'Tabs': 'Tablet',
    'Caplet': 'Tablet', 'Caplets': 'Tablet',  # ✅ 首字母大写也归为 Tablet
    'Chewable': 'Tablet', 'Chewables': 'Tablet',
    'Chew': 'Tablet', 'Chews': 'Tablet',
    'Sublingual': 'Tablet', 'Enteric': 'Tablet',
    # 全大写
    'TABLET': 'Tablet', 'TABLETS': 'Tablet',
    'TAB': 'Tablet', 'TABS': 'Tablet',
    'CAPLET': 'Tablet', 'CAPLETS': 'Tablet',  # ✅ 全大写也正确映射
    'CHEWABLE': 'Tablet', 'CHEWABLES': 'Tablet',
    'CHEW': 'Tablet', 'CHEWS': 'Tablet',
    'SUBLINGUAL': 'Tablet', 'ENTERIC': 'Tablet',

    # ========================================
    # Powder 相关
    # ========================================
    'powder': 'Powder', 'powders': 'Powder','Powdered': 'Powder',
    'granule': 'Powder', 'granules': 'Powder',
    'Crystals': 'Powder','Crystal': 'Powder','crystal': 'Powder','crystals': 'Powder',
    'pwd': 'Powder',
    'Powder': 'Powder', 'Powders': 'Powder',
    'Granule': 'Powder', 'Granules': 'Powder',
    'Pwd': 'Powder',
    'POWDER': 'Powder', 'POWDERS': 'Powder',
    'GRANULE': 'Powder', 'GRANULES': 'Powder',
    'PWD': 'Powder',

    # ========================================
    # Gummy 相关
    # ========================================
    'gummy': 'Gummy', 'gummies': 'Gummy',
    'jelly': 'Gummy', 'jellies': 'Gummy',
    'gumm': 'Gummy',
    'Gummy': 'Gummy', 'Gummies': 'Gummy',
    'Jelly': 'Gummy', 'Jellies': 'Gummy',
    'Gumm': 'Gummy',
    'GUMMY': 'Gummy', 'GUMMIES': 'Gummy',
    'JELLY': 'Gummy', 'JELLIES': 'Gummy',
    'GUMM': 'Gummy',

    # ========================================
    # Drop 相关
    # ========================================
    'drop': 'Drop', 'drops': 'Drop',
    'tincture': 'Drop', 'tinctures': 'Drop',
    'fl oz': 'Drop', 'fl. oz.': 'Drop',
    'Drop': 'Drop', 'Drops': 'Drop',
    'Tincture': 'Drop', 'Tinctures': 'Drop',
    'Fl Oz': 'Drop', 'Fl. Oz.': 'Drop',
    'DROP': 'Drop', 'DROPS': 'Drop',
    'TINCTURE': 'Drop', 'TINCTURES': 'Drop',
    'FL OZ': 'Drop', 'FL. OZ.': 'Drop',

    # ========================================
    # Softgel 相关
    # ========================================
    'softgel': 'Softgel', 'softgels': 'Softgel','sof': 'Softgel',
    'gel': 'Softgel', 'gels': 'Softgel',
    'Softgel': 'Softgel', 'Softgels': 'Softgel',
    'Gel': 'Softgel', 'Gels': 'Softgel',
    'SOFTGEL': 'Softgel', 'SOFTGELS': 'Softgel',
    'GEL': 'Softgel', 'GELS': 'Softgel',

    # ========================================
    # Liquid 相关
    # ========================================
    'liquid': 'Liquid', 'liquids': 'Liquid',
    'syrup': 'Liquid', 'syrups': 'Liquid',
    'solution': 'Liquid', 'solutions': 'Liquid',
    'suspension': 'Liquid', 'suspensions': 'Liquid',
    'Liquid': 'Liquid', 'Liquids': 'Liquid',
    'Syrup': 'Liquid', 'Syrups': 'Liquid',
    'Solution': 'Liquid', 'Solutions': 'Liquid',
    'Suspension': 'Liquid', 'Suspensions': 'Liquid',
    'LIQUID': 'Liquid', 'LIQUIDS': 'Liquid',
    'SYRUP': 'Liquid', 'SYRUPS': 'Liquid',
    'SOLUTION': 'Liquid', 'SOLUTIONS': 'Liquid',
    'SUSPENSION': 'Liquid', 'SUSPENSIONS': 'Liquid',

    # ========================================
    # Cream 相关
    # ========================================
    'cream': 'Cream', 'creams': 'Cream',
    'ointment': 'Cream', 'ointments': 'Cream',
    'Cream': 'Cream', 'Creams': 'Cream',
    'Ointment': 'Cream', 'Ointments': 'Cream',
    'CREAM': 'Cream', 'CREAMS': 'Cream',
    'OINTMENT': 'Cream', 'OINTMENTS': 'Cream',

    # ========================================
    # Spray 相关
    # ========================================
    'spray': 'Spray', 'sprays': 'Spray',
    'inhaler': 'Spray', 'inhalers': 'Spray',
    'Spray': 'Spray', 'Sprays': 'Spray',
    'Inhaler': 'Spray', 'Inhalers': 'Spray',
    'SPRAY': 'Spray', 'SPRAYS': 'Spray',
    'INHALER': 'Spray', 'INHALERS': 'Spray',

    # ========================================
    # Lotion 相关
    # ========================================
    'lotion': 'Lotion', 'lotions': 'Lotion',
    'Lotion': 'Lotion', 'Lotions': 'Lotion',
    'LOTION': 'Lotion', 'LOTIONS': 'Lotion',

    # ========================================
    # Patch 相关
    # ========================================
    'patch': 'Patch', 'patches': 'Patch',
    'Patch': 'Patch', 'Patches': 'Patch',
    'PATCH': 'Patch', 'PATCHES': 'Patch',

    # ========================================
    # Suppository 相关
    # ========================================
    'suppository': 'Suppository', 'suppositories': 'Suppository',
    'Suppository': 'Suppository', 'Suppositories': 'Suppository',
    'SUPPOSITORY': 'Suppository', 'SUPPOSITORIES': 'Suppository',

    # ========================================
    # Oil 相关
    # ========================================
    'oil': 'Oil', 'oils': 'Oil',
    'essential oil': 'Oil', 'essential oils': 'Oil',
    'fish oil': 'Oil', 'omega oil': 'Oil',
    'carrier oil': 'Oil', 'carrier oils': 'Oil',
    'Oil': 'Oil', 'Oils': 'Oil',
    'Carrier Oil': 'Oil', 'Carrier Oils': 'Oil',
    'OIL': 'Oil', 'OILS': 'Oil',
    'CARRIER OIL': 'Oil', 'CARRIER OILS': 'Oil',

    # ========================================
    # Others 相关
    # ========================================
    'bag': 'Others', 'bags': 'Others','Tea bags': 'Others',
    'teabag': 'Others', 'teabags': 'Others',
    'strip': 'Others', 'strips': 'Others',
    'stick': 'Others', 'sticks': 'Others',
    'other': 'Others', 'others': 'Others',
    'strippy': 'Others',
    # 首字母大写
    'Bag': 'Others', 'Bags': 'Others',
    'Teabag': 'Others', 'Teabags': 'Others',
    'Strip': 'Others', 'Strips': 'Others',
    'Stick': 'Others', 'Sticks': 'Others',
    'Other': 'Others', 'Others': 'Others',
    'Strippy': 'Others',
    # 全大写
    'BAG': 'Others', 'BAGS': 'Others',
    'TEABAG': 'Others', 'TEABAGS': 'Others',
    'STRIP': 'Others', 'STRIPS': 'Others',
    'STICK': 'Others', 'STICKS': 'Others',
    'OTHER': 'Others', 'OTHERS': 'Others',
    'STRIPPY': 'Others',
    }
    
    def detect_others_forms(self, product_text):
        """
        检测Others类剂型
        
        Args:
            product_text (str): 产品描述文本
            
        Returns:
            list: 检测到的Others类剂型列表
        """
        if pd.isna(product_text) or not isinstance(product_text, str):
            return []
        
        others_patterns = {
            'Injection': [r'\binjection\b', r'\binjections\b', r'注射剂', r'针剂'],
            'Nasal': [r'\bnasal\b', r'鼻用', r'鼻腔'],
            'Topical': [r'\btopical\b', r'外用', r'局部'],
            'External': [r'\bexternal\b', r'外用', r'外部'],
            'Bag': [r'\bbag\b', r'\bbags\b', r'袋装', r'包装'],
            'Teabag': [r'\bteabag\b', r'\bteabags\b', r'茶包', r'袋泡茶'],
            'Strip': [r'\bstrip\b', r'\bstrips\b', r'条装', r'条剂'],
            'Stick': [r'\bstick\b', r'\bsticks\b', r'棒状', r'棒剂']
        }
        
        detected_others = []
        text_lower = product_text.lower()
        
        for form, patterns in others_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    detected_others.append(form)
                    break
        
        return detected_others

    def standardize_pack_form(self, pack_form):
        """
        标准化剂型名称
        
        Args:
            pack_form (str): 原始剂型名称
            
        Returns:
            str: 标准化后的剂型名称
        """
        if pd.isna(pack_form) or pack_form == '':
            return pack_form
        
        # 转换为字符串
        pack_form_str = str(pack_form).strip()
        
        # 检查是否已经在标准映射表中
        if pack_form_str in self.standardization_map:
            return self.standardization_map[pack_form_str]
        
        # 检查是否匹配正则表达式模式
        for standard_form, patterns in self.pack_forms.items():
            for pattern in patterns:
                if re.search(pattern, pack_form_str, re.IGNORECASE):
                    return standard_form
        
        # 如果没有匹配到，返回原值
        return pack_form_str
    
    def detect_pack_form(self, product_text):
        """
        从产品描述中检测剂型
        
        Args:
            product_text (str): 产品描述文本
            
        Returns:
            tuple: (检测到的剂型列表, 匹配的文本列表)
        """
        if pd.isna(product_text) or not isinstance(product_text, str):
            return [], []
        
        detected_forms = []
        matched_texts = []
        
        # 转换为小写进行匹配
        text_lower = product_text.lower()
        
        # 检查主要剂型
        for form, patterns in self.pack_forms.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    detected_forms.append(form)
                    matched_texts.extend(matches)
        
        # 检查Others类剂型
        others_forms = self.detect_others_forms(product_text)
        if others_forms:
            detected_forms.append('Others')
            matched_texts.extend(others_forms)
        
        return detected_forms, matched_texts
    
    def classify_pack_form(self, detected_forms):
        """
        根据检测到的剂型进行分类
        
        Args:
            detected_forms (list): 检测到的剂型列表
            
        Returns:
            str: 分类结果
        """
        if not detected_forms:
            return 'Others'
        
        # 去重
        unique_forms = list(set(detected_forms))
        
        # 特殊处理：如果同时检测到Liquid和Drop，优先归类为Drop
        if 'Liquid' in unique_forms and 'Drop' in unique_forms:
            return 'Drop'
        
        if len(unique_forms) == 1:
            return unique_forms[0]
        elif len(unique_forms) > 1:
            return 'Bundle'
        else:
            return 'Others'
    
    def process_dataframe(self, df):
        """
        处理DataFrame，对Pack form列进行智能打标和标准化
        
        Args:
            df (pd.DataFrame): 包含'Pack form'和'Product'列的DataFrame
            
        Returns:
            pd.DataFrame: 处理后的DataFrame
        """
        # 复制DataFrame避免修改原始数据
        df_processed = df.copy()
        
        # 添加新列
        df_processed['Matched_Pack_Form'] = ''
        df_processed['Match_Source'] = ''
        df_processed['Is_Originally_Empty'] = df_processed['Pack form'].isna()
        df_processed['Confidence_Score'] = 0.0
        df_processed['Standardization_Applied'] = False
        
        # 第一步：标准化已存在的剂型
        standardization_count = 0
        for idx, row in df_processed.iterrows():
            if pd.notna(row['Pack form']) and row['Pack form'] != '':
                original_form = row['Pack form']
                standardized_form = self.standardize_pack_form(original_form)
                
                if standardized_form != original_form:
                    df_processed.at[idx, 'Pack form'] = standardized_form
                    df_processed.at[idx, 'Standardization_Applied'] = True
                    standardization_count += 1
        
        # 第二步：处理空的Pack form列
        processed_count = 0
        for idx, row in df_processed.iterrows():
            # 只处理Pack form为空的行
            if pd.isna(row['Pack form']) or row['Pack form'] == '':
                product_text = row['Product']
                detected_forms, matched_texts = self.detect_pack_form(product_text)
                
                if detected_forms:
                    classified_form = self.classify_pack_form(detected_forms)
                    
                    # 实际填充到Pack form列
                    df_processed.at[idx, 'Pack form'] = classified_form
                    
                    # 同时保存到新列
                    df_processed.at[idx, 'Matched_Pack_Form'] = classified_form
                    df_processed.at[idx, 'Match_Source'] = ', '.join(matched_texts)
                    
                    # 计算置信度分数
                    confidence = min(len(detected_forms) / 2.0, 1.0)
                    df_processed.at[idx, 'Confidence_Score'] = confidence
                    
                    processed_count += 1
        
        return df_processed, processed_count, standardization_count
    
    def generate_standardization_report(self, df_processed):
        """
        生成标准化处理报告
        
        Args:
            df_processed (pd.DataFrame): 处理后的DataFrame
            
        Returns:
            dict: 标准化报告
        """
        report = {
            'total_rows': len(df_processed),
            'standardization_applied': df_processed['Standardization_Applied'].sum(),
            'originally_empty': df_processed['Is_Originally_Empty'].sum(),
            'successfully_filled': 0,
            'final_empty': 0,
            'pack_form_distribution': {},
            'standardization_examples': []
        }
        
        # 计算填充统计
        report['successfully_filled'] = report['originally_empty'] - df_processed['Pack form'].isna().sum()
        report['final_empty'] = df_processed['Pack form'].isna().sum()
        
        # 剂型分布
        pack_form_counts = df_processed['Pack form'].value_counts()
        report['pack_form_distribution'] = pack_form_counts.to_dict()
        
        # 标准化示例
        standardized_rows = df_processed[df_processed['Standardization_Applied'] == True]
        if len(standardized_rows) > 0:
            for idx, row in standardized_rows.head(10).iterrows():
                report['standardization_examples'].append({
                    'row': idx + 1,
                    'product': str(row['Product'])[:80] + "..." if len(str(row['Product'])) > 80 else str(row['Product']),
                    'pack_form': row['Pack form']
                })
        
        return report

def pack_form_labeler_app():
    render_app_header("🏷️ 剂型打标工具", "通过匹配产品标题，自动识别剂型并填充到空的Pack form列中")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "选择您的Excel文件 (.xlsx格式)",
            type=["xlsx"],
            key="pack_form_file"
        )
    with col2:
        save_filename = st.text_input("输出文件名", "labeled_pack_forms.xlsx", key="pack_form_save")
    st.divider()
    if uploaded_file is not None:
        try:
            df_input = _read_excel_cached(uploaded_file)
            st.markdown("#### 文件信息")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总行数", len(df_input))
            with col2:
                st.metric("总列数", len(df_input.columns))
            with col3:
                empty_count = df_input['Pack form'].isna().sum() if 'Pack form' in df_input.columns else 0
                st.metric("Pack form空值", empty_count)
            required_columns = ['Pack form', 'Product']
            missing_columns = [col for col in required_columns if col not in df_input.columns]
            if missing_columns:
                st.error(f"文件缺少必要的列: {missing_columns}")
            else:
                st.success("文件格式正确，包含所有必要的列")
                st.markdown("#### 数据预览 (前5行)")
                st.dataframe(df_input.head(), use_container_width=True)
                st.divider()
                execute_btn = st.button("🚀 开始剂型打标", key="pack_form_button", use_container_width=True)
                if execute_btn:
                    with st.spinner("🔄 正在进行剂型智能打标，请稍候..."):
                        try:
                            labeler = PackFormLabeler()
                            df_processed, processed_count, standardization_count = labeler.process_dataframe(df_input)
                            st.success("剂型打标完成！")
                            original_empty_count = (df_input['Pack form'].isna() | (df_input['Pack form'] == '')).sum()
                            final_empty_count = (df_processed['Pack form'].isna() | (df_processed['Pack form'] == '')).sum()
                            successfully_filled_count = original_empty_count - final_empty_count
                            col1, col2, col3, col4, col5 = st.columns(5)
                            with col1:
                                st.metric("原始空值", original_empty_count)
                            with col2:
                                st.metric("成功填充", successfully_filled_count)
                            with col3:
                                st.metric("标准化处理", standardization_count)
                            with col4:
                                st.metric("处理后空值", final_empty_count)
                            with col5:
                                if original_empty_count > 0:
                                    success_rate = successfully_filled_count / original_empty_count * 100
                                    st.metric("成功率", f"{success_rate:.1f}%")
                                else:
                                    st.metric("成功率", "N/A")
                            if standardization_count > 0:
                                st.markdown("#### 标准化处理详情")
                                st.info(f"对 {standardization_count} 行已有剂型进行了标准化处理")
                            st.markdown("#### 剂型分布")
                            pack_form_counts = df_processed['Pack form'].value_counts()
                            st.bar_chart(pack_form_counts)
                            st.markdown("#### 处理结果预览 (前5行)")
                            st.dataframe(df_processed.head(), use_container_width=True)
                            buffer = save_df_to_buffer(df_processed)
                            ts = get_timestamp()
                            out_name = f"labeled_{ts}.xlsx"
                            out_path = os.path.join("/tmp", out_name)
                            save_func = lambda: df_processed.to_excel(out_path, index=False, engine="openpyxl")
                            render_download_section(
                                buffer,
                                out_name,
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                "📥 下载打标后的Excel文件",
                                "pack_form",
                                has_save=True,
                                save_func=save_func,
                                save_path=out_path,
                            )
                            st.info("下载的文件包含：原始数据、填充和标准化后的Pack form列，以及新增的匹配信息列")
                        except Exception as e:
                            st.error(f"处理过程中发生错误: {str(e)}")
        except Exception as e:
            st.error(f"读取文件时发生错误: {str(e)}")
