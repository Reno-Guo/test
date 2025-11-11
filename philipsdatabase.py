import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import io
import pytz

# ==================== 配置常量 ====================
BRAND_COLOR = "#00a6e4"
SECONDARY_COLOR = "#0088c7"
SUCCESS_COLOR = "#00c853"
WARNING_COLOR = "#ff9800"
ERROR_COLOR = "#f44336"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库配置
DB_CONFIG = {
    'username': 'haiyi',
    'password': 'G7f@2eBw',
    'host': '47.109.55.96',
    'port': 8124,
    'database': 'semanticdb_haiyi'
}

# 邮件配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.feishu.cn',
    'smtp_port': 465,
    'sender_email': 'idc_ow@oceanwing.com',
    'sender_password': 'OkTIL1AxudQ2y2tC',
    'log_recipient': 'reno.guo@oceanwing.com',
    'cc_recipients': ['yana.cao@oceanwing.com']
}

# 表配置
TABLES = {
    'ASIN_goal_philips': {'name': 'ASIN 目标数据', 'icon': '🎯', 'color': '#FF6B6B'},
    'ods_category': {'name': '类目数据', 'icon': '📁', 'color': '#4ECDC4'},
    'ods_asin_philips': {'name': 'ASIN 基础数据', 'icon': '📊', 'color': '#45B7D1'},
    'SI_keyword_philips': {'name': 'SI 关键词数据', 'icon': '🔑', 'color': '#96CEB4'},
    'ods_goal_vcp': {'name': 'VCP 目标数据', 'icon': '📈', 'color': '#FFEAA7'}
}

