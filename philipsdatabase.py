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

# 北京时区
beijing_tz = pytz.timezone('Asia/Shanghai')

# 数据库连接配置（你的新凭证）
def get_engine():
    username = 'haiyi'
    password = quote_plus('G7f@2eBw')
    host = '47.109.55.96'
    port = 8124
    database = 'semanticdb_haiyi'
    connection_string = f'clickhouse://{username}:{password}@{host}:{port}/{database}'
    return create_engine(connection_string)

# 检查表是否存在
def table_exists(engine, table_name, database):
    check_query = text(f"SELECT * FROM system.tables WHERE name = '{table_name}' AND database = '{database}' LIMIT 1")
    with engine.connect() as conn:
        result = pd.read_sql(check_query, conn)
    return not result.empty

# 测试 INSERT 权限
def test_insert_permission(engine, table_name):
    try:
        with engine.connect() as conn:
            test_insert = text(
                f"INSERT INTO {table_name} (Country, SKU, spend_contrbution, Profitable_ROAS, Breakeven_ROAS) VALUES ('PERM_TEST', 'PERM_TEST', 0.0, 0.0, 0.0)")
            conn.execute(test_insert)
            cleanup = text(f"DELETE FROM {table_name} WHERE Country = 'PERM_TEST'")
            conn.execute(cleanup)
            return True
    except Exception:
        return False

# 导出空表模板（生成只有表头的空 XLSX）
def export_columns(table_name):
    try:
        engine = get_engine()
        if not table_exists(engine, table_name, 'semanticdb_haiyi'):
            return None, f'表 {table_name} 不存在。'

        # 查询表列（使用 system.columns）
        query = text(
            f"SELECT name FROM system.columns WHERE table = '{table_name}' AND database = 'semanticdb_haiyi' ORDER BY position")
        with engine.connect() as conn:
            df_columns = pd.read_sql(query, conn)

        if df_columns.empty:
            return None, '未找到列信息。'

        # 创建空 DataFrame（只有列名，无行）
        column_names = df_columns['name'].tolist()
        empty_df = pd.DataFrame(columns=column_names)

        # 保存为 XLSX（空表模板，便于编辑）
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            empty_df.to_excel(writer, index=False)
        output_buffer.seek(0)
        return output_buffer, None
    except Exception as e:
        return None, f'导出失败: {str(e)}\n\n提示：确保安装 openpyxl'

# 下载全表
def export_full_table(table_name):
    try:
        engine = get_engine()
        if not table_exists(engine, table_name, 'semanticdb_haiyi'):
            return None, f'表 {table_name} 不存在。'

        query = text(f"SELECT * FROM {table_name}")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)

        if df.empty:
            return None, '表为空，无数据导出。'

        output_buffer = io.BytesIO()
        df.to_csv(output_buffer, index=False, encoding='utf-8')
        output_buffer.seek(0)
        return output_buffer, None
    except Exception as e:
        return None, f'导出失败: {str(e)}'

# 自动备份全表（生成 BytesIO buffer 用于下载，不再保存到本地文件）
def backup_table_before_upload(table_name):
    try:
        engine = get_engine()
        if not table_exists(engine, table_name, 'semanticdb_haiyi'):
            return False, f'表 {table_name} 不存在。'

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f'{table_name}_backup_{timestamp}.csv'

        query = text(f"SELECT * FROM {table_name}")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)

        # 生成 BytesIO buffer（内存中，不保存文件）
        output_buffer = io.BytesIO()
        df.to_csv(output_buffer, index=False, encoding='utf-8')
        output_buffer.seek(0)

        st.success(f"备份已生成，包含 {len(df)} 行数据。请立即下载备份文件以防丢失。" if not df.empty else f"备份已生成（表为空）。请立即下载备份文件。")
        return True, (output_buffer, backup_filename)
    except Exception as e:
        return False, f'备份失败: {str(e)}'

