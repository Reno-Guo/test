import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import io
import pytz
import chardet

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
    'cc_recipient': ['yana.cao@oceanwing.com']
}

# 表配置（移除未使用的icon和color）
TABLES = {
    'ASIN_goal_philips': {'name': 'ASIN 目标数据'},
    'ods_category': {'name': '类目数据'},
    'ods_asin_philips': {'name': 'ASIN 基础数据'},
    'SI_keyword_philips': {'name': 'SI 关键词数据'},
    'ods_goal_vcp': {'name': 'VCP 目标数据'}
}

# ==================== 自定义样式 ====================
def apply_custom_styles():
    st.markdown(f"""
    <style>
        /* 全局样式 */
        .stApp {{
            background: #ffffff;
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
        
        /* 分组标题 */
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
        
        /* 验证码卡片 */
        .auth-card {{
            background: white;
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
            margin: 2rem auto;
            max-width: 500px;
            border-top: 4px solid {BRAND_COLOR};
        }}
        
        /* 备份下载卡片 */
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
    st.session_state.update({k: v for k, v in defaults.items() if k not in st.session_state})

def get_engine():
    """创建数据库连接"""
    password_encoded = quote_plus(DB_CONFIG['password'])
    connection_string = f"clickhouse://{DB_CONFIG['username']}:{password_encoded}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    return create_engine(connection_string)

def table_exists(engine, table_name, database):
    """检查表是否存在"""
    query = text(f"SELECT * FROM system.tables WHERE name = '{table_name}' AND database = '{database}' LIMIT 1")
    with engine.connect() as conn:
        result = pd.read_sql(query, conn)
    return not result.empty

def test_insert_permission(engine, table_name, database):
    """测试INSERT权限 - 动态获取表结构"""
    try:
        query = text(f"SELECT name, type FROM system.columns WHERE table = '{table_name}' AND database = '{database}' ORDER BY position LIMIT 5")
        with engine.connect() as conn:
            columns_info = pd.read_sql(query, conn)
        
        if columns_info.empty:
            return False
        
        test_values = []
        test_columns = []
        cleanup_condition = None
        
        for _, row in columns_info.iterrows():
            col_name = row['name']
            col_type = row['type'].lower()
            test_columns.append(col_name)
            
            if 'int' in col_type or 'float' in col_type or 'decimal' in col_type:
                test_values.append('0')
            elif 'date' in col_type or 'time' in col_type:
                test_values.append("'1970-01-01'")
            else:
                test_values.append("'__PERM_TEST__'")
                if cleanup_condition is None:
                    cleanup_condition = f"{col_name} = '__PERM_TEST__'"
        
        if cleanup_condition is None:
            cleanup_condition = f"{test_columns[0]} = {test_values[0]}"
        
        with engine.connect() as conn:
            insert_sql = text(f"INSERT INTO {table_name} ({', '.join(test_columns)}) VALUES ({', '.join(test_values)})")
            conn.execute(insert_sql)
            cleanup_sql = text(f"DELETE FROM {table_name} WHERE {cleanup_condition}")
            conn.execute(cleanup_sql)
            
        return True
    except Exception:
        return False

def get_table_columns(engine, table_name, database):
    """获取数据库表的列名"""
    try:
        query = text(f"SELECT name FROM system.columns WHERE table = '{table_name}' AND database = '{database}' ORDER BY position")
        with engine.connect() as conn:
            result = pd.read_sql(query, conn)
        return result['name'].tolist() if not result.empty else []
    except Exception as e:
        st.error(f'获取表结构失败: {str(e)}')
        return []

def clean_data(df, table_name=None, database=None):
    """数据清洗 - 根据数据库表结构动态处理"""
    df.columns = [col.strip() for col in df.columns]
    
    if table_name and database:
        try:
            engine = get_engine()
            query = text(f"SELECT name, type FROM system.columns WHERE table = '{table_name}' AND database = '{database}'")
            with engine.connect() as conn:
                columns_info = pd.read_sql(query, conn)
            
            col_type_map = dict(zip(columns_info['name'], columns_info['type']))
            
            for col in df.columns:
                if col not in col_type_map:
                    continue
                
                db_type = col_type_map[col].lower()
                
                if any(t in db_type for t in ['int', 'float', 'decimal', 'double']):
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                elif any(t in db_type for t in ['date', 'datetime', 'timestamp']):
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                elif any(t in db_type for t in ['string', 'char', 'varchar', 'text']):
                    df[col] = df[col].astype(str).str.strip().replace('nan', '')
        except Exception as e:
            st.warning(f'⚠️ 无法获取表结构进行智能清洗,使用基础清洗: {str(e)}')
            df = basic_clean_data(df)
    else:
        df = basic_clean_data(df)
    
    return df

def basic_clean_data(df):
    """基础数据清洗 - 不依赖数据库结构"""
    df.columns = [col.strip() for col in df.columns]
    
    for col in df.columns:
        try:
            numeric_series = pd.to_numeric(df[col], errors='coerce')
            if numeric_series.notna().mean() > 0.5:
                df[col] = numeric_series
            else:
                df[col] = df[col].astype(str).str.strip()
        except:
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
    body = f'您的验证码是: {code}\n有效期: 5 分钟\n\n发送时间: {beijing_time.strftime("%Y-%m-%d %H:%M:%S")} (北京时间)'
    return send_email(to_email, subject, body)

def generate_code():
    """生成6位数字验证码"""
    return ''.join(random.choices('0123456789', k=6))

# ==================== 导出功能 ====================
def export_table(table_name, mode='full', filename=None):
    """通用导出函数：支持全表/备份（CSV）或模板（XLSX）"""
    try:
        engine = get_engine()
        if not table_exists(engine, table_name, DB_CONFIG['database']):
            return None, f'表 {table_name} 不存在。'
        
        if mode == 'columns':
            query = text(f"SELECT name FROM system.columns WHERE table = '{table_name}' AND database = '{DB_CONFIG['database']}' ORDER BY position")
            with engine.connect() as conn:
                df_columns = pd.read_sql(query, conn)
            
            if df_columns.empty:
                return None, '未找到列信息。'
            
            column_names = df_columns['name'].tolist()
            df = pd.DataFrame(columns=column_names)
            output_buffer = io.BytesIO()
            with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            output_buffer.seek(0)
            return output_buffer, f'{table_name}_template.xlsx', None, None
        
        # 全表或备份模式
        query = text(f"SELECT * FROM {table_name}")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if df.empty:
            return None, None, None, '表为空,无数据导出。'
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'{table_name}_backup_{timestamp}.csv' if mode == 'backup' else f'{table_name}_full_data.csv'
        
        output_buffer = io.BytesIO()
        df.to_csv(output_buffer, index=False, encoding='utf-8')
        output_buffer.seek(0)
        
        row_msg = f",包含 {len(df)} 行数据" if not df.empty else "(表为空)"
        return output_buffer, filename, row_msg, None
    except Exception as e:
        return None, None, None, f'导出失败: {str(e)}'

# ==================== 上传功能 ====================
def perform_upload(table_name, upload_mode, df, uploaded_file, backup_filename):
    """执行上传逻辑"""
    try:
        engine = get_engine()
        
        if not table_exists(engine, table_name, DB_CONFIG['database']):
            return f'表 {table_name} 不存在。请先重建表。'
        
        if not test_insert_permission(engine, table_name, DB_CONFIG['database']):
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
        
        if send_email(EMAIL_CONFIG['log_recipient'], log_subject, log_body, EMAIL_CONFIG['cc_recipient']):
            st.info('📧 操作日志已发送到指定邮箱。')
        else:
            st.warning('⚠️ 上传成功,但日志邮件发送失败。')
        
        return f'成功: 已{operation_type} {row_count} 行数据到表 {table_name}。'
    
    except Exception as e:
        return f'上传失败: {str(e)}\n\n提示:检查权限或重建表后重试。'

def read_csv_with_encoding(uploaded_file):
    """使用chardet自动检测编码并读取CSV"""
    uploaded_file.seek(0)
    
    try:
        raw_data = uploaded_file.read(min(100000, uploaded_file.size))
        uploaded_file.seek(0)
        detected = chardet.detect(raw_data)
        encoding = detected['encoding']
        confidence = detected['confidence']
        
        if encoding and confidence > 0.7:
            try:
                df = pd.read_csv(uploaded_file, encoding=encoding, na_values=['', 'NA', 'N/A', 'NULL', 'null', 'None', '#N/A', 'nan', 'NaN'],
                                 keep_default_na=True, skip_blank_lines=True)
                if encoding.lower() in ['utf-8', 'ascii']:
                    st.success(f'✅ 文件编码: **{encoding.upper()}** (置信度: {confidence:.0%})')
                else:
                    st.info(f'ℹ️ 检测到文件编码: **{encoding.upper()}** (置信度: {confidence:.0%}),已自动转换')
                return df
            except Exception as e:
                st.warning(f'⚠️ 使用检测到的编码 {encoding} 读取失败: {str(e)},尝试常用编码...')
        else:
            st.warning(f'⚠️ 编码检测置信度较低({confidence:.0%}),尝试常用编码...')
    except Exception as e:
        st.warning(f'⚠️ 自动检测编码失败: {str(e)},尝试常用编码...')
    
    uploaded_file.seek(0)
    common_encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030', 'big5', 'shift_jis', 'euc_kr', 'iso-8859-1', 'cp1252', 'latin1']
    
    for encoding in common_encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding=encoding, na_values=['', 'NA', 'N/A', 'NULL', 'null', 'None', '#N/A', 'nan', 'NaN'],
                             keep_default_na=True, skip_blank_lines=True)
            if encoding != 'utf-8':
                st.info(f'ℹ️ 使用编码: **{encoding.upper()}**')
            return df
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception:
            continue
    
    st.error("""
    ❌ **无法读取CSV文件**
    
    **可能原因:**
    1. 文件编码格式非常罕见
    2. 文件已损坏
    3. 文件包含二进制数据
    
    **建议操作:**
    1. 用Excel打开文件,另存为 **UTF-8 CSV** 格式
    2. 或使用记事本打开,选择 **另存为** → **编码选择UTF-8**
    3. 确认文件是标准CSV格式（逗号分隔）
    """)
    return None

def upload_data(table_name, upload_mode, uploaded_file):
    """上传数据主函数"""
    if uploaded_file is None:
        return '请选择文件'
    
    original_filename = uploaded_file.name
    file_lower = original_filename.lower()
    st.info(f'📄 正在处理文件: **{original_filename}**')
    
    try:
        df = None
        
        if file_lower.endswith('.csv'):
            st.info('📝 识别为 CSV 文件，正在检测编码...')
            df = read_csv_with_encoding(uploaded_file)
            if df is None:
                return '❌ 无法读取CSV文件\n\n**可能原因:**\n1. 文件编码无法识别\n2. 文件已损坏\n3. 文件格式不正确\n\n**建议操作:**\n- 用Excel打开后另存为 UTF-8 CSV\n- 确认文件是标准CSV格式（逗号分隔）'
        
        elif file_lower.endswith(('.xlsx', '.xls')):
            st.info('📊 识别为 Excel 文件，正在读取...')
            try:
                df = pd.read_excel(uploaded_file)
            except Exception as e:
                return f'❌ 读取Excel文件失败: {str(e)}\n\n请确认文件未损坏，或尝试另存为CSV格式。'
        
        else:
            extension = original_filename.split('.')[-1] if '.' in original_filename else '无扩展名'
            return f'❌ 不支持的文件格式\n\n**文件信息:**\n- 文件名: {original_filename}\n- 扩展名: .{extension}\n\n**支持的格式:**\n- .csv (推荐)\n- .xlsx\n- .xls\n\n请转换文件格式后重新上传。'
        
        if df is None:
            return '❌ 文件读取失败，返回空数据'
        
        if df.empty:
            return '❌ 文件内容为空，没有数据行'
        
        st.success(f'✅ 文件读取成功！数据维度: **{len(df)}** 行 × **{len(df.columns)}** 列')
        
        preview_cols = df.columns.tolist()[:5]
        preview = f'{", ".join(preview_cols)} ... (共{len(df.columns)}列)' if len(df.columns) > 5 else ", ".join(preview_cols)
        st.info(f'📋 列名预览: {preview}')
        
        st.info('🧹 正在清洗数据...')
        df = clean_data(df, table_name, DB_CONFIG['database'])
        
        if df.empty:
            return '❌ 数据清洗后为空，可能所有数据都是无效的'
        
        st.info('🔍 正在验证表结构...')
        engine = get_engine()
        db_columns = get_table_columns(engine, table_name, DB_CONFIG['database'])
        
        if not db_columns:
            return f'❌ 无法获取表 {table_name} 的结构信息\n\n请检查:\n1. 表是否存在\n2. 数据库连接是否正常\n3. 是否有查询权限'
        
        file_columns = df.columns.tolist()
        invalid_cols = [col for col in file_columns if col not in db_columns]
        
        if invalid_cols:
            return f'❌ 表头验证失败\n\n**文件中存在数据库表不包含的列:**\n{", ".join(invalid_cols)}\n\n**数据库表 [{table_name}] 的所有列:**\n{", ".join(db_columns)}\n\n**请执行以下操作之一:**\n1. 删除文件中的无效列\n2. 修改列名使其匹配数据库表\n3. 在数据库中添加缺失的列'
        
        st.success(f'✅ 表头验证通过！文件列: {len(file_columns)} 个 | 数据库列: {len(db_columns)} 个')
        
        st.session_state.current_df = df
        st.session_state.current_table = table_name
        st.session_state.current_mode = upload_mode
        st.session_state.current_uploaded_file = uploaded_file
        
        if not st.session_state.backup_generated:
            st.info('💾 正在生成备份...')
            buffer, filename, row_msg, error = export_table(table_name, mode='backup')
            if error:
                return f'❌ 备份失败: {error}'
            
            st.session_state.backup_buffer = buffer
            st.session_state.backup_filename = filename
            st.session_state.backup_row_msg = row_msg
            st.session_state.backup_generated = True
            st.success('✅ 备份已生成')
        
        return 'backup_ready'
    
    except Exception as e:
        st.session_state.backup_generated = False
        import traceback
        st.error('💥 发生错误')
        with st.expander('🔍 查看详细错误信息', expanded=True):
            st.code(traceback.format_exc())
        return f'❌ 上传失败: {str(e)}\n\n点击上方展开查看详细错误信息'

# ==================== UI组件 ====================
def render_divider(thick=False):
    """复用分割线"""
    cls = "divider-thick" if thick else "divider"
    st.markdown(f'<div class="{cls}"></div>', unsafe_allow_html=True)

def render_table_selector():
    """渲染表选择器"""
    st.markdown('<div class="section-title"><span class="icon">📊</span>选择数据表</div>', unsafe_allow_html=True)
    
    table_options = list(TABLES.keys())
    current_index = table_options.index(st.session_state.selected_table) if st.session_state.selected_table in table_options else 0
    
    selected_table = st.selectbox('选择要操作的数据表:', options=table_options, index=current_index, key='table_selector')
    
    if selected_table != st.session_state.selected_table:
        st.session_state.selected_table = selected_table
        st.rerun()
    
    render_divider()
    return selected_table

def render_captcha_ui():
    """渲染验证码界面"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
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
            user_input = st.text_input('🔢 输入验证码:', max_chars=6, placeholder='请输入6位数字验证码')
            
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
    table_name = render_table_selector()

    with st.expander("📋 查看当前表结构", expanded=False):
        engine = get_engine()
        db_columns = get_table_columns(engine, table_name, DB_CONFIG['database'])
        if db_columns:
            st.info(f"表 **{table_name}** 包含 {len(db_columns)} 个字段:")
            cols = st.columns(3)
            for idx, col in enumerate(db_columns):
                cols[idx % 3].markdown(f"• `{col}`")
        else:
            st.warning("无法获取表结构信息")
    
    render_divider(thick=True)
    
    st.markdown('<div class="section-title"><span class="icon">📥</span>数据导出</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button('📋 导出空表模板', use_container_width=True):
            with st.spinner('正在生成模板...'):
                buffer, filename, _, error = export_table(table_name, mode='columns')
                if error:
                    st.error(f'❌ {error}')
                else:
                    st.download_button(label='⬇️ 下载空表模板 (XLSX)', data=buffer, file_name=filename,
                                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
    
    with col2:
        if st.button('📦 下载全表数据', use_container_width=True):
            with st.spinner('正在导出数据...'):
                buffer, filename, _, error = export_table(table_name, mode='full')
                if error:
                    st.error(f'❌ {error}')
                else:
                    st.download_button(label='⬇️ 下载全表数据 (CSV)', data=buffer, file_name=filename, mime='text/csv', use_container_width=True)
    
    render_divider(thick=True)
    
    st.markdown('<div class="section-title"><span class="icon">📤</span>数据上传</div>', unsafe_allow_html=True)
    
    st.markdown('**步骤 1: 选择上传方式**')
    upload_mode = st.radio('上传方式:', ('🔄 覆盖模式 (Replace) - 清空表后上传', '➕ 续表模式 (Append) - 追加到现有数据'),
                           horizontal=False, label_visibility="collapsed")
    upload_mode = 'replace' if '覆盖' in upload_mode else 'append'
    
    render_divider()
    
    st.markdown('**步骤 2: 选择文件**')
    uploaded_file = st.file_uploader('选择 CSV 或 XLSX 文件', type=['csv', 'xlsx'], help='支持 CSV 和 XLSX 格式的文件', label_visibility="collapsed")
    
    if uploaded_file:
        st.success(f'✅ 已选择文件: **{uploaded_file.name}**')
    
    render_divider()
    
    st.markdown('**步骤 3: 开始上传**')
    if st.button('🚀 开始上传数据', type='primary', use_container_width=True):
        with st.spinner('正在处理文件...'):
            result = upload_data(table_name, upload_mode, uploaded_file)
            if result == 'backup_ready':
                st.success('✅ 备份已准备好,请下载后继续。')
            elif '成功' in result:
                st.success(f'✅ {result}')
                st.balloons()
            else:
                st.error(f'❌ {result}')
    
    if st.session_state.get('backup_generated', False):
        render_divider(thick=True)
        st.markdown('<div class="section-title"><span class="icon">💾</span>备份文件下载</div>', unsafe_allow_html=True)
        
        st.warning(f'⚠️ 备份文件已生成{st.session_state.backup_row_msg}')
        st.info('📌 **重要提示**: 请先下载备份文件,然后勾选确认框,最后点击"继续上传"按钮。')
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.download_button(label=f'💾 下载备份文件: {st.session_state.backup_filename}', data=st.session_state.backup_buffer,
                               file_name=st.session_state.backup_filename, mime='text/csv', use_container_width=True)
        with col2:
            st.markdown('<div style="text-align: center; padding-top: 8px;">', unsafe_allow_html=True)
            st.markdown('<span class="badge badge-warning">必须下载</span>', unsafe_allow_html=True)
        
        st.session_state.backup_download_confirmed = st.checkbox('✓ 我已下载备份文件', value=st.session_state.backup_download_confirmed)
        
        if st.session_state.backup_download_confirmed:
            if st.button('✅ 继续上传', type='primary', use_container_width=True):
                with st.spinner('正在上传数据到数据库...'):
                    result = perform_upload(st.session_state.current_table, st.session_state.current_mode, st.session_state.current_df,
                                            st.session_state.current_uploaded_file, st.session_state.backup_filename)
                    
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
    
    render_divider(thick=True)
    
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
    st.set_page_config(page_title="Database Manager", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
    
    apply_custom_styles()
    init_session_state()
    
    st.markdown('<h1 class="main-title">📊 Database Manager</h1>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">semanticdb_haiyi 数据库管理系统</p>', unsafe_allow_html=True)
    
    render_divider()
    
    if not st.session_state.captcha_verified:
        render_captcha_ui()
    else:
        render_main_ui()

if __name__ == '__main__':
    main()