# ==================== 自定义样式 ====================
def apply_custom_styles():
    st.markdown(f"""
    <style>
        /* 全局样式 */
        .stApp {{
            background: linear-gradient(135deg, #f5f7fa 0%, #e8f0f8 100%);
        }}
        
        /* 主标题 */
        .main-title {{
            color: {BRAND_COLOR};
            font-size: 2.2rem;
            font-weight: 700;
            text-align: center;
            padding: 1rem 0 0.3rem 0;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        
        .main-subtitle {{
            text-align: center;
            color: #666;
            font-size: 0.95rem;
            margin: 0 0 1.5rem 0;
            font-weight: 400;
        }}
        
        /* 主容器 - 紧凑布局 */
        .main-container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 0 1rem;
        }}
        
        /* 分组标题 - 更轻量 */
        .section-title {{
            color: {BRAND_COLOR};
            font-size: 1.3rem;
            font-weight: 600;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid {BRAND_COLOR};
            display: flex;
            align-items: center;
        }}
        
        .section-title .icon {{
            margin-right: 0.5rem;
            font-size: 1.5rem;
        }}
        
        /* 轻量分割线 */
        .divider {{
            height: 1px;
            background: linear-gradient(90deg, transparent, #e0e0e0, transparent);
            margin: 2rem 0;
        }}
        
        .divider-thick {{
            height: 2px;
            background: linear-gradient(90deg, transparent, {BRAND_COLOR}, transparent);
            margin: 2.5rem 0;
            opacity: 0.3;
        }}
        
        /* 表选择卡片 - 突出显示 */
        .table-selector-container {{
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 8px 24px rgba(0,166,228,0.15);
            margin-bottom: 2rem;
            border: 2px solid {BRAND_COLOR};
        }}
        
        .table-card {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 0.5rem;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid #e0e0e0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        
        .table-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,166,228,0.2);
            border-color: {BRAND_COLOR};
        }}
        
        .table-card-selected {{
            border-color: {BRAND_COLOR};
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            box-shadow: 0 4px 16px rgba(0,166,228,0.3);
        }}
        
        .table-icon {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            display: block;
        }}
        
        .table-name {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 0.3rem;
        }}
        
        .table-key {{
            font-size: 0.85rem;
            color: #666;
            font-family: 'Courier New', monospace;
            background: #f5f5f5;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }}
        
        /* 验证码卡片 - 保留强调 */
        .auth-card {{
            background: white;
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
            margin: 2rem auto;
            max-width: 500px;
            border-top: 4px solid {BRAND_COLOR};
        }}
        
        /* 备份下载卡片 - 保留强调 */
        .backup-card {{
            background: linear-gradient(135deg, #fff5e6 0%, #ffe8cc 100%);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            border: 2px solid {WARNING_COLOR};
            box-shadow: 0 4px 12px rgba(255,152,0,0.2);
        }}
        
        /* 按钮样式 */
        .stButton > button {{
            background: linear-gradient(135deg, {BRAND_COLOR} 0%, {SECONDARY_COLOR} 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s;
            box-shadow: 0 2px 8px rgba(0,166,228,0.3);
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,166,228,0.5);
        }}
        
        .stDownloadButton > button {{
            background: white;
            color: {BRAND_COLOR};
            border: 2px solid {BRAND_COLOR};
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        
        .stDownloadButton > button:hover {{
            background: {BRAND_COLOR};
            color: white;
        }}
        
        /* 输入框样式 */
        .stTextInput > div > div > input {{
            border-radius: 8px;
            border: 2px solid #e0e0e0;
            transition: all 0.3s;
            padding: 0.75rem;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: {BRAND_COLOR};
            box-shadow: 0 0 0 3px rgba(0,166,228,0.1);
        }}
        
        /* 文件上传器 */
        .uploadedFile {{
            border: 2px dashed {BRAND_COLOR};
            border-radius: 8px;
            background: #f8fcff;
        }}
        
        /* 选择框 */
        .stSelectbox > div > div {{
            border-radius: 8px;
        }}
        
        /* Radio按钮 */
        .stRadio > div {{
            background: transparent;
            padding: 0;
        }}
        
        .stRadio > div > label {{
            background: white;
            padding: 0.8rem 1.2rem;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
            margin: 0.3rem 0;
            transition: all 0.3s;
        }}
        
        .stRadio > div > label:hover {{
            border-color: {BRAND_COLOR};
            background: #f0f9ff;
        }}
        
        /* 信息框优化 */
        .stAlert {{
            border-radius: 8px;
            border-left: 4px solid {BRAND_COLOR};
        }}
        
        /* 使用说明区域 */
        .info-box {{
            background: #f8f9fa;
            border-left: 4px solid {BRAND_COLOR};
            border-radius: 4px;
            padding: 1rem 1.5rem;
            margin: 1.5rem 0;
            color: #666;
            font-size: 0.95rem;
            line-height: 1.8;
        }}
        
        .info-box ul {{
            margin: 0.5rem 0;
            padding-left: 1.5rem;
        }}
        
        .info-box li {{
            margin: 0.3rem 0;
        }}
        
        /* 状态徽章 */
        .badge {{
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 600;
            margin: 0.25rem;
        }}
        
        .badge-success {{
            background: {SUCCESS_COLOR};
            color: white;
        }}
        
        .badge-warning {{
            background: {WARNING_COLOR};
            color: white;
        }}
        
        .badge-info {{
            background: {BRAND_COLOR};
            color: white;
        }}
    </style>
    """, unsafe_allow_html=True)