# 数据清洗函数
def clean_data(df):
    df.columns = [col.strip() for col in df.columns]

    if 'spend_contrbution' in df.columns:
        df['spend_contrbution'] = pd.to_numeric(df['spend_contrbution'], errors='coerce')
    if 'Profitable_ROAS' in df.columns:
        df['Profitable_ROAS'] = pd.to_numeric(df['Profitable_ROAS'], errors='coerce')
    if 'Breakeven_ROAS' in df.columns:
        df['Breakeven_ROAS'] = pd.to_numeric(df['Breakeven_ROAS'], errors='coerce')

    if 'Country' in df.columns:
        df['Country'] = df['Country'].astype(str).str.strip()
    if 'SKU' in df.columns:
        df['SKU'] = df['SKU'].astype(str).str.strip()

    return df

# 通用发送邮件函数
def send_email(to_email, subject, body):
    # 配置你的 SMTP 服务器细节（替换为你的实际配置）
    smtp_server = 'smtp.feishu.cn'
    smtp_port = 465
    sender_email = 'reno.guo@oceanwing.com'  # 替换为你的发件人邮箱
    sender_password = 'd7Zezl9LqUXCP5xe'  # 替换为你的应用密码

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = sender_email
    msg['To'] = to_email

    try:
        # 关键修改：使用 SMTP_SSL for 端口 465 (SSL)
        import smtplib  # 确保导入
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f'发送邮件失败: {str(e)}')
        return False

# 发送邮件验证码函数（使用北京时间）
def send_email_code(to_email, code):
    beijing_time = datetime.now(beijing_tz)
    # 邮件内容
    subject = '飞利浦数据库操作程序验证码'
    body = f'您的验证码是: {code}\n有效期: 5 分钟\n\n发送时间: {beijing_time.strftime("%Y-%m-%d %H:%M:%S")} (北京时间)'
    return send_email(to_email, subject, body)

# 生成验证码
def generate_code():
    return ''.join(random.choices('0123456789', k=6))  # 6位数字验证码

# 上传函数（使用 TRUNCATE + APPEND 实现替换）
def upload_data(table_name, upload_mode, uploaded_file):
    if uploaded_file is None:
        return '请选择文件'

    # 读取文件
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

        expected_cols = ['Country', 'SKU', 'spend_contrbution', 'Profitable_ROAS', 'Breakeven_ROAS']
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            return f'文件缺少必要列: {", ".join(missing_cols)}。请确保文件列名为: {", ".join(expected_cols)}'

        engine = get_engine()

        if not table_exists(engine, table_name, 'semanticdb_haiyi'):
            return f'表 {table_name} 不存在。请先重建表。'

        if not test_insert_permission(engine, table_name):
            grant_sql = f"GRANT INSERT ON semanticdb_haiyi.{table_name} TO haiyi;"
            if upload_mode == 'replace':
                grant_sql += "\nGRANT TRUNCATE ON semanticdb_haiyi.{table_name} TO haiyi;"
            return f'权限不足。请联系管理员执行:\n{grant_sql}'

        # 强制备份（返回 buffer 和 filename）
        success, backup_info = backup_table_before_upload(table_name)
        if not success:
            return backup_info

        backup_buffer, backup_filename = backup_info

        # 显示下载按钮（备份生成后立即提供下载）
        st.download_button(
            label=f'立即下载备份文件: {backup_filename}',
            data=backup_buffer,
            file_name=backup_filename,
            mime='text/csv'
        )
        st.info('⚠️ 请立即点击上方按钮下载备份文件！上传操作将继续进行。')

        # 处理上传模式
        with engine.connect() as conn:
            if upload_mode == 'replace':
                # 清空表 + 插入（安全替换）
                try:
                    conn.execute(text(f"TRUNCATE TABLE {table_name}"))
                    st.info(f"表 {table_name} 已清空。")
                except Exception as truncate_e:
                    st.warning(f'TRUNCATE 失败: {str(truncate_e)}\n\n使用 DELETE 清空（可能慢）。')
                    conn.execute(text(f"DELETE FROM {table_name}"))

            # 插入数据
            df.to_sql(table_name, engine, if_exists='append', index=False)

        # 上传成功，发送操作日志邮件
        beijing_time = datetime.now(beijing_tz)
        operation_type = '覆盖 (Replace)' if upload_mode == 'replace' else '续表 (Append)'
        row_count = len(df)
        log_subject = '飞利浦数据库上传操作日志'
        log_body = f"""数据库上传操作日志

操作时间: {beijing_time.strftime("%Y-%m-%d %H:%M:%S")} (北京时间)
操作类型: {operation_type}
操作表名: {table_name}
上传文件: {uploaded_file.name}
上传行数: {row_count}
备份文件: {backup_filename}
操作说明: 数据已成功{"清空并" if upload_mode == "replace" else ""}上传到 ClickHouse 数据库。
如有疑问，请联系管理员。"""

        to_email = 'reno.guo@oceanwing.com'  # 固定日志接收邮箱
        if send_email(to_email, log_subject, log_body):
            st.info('操作日志已发送到指定邮箱。')
        else:
            st.warning('上传成功，但日志邮件发送失败。')

        return f'成功: 已{operation_type} {row_count} 行数据到表 {table_name}。备份文件下载链接已在上方显示。'

    except Exception as e:
        return f'上传失败: {str(e)}\n\n提示：检查权限或重建表后重试。'