# ==================== 工具函数 ====================
def init_session_state():
    """统一初始化session_state"""
    defaults = {
        'captcha_verified': False,
        'captcha_code': None,
        'captcha_expiry': None,
        'code_sent': False,
        'backup_generated': False,
        'backup_buffer': None,
        'backup_filename': None,
        'backup_row_msg': '',
        'current_df': None,
        'current_table': None,
        'current_mode': None,
        'current_uploaded_file': None,
        'backup_download_confirmed': False,
        'selected_table': list(TABLES.keys())[0]
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_engine():
    """创建数据库连接"""
    password_encoded = quote_plus(DB_CONFIG['password'])
    connection_string = (
        f"clickhouse://{DB_CONFIG['username']}:{password_encoded}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(connection_string)

def table_exists(engine, table_name, database):
    """检查表是否存在"""
    query = text(
        f"SELECT * FROM system.tables WHERE name = '{table_name}' "
        f"AND database = '{database}' LIMIT 1"
    )
    with engine.connect() as conn:
        result = pd.read_sql(query, conn)
    return not result.empty

def test_insert_permission(engine, table_name):
    """测试INSERT权限"""
    try:
        with engine.connect() as conn:
            test_insert = text(
                f"INSERT INTO {table_name} (Country, SKU, spend_contrbution, "
                f"Profitable_ROAS, Breakeven_ROAS) VALUES "
                f"('PERM_TEST', 'PERM_TEST', 0.0, 0.0, 0.0)"
            )
            conn.execute(test_insert)
            cleanup = text(f"DELETE FROM {table_name} WHERE Country = 'PERM_TEST'")
            conn.execute(cleanup)
            return True
    except Exception:
        return False

def get_table_columns(engine, table_name, database):
    """获取数据库表的列名"""
    try:
        query = text(
            f"SELECT name FROM system.columns WHERE table = '{table_name}' "
            f"AND database = '{database}' ORDER BY position"
        )
        with engine.connect() as conn:
            result = pd.read_sql(query, conn)
        return result['name'].tolist() if not result.empty else []
    except Exception as e:
        st.error(f'获取表结构失败: {str(e)}')
        return []

def clean_data(df):
    """数据清洗"""
    df.columns = [col.strip() for col in df.columns]
    
    numeric_cols = ['spend_contrbution', 'Profitable_ROAS', 'Breakeven_ROAS']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    string_cols = ['Country', 'SKU']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    
    return df

def send_email(to_email, subject, body, cc_emails=None):
    """通用发送邮件函数"""
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = EMAIL_CONFIG['sender_email']
    msg['To'] = to_email
    
    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)
    
    try:
        recipients = [to_email] + (cc_emails or [])
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.sendmail(EMAIL_CONFIG['sender_email'], recipients, msg.as_string())
        return True
    except Exception as e:
        st.error(f'📧 发送邮件失败: {str(e)}')
        return False

def send_email_code(to_email, code):
    """发送验证码邮件"""
    beijing_time = datetime.now(BEIJING_TZ)
    subject = 'semanticdb_haiyi数据库操作程序验证码'
    body = (
        f'您的验证码是: {code}\n'
        f'有效期: 5 分钟\n\n'
        f'发送时间: {beijing_time.strftime("%Y-%m-%d %H:%M:%S")} (北京时间)'
    )
    return send_email(to_email, subject, body)

def generate_code():
    """生成6位数字验证码"""
    return ''.join(random.choices('0123456789', k=6))

# ==================== 导出功能 ====================
def export_columns(table_name):
    """导出空表模板"""
    try:
        engine = get_engine()
        if not table_exists(engine, table_name, DB_CONFIG['database']):
            return None, f'表 {table_name} 不存在。'
        
        query = text(
            f"SELECT name FROM system.columns WHERE table = '{table_name}' "
            f"AND database = '{DB_CONFIG['database']}' ORDER BY position"
        )
        with engine.connect() as conn:
            df_columns = pd.read_sql(query, conn)
        
        if df_columns.empty:
            return None, '未找到列信息。'
        
        column_names = df_columns['name'].tolist()
        empty_df = pd.DataFrame(columns=column_names)
        
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            empty_df.to_excel(writer, index=False)
        output_buffer.seek(0)
        return output_buffer, None
    except Exception as e:
        return None, f'导出失败: {str(e)}\n\n提示:确保安装 openpyxl'

def export_full_table(table_name):
    """下载全表数据"""
    try:
        engine = get_engine()
        if not table_exists(engine, table_name, DB_CONFIG['database']):
            return None, f'表 {table_name} 不存在。'
        
        query = text(f"SELECT * FROM {table_name}")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if df.empty:
            return None, '表为空,无数据导出。'
        
        output_buffer = io.BytesIO()
        df.to_csv(output_buffer, index=False, encoding='utf-8')
        output_buffer.seek(0)
        return output_buffer, None
    except Exception as e:
        return None, f'导出失败: {str(e)}'

def backup_table_before_upload(table_name):
    """自动备份全表"""
    try:
        engine = get_engine()
        if not table_exists(engine, table_name, DB_CONFIG['database']):
            return False, f'表 {table_name} 不存在。'
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f'{table_name}_backup_{timestamp}.csv'
        
        query = text(f"SELECT * FROM {table_name}")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        output_buffer = io.BytesIO()
        df.to_csv(output_buffer, index=False, encoding='utf-8')
        output_buffer.seek(0)
        
        row_count_msg = f",包含 {len(df)} 行数据" if not df.empty else "(表为空)"
        return True, (output_buffer, backup_filename, row_count_msg)
    except Exception as e:
        return False, f'备份失败: {str(e)}'

# ==================== 上传功能 ====================
def perform_upload(table_name, upload_mode, df, uploaded_file, backup_filename):
    """执行上传逻辑"""
    try:
        engine = get_engine()
        
        if not table_exists(engine, table_name, DB_CONFIG['database']):
            return f'表 {table_name} 不存在。请先重建表。'
        
        if not test_insert_permission(engine, table_name):
            grant_sql = f"GRANT INSERT ON {DB_CONFIG['database']}.{table_name} TO {DB_CONFIG['username']};"
            if upload_mode == 'replace':
                grant_sql += f"\nGRANT TRUNCATE ON {DB_CONFIG['database']}.{table_name} TO {DB_CONFIG['username']};"
            return f'权限不足。请联系管理员执行:\n{grant_sql}'
        
        with engine.connect() as conn:
            if upload_mode == 'replace':
                try:
                    conn.execute(text(f"TRUNCATE TABLE {table_name}"))
                    st.info(f"✓ 表 {table_name} 已清空。")
                except Exception as truncate_e:
                    st.warning(f'TRUNCATE 失败: {str(truncate_e)}\n使用 DELETE 清空。')
                    conn.execute(text(f"DELETE FROM {table_name}"))
            
            df.to_sql(table_name, engine, if_exists='append', index=False)
        
        # 发送操作日志邮件
        beijing_time = datetime.now(BEIJING_TZ)
        operation_type = '覆盖 (Replace)' if upload_mode == 'replace' else '续表 (Append)'
        row_count = len(df)
        
        log_subject = 'semanticdb_haiyi数据库上传操作日志'
        log_body = f"""数据库上传操作日志

操作时间: {beijing_time.strftime("%Y-%m-%d %H:%M:%S")} (北京时间)
操作类型: {operation_type}
操作表名: {table_name}
上传文件: {uploaded_file.name}
上传行数: {row_count}
备份文件: {backup_filename}
操作说明: 数据已成功{"清空并" if upload_mode == "replace" else ""}上传到 ClickHouse 数据库。
如有疑问,请联系管理员。"""
        
        if send_email(EMAIL_CONFIG['log_recipient'], log_subject, log_body, 
                     cc_emails=EMAIL_CONFIG['cc_recipients']):
            st.info('📧 操作日志已发送到指定邮箱。')
        else:
            st.warning('⚠️ 上传成功,但日志邮件发送失败。')
        
        return f'成功: 已{operation_type} {row_count} 行数据到表 {table_name}。'
    
    except Exception as e:
        return f'上传失败: {str(e)}\n\n提示:检查权限或重建表后重试。'

def upload_data(table_name, upload_mode, uploaded_file):
    """上传数据主函数"""
    if uploaded_file is None:
        return '请选择文件'
    
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.lower().endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            return '不支持的文件格式。请使用 CSV 或 XLSX。'
        
        df = clean_data(df)
        
        if df.empty:
            return '文件为空或无有效数据'
        
        # 🟢 改为动态获取数据库表结构并验证:
        engine = get_engine()
        db_columns = get_table_columns(engine, table_name, DB_CONFIG['database'])
        
        if not db_columns:
            return f'无法获取表 {table_name} 的结构信息'
        
        # 检查上传文件的列是否都在数据库表中
        file_columns = df.columns.tolist()
        invalid_cols = [col for col in file_columns if col not in db_columns]
        
        if invalid_cols:
            return (
                f'❌ 文件包含数据库表中不存在的列:\n'
                f'无效列: {", ".join(invalid_cols)}\n\n'
                f'数据库表 [{table_name}] 的有效列:\n'
                f'{", ".join(db_columns)}\n\n'
                f'请修改文件,确保所有列名都在数据库表中。'
            )
        
        st.info(f'✅ 表头验证通过! 文件列数: {len(file_columns)}, 数据库列数: {len(db_columns)}')
        
        # 继续原有逻辑...
        st.session_state.current_df = df
        st.session_state.current_table = table_name
        st.session_state.current_mode = upload_mode
        st.session_state.current_uploaded_file = uploaded_file
        
        if not st.session_state.backup_generated:
            success, backup_info = backup_table_before_upload(table_name)
            if not success:
                return backup_info
            
            st.session_state.backup_buffer, st.session_state.backup_filename, st.session_state.backup_row_msg = backup_info
            st.session_state.backup_generated = True
        
        return 'backup_ready'
    
    except Exception as e:
        st.session_state.backup_generated = False
        return f'上传失败: {str(e)}'

# ==================== UI组件 ====================
def render_table_selector():
    """渲染表选择器 - 卡片式"""
    st.markdown('<div class="table-selector-container">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="icon">📊</span>选择数据表</div>', unsafe_allow_html=True)
    
    cols = st.columns(len(TABLES))
    
    for idx, (table_key, table_info) in enumerate(TABLES.items()):
        with cols[idx]:
            is_selected = st.session_state.selected_table == table_key
            card_class = "table-card table-card-selected" if is_selected else "table-card"
            
            if st.button(
                f"{table_info['icon']}\n\n{table_info['name']}\n`{table_key}`",
                key=f"table_{table_key}",
                use_container_width=True
            ):
                st.session_state.selected_table = table_key
                st.rerun()
    
    # 显示当前选择
    selected_info = TABLES[st.session_state.selected_table]
    st.markdown(f"""
    <div style="margin-top: 1rem; padding: 1rem; background: #f0f9ff; border-radius: 8px; text-align: center;">
        <span style="font-size: 1.5rem;">{selected_info['icon']}</span>
        <strong style="color: {BRAND_COLOR}; margin-left: 0.5rem;">当前选择: {selected_info['name']}</strong>
        <code style="margin-left: 0.5rem; background: white; padding: 0.2rem 0.6rem; border-radius: 4px;">{st.session_state.selected_table}</code>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    return st.session_state.selected_table

def render_captcha_ui():
    """渲染验证码界面"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown(f'<div style="text-align: center; margin-bottom: 1.5rem;"><span style="font-size: 3rem;">🔐</span></div>', unsafe_allow_html=True)
        st.markdown(f'<h2 style="text-align: center; color: {BRAND_COLOR}; margin-bottom: 1rem;">邮件验证码验证</h2>', unsafe_allow_html=True)
        
        to_email = EMAIL_CONFIG['log_recipient']
        
        if not st.session_state.code_sent:
            st.info(f'📧 验证码将发送到: **{to_email}**')
            if st.button('📨 发送验证码', use_container_width=True):
                with st.spinner('正在发送验证码...'):
                    code = generate_code()
                    if send_email_code(to_email, code):
                        st.session_state.captcha_code = code
                        st.session_state.captcha_expiry = datetime.now() + timedelta(minutes=5)
                        st.session_state.code_sent = True
                        st.success(f'✅ 验证码已发送到 {to_email}')
                        st.rerun()
        else:
            user_input = st.text_input('🔢 输入验证码:', max_chars=6, 
                                      placeholder='请输入6位数字验证码')
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button('✓ 验证', use_container_width=True):
                    now = datetime.now()
                    if now > st.session_state.captcha_expiry:
                        st.error('⏰ 验证码已过期。请重新发送。')
                        st.session_state.code_sent = False
                        st.session_state.captcha_code = None
                        st.session_state.captcha_expiry = None
                    elif user_input == st.session_state.captcha_code:
                        st.session_state.captcha_verified = True
                        st.success('✅ 验证码正确!')
                        st.balloons()
                        st.rerun()
                    else:
                        st.error('❌ 验证码错误,请重试。')
            
            with col_b:
                if st.button('🔄 重新发送', use_container_width=True):
                    code = generate_code()
                    if send_email_code(to_email, code):
                        st.session_state.captcha_code = code
                        st.session_state.captcha_expiry = datetime.now() + timedelta(minutes=5)
                        st.success('✅ 新验证码已发送。')
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_main_ui():
    """渲染主界面"""
    # 表选择区域
    table_name = render_table_selector()

    with st.expander("📋 查看当前表结构", expanded=False):
        engine = get_engine()
        db_columns = get_table_columns(engine, table_name, DB_CONFIG['database'])
        if db_columns:
            st.info(f"表 **{table_name}** 包含 {len(db_columns)} 个字段:")
            # 分3列显示
            cols = st.columns(3)
            for idx, col in enumerate(db_columns):
                cols[idx % 3].markdown(f"• `{col}`")
        else:
            st.warning("无法获取表结构信息")
    
    # 分割线
    st.markdown('<div class="divider-thick"></div>', unsafe_allow_html=True)
    
    # 导出功能区域
    st.markdown('<div class="section-title"><span class="icon">📥</span>数据导出</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button('📋 导出空表模板', use_container_width=True):
            with st.spinner('正在生成模板...'):
                buffer, error = export_columns(table_name)
                if error:
                    st.error(f'❌ {error}')
                else:
                    st.download_button(
                        label='⬇️ 下载空表模板 (XLSX)',
                        data=buffer,
                        file_name=f'{table_name}_template.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True
                    )
    
    with col2:
        if st.button('📦 下载全表数据', use_container_width=True):
            with st.spinner('正在导出数据...'):
                buffer, error = export_full_table(table_name)
                if error:
                    st.error(f'❌ {error}')
                else:
                    st.download_button(
                        label='⬇️ 下载全表数据 (CSV)',
                        data=buffer,
                        file_name=f'{table_name}_full_data.csv',
                        mime='text/csv',
                        use_container_width=True
                    )
    
    # 分割线
    st.markdown('<div class="divider-thick"></div>', unsafe_allow_html=True)
    
    # 上传功能区域
    st.markdown('<div class="section-title"><span class="icon">📤</span>数据上传</div>', unsafe_allow_html=True)
    
    st.markdown('**步骤 1: 选择上传方式**')
    upload_mode = st.radio(
        '上传方式:',
        ('🔄 覆盖模式 (Replace) - 清空表后上传', '➕ 续表模式 (Append) - 追加到现有数据'),
        horizontal=False,
        label_visibility="collapsed"
    )
    upload_mode = 'replace' if '覆盖' in upload_mode else 'append'
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    st.markdown('**步骤 2: 选择文件**')
    uploaded_file = st.file_uploader(
        '选择 CSV 或 XLSX 文件',
        type=['csv', 'xlsx'],
        help='支持 CSV 和 XLSX 格式的文件',
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        st.success(f'✅ 已选择文件: **{uploaded_file.name}**')
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    st.markdown('**步骤 3: 开始上传**')
    if st.button('🚀 开始上传数据', type='primary', use_container_width=True):
        with st.spinner('正在处理文件...'):
            result = upload_data(table_name, upload_mode, uploaded_file)
            if result == 'backup_ready':
                st.success('✅ 备份已准备好,请下载后继续。')
            elif result and '成功' in result:
                st.success(f'✅ {result}')
                st.balloons()
            elif result:
                st.error(f'❌ {result}')
    
    # 备份下载区域
    if st.session_state.get('backup_generated', False):
        st.markdown('<div class="divider-thick"></div>', unsafe_allow_html=True)
        st.markdown('<div class="backup-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title"><span class="icon">💾</span>备份文件下载</div>', unsafe_allow_html=True)
        
        st.warning(f'⚠️ 备份文件已生成{st.session_state.backup_row_msg}')
        st.info('📌 **重要提示**: 请先下载备份文件,然后勾选确认框,最后点击"继续上传"按钮。')
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.download_button(
                label=f'💾 下载备份文件: {st.session_state.backup_filename}',
                data=st.session_state.backup_buffer,
                file_name=st.session_state.backup_filename,
                mime='text/csv',
                use_container_width=True
            )
        with col2:
            st.markdown('<div style="text-align: center; padding-top: 8px;">', unsafe_allow_html=True)
            st.markdown('<span class="badge badge-warning">必须下载</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.session_state.backup_download_confirmed = st.checkbox(
            '✓ 我已下载备份文件',
            value=st.session_state.backup_download_confirmed
        )
        
        if st.session_state.backup_download_confirmed:
            if st.button('✅ 继续上传', type='primary', use_container_width=True):
                with st.spinner('正在上传数据到数据库...'):
                    result = perform_upload(
                        st.session_state.current_table,
                        st.session_state.current_mode,
                        st.session_state.current_df,
                        st.session_state.current_uploaded_file,
                        st.session_state.backup_filename
                    )
                    
                    # 重置状态
                    st.session_state.backup_generated = False
                    st.session_state.backup_buffer = None
                    st.session_state.backup_filename = None
                    st.session_state.backup_row_msg = ''
                    st.session_state.current_df = None
                    st.session_state.current_table = None
                    st.session_state.current_mode = None
                    st.session_state.current_uploaded_file = None
                    st.session_state.backup_download_confirmed = False
                    
                    if '成功' in result:
                        st.success(f'✅ {result}')
                        st.balloons()
                    else:
                        st.error(f'❌ {result}')
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 分割线
    st.markdown('<div class="divider-thick"></div>', unsafe_allow_html=True)
    
    # 使用说明
    st.markdown('<div class="section-title"><span class="icon">📖</span>使用说明</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    <ul>
        <li><strong>导出空表模板</strong>: 生成包含列名的空 XLSX 文件,方便填写数据</li>
        <li><strong>下载全表数据</strong>: 导出当前表的所有数据为 CSV 文件</li>
        <li><strong>覆盖模式</strong>: 清空表中所有数据后上传新数据</li>
        <li><strong>续表模式</strong>: 将新数据追加到现有数据之后</li>
        <li><strong>备份机制</strong>: 上传前会自动创建备份,必须下载后才能继续</li>
        <li><strong>操作日志</strong>: 每次上传操作都会发送邮件日志到管理员</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# ==================== 主程序 ====================
def main():
    st.set_page_config(
        page_title="Database Manager",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    apply_custom_styles()
    init_session_state()
    
    # 标题
    st.markdown('<h1 class="main-title">📊 Database Manager</h1>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">semanticdb_haiyi 数据库管理系统</p>', unsafe_allow_html=True)
    
    # 轻量分割线
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # 验证码验证
    if not st.session_state.captcha_verified:
        render_captcha_ui()
    else:
        render_main_ui()

if __name__ == '__main__':
    main()