# Streamlit 主应用
def main():
    st.title('Data Uploader')

    # 初始化 session_state
    if 'captcha_verified' not in st.session_state:
        st.session_state.captcha_verified = False
        st.session_state.captcha_code = None
        st.session_state.captcha_expiry = None

    if not st.session_state.captcha_verified:
        st.subheader('邮件验证码验证')
        to_email = 'reno.guo@oceanwing.com'  # 固定接收邮箱

        if 'code_sent' not in st.session_state:
            st.session_state.code_sent = False

        if not st.session_state.code_sent:
            if st.button('发送验证码'):
                code = generate_code()
                if send_email_code(to_email, code):
                    st.session_state.captcha_code = code
                    st.session_state.captcha_expiry = datetime.now() + timedelta(minutes=5)
                    st.session_state.code_sent = True
                    st.success(f'验证码已发送到 {to_email}。请检查您的邮箱（包括垃圾邮件）。')
                    st.rerun()
        else:
            user_input = st.text_input('输入验证码:', max_chars=6)
            if st.button('验证'):
                now = datetime.now()
                if now > st.session_state.captcha_expiry:
                    st.error('验证码已过期。请重新发送。')
                    st.session_state.code_sent = False
                    st.session_state.captcha_code = None
                    st.session_state.captcha_expiry = None
                elif user_input == st.session_state.captcha_code:
                    st.session_state.captcha_verified = True
                    st.success('验证码正确！')
                    st.rerun()  # 刷新页面显示主界面
                else:
                    st.error('验证码错误，请重试。')

            if st.button('重新发送验证码'):
                code = generate_code()
                if send_email_code(to_email, code):
                    st.session_state.captcha_code = code
                    st.session_state.captcha_expiry = datetime.now() + timedelta(minutes=5)
                    st.success('新验证码已发送。')
    else:
        # 主界面
        tables = ['ASIN_goal_philips', 'ods_category', 'ods_asin_philips', 'SI_keyword_philips', 'ods_goal_vcp']
        table_name = st.selectbox('选择表:', tables)

        col1, col2 = st.columns(2)
        with col1:
            if st.button('导出空表模板'):
                buffer, error = export_columns(table_name)
                if error:
                    st.error(error)
                else:
                    st.download_button(
                        label='下载空表模板 (XLSX)',
                        data=buffer,
                        file_name=f'{table_name}_template.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
        with col2:
            if st.button('下载全表'):
                buffer, error = export_full_table(table_name)
                if error:
                    st.error(error)
                else:
                    st.download_button(
                        label='下载全表数据 (CSV)',
                        data=buffer,
                        file_name=f'{table_name}_full_data.csv',
                        mime='text/csv'
                    )

        st.subheader('上传数据')
        upload_mode = st.radio('上传方式:', ('覆盖 (Replace)', '续表 (Append)'), horizontal=True)
        upload_mode = 'replace' if upload_mode == '覆盖 (Replace)' else 'append'

        uploaded_file = st.file_uploader('选择 CSV 或 XLSX 文件', type=['csv', 'xlsx'])

        if st.button('上传数据'):
            result = upload_data(table_name, upload_mode, uploaded_file)
            if '成功' in result:
                st.success(result)
            else:
                st.error(result)

        st.info('“导出空表模板”生成 XLSX 文件（只有表头），填写后上传。上传前会自动生成备份并提供下载按钮（内存中生成，便于 Web 端下载）。支持 CSV/XLSX。')

if __name__ == '__main__':
    main()
