      
import psycopg2
from sqlalchemy import create_engine, text, MetaData, Table
from urllib.parse import quote_plus
import pandas as pd

POSTGRES_CONFIG = {
    'host': 'postgre.cluster-cavkqwqmyvuw.us-west-2.rds.amazonaws.com',  # 替换为实际的PostgreSQL主机
    'port': 5432,  # PostgreSQL默认端口
    'database': 'postgres',
    'user': 'owpostgre',
    'password': 'oceanwing-pg02',
    'client_encoding': 'utf8',
    'autocommit': False,
    'connect_timeout': 30
}

TABLES = {
    'ASIN_goal_philips': 'ods_asin_goal_philips',
    'ods_category': 'ods_category',
    'ods_asin_philips': 'ods_asin_philips',
    'SI_keyword_philips': 'ods_si_keyword_philips',
    'ods_goal_vcp': 'ods_goal_vcp',
    'ods_asin_sale_goal': 'ods_asin_sale_goal',
    'ods_date_event': 'ods_date_even',
    'ods_category_dsp': 'ods_category_dsp',
}

def get_engine():
    """创建PostgreSQL数据库连接"""
    password_encoded = quote_plus(POSTGRES_CONFIG['password'])
    connection_string = f"postgresql+psycopg2://{POSTGRES_CONFIG['user']}:{password_encoded}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
    return create_engine(connection_string)

def get_table_columns( table_name, database):
    """获取数据库表的列名"""
    try:
        query = text(f"""SELECT column_name name
FROM information_schema.columns
WHERE table_name = '{table_name}'
ORDER BY ordinal_position """)
        with get_engine().begin() as conn:
            result = pd.read_sql(query, conn)
        return result['name'].tolist() if not result.empty else []
    except Exception as e:
        print(f'获取表结构失败: {str(e)}')
        raise e

def to_postgresql_data(table_name, upload_mode, df, batch_size=1000):
    """优化的分批插入版本 - PostgreSQL适配"""
    # try:
    #     to_mysql_data_safe(table_name, upload_mode, df)
    #     return True
    # except Exception as e:
    #     print(f"安全插入失败: {e}")

    engine = get_engine()
    table_name = TABLES[table_name]

    # 将列名转为小写
    df.columns = df.columns.str.lower()
    if 'ods_date_even' in table_name :
        if 'date' in df.columns:
            df = df.rename(columns={'date': 'date_time'})
    # 处理替换模式 - PostgreSQL使用TRUNCATE或DELETE
    if upload_mode == 'replace':
        with engine.begin() as conn:
            try:
                # PostgreSQL的TRUNCATE语法
                conn.execute(text(f"TRUNCATE TABLE {table_name}"))
                print(f"已清空表 {table_name}")
            except Exception as e:
                print(f"TRUNCATE失败，使用DELETE: {e}")
                conn.rollback()
                conn.execute(text(f"DELETE FROM {table_name}"))

    # 分批插入数据
    total_rows = len(df)
    inserted = 0

    for i in range(0, total_rows, batch_size):
        batch_df = df.iloc[i:i + batch_size]

        try:
            # 每个批次使用独立的事务
            with engine.begin() as conn:
                # PostgreSQL不需要设置innodb_lock_wait_timeout
                # 可以设置语句超时（可选）
                conn.execute(text("SET statement_timeout = 300000"))  # 300秒

                batch_df.to_sql(
                    table_name,
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=5000
                )

            inserted += len(batch_df)
            print(f"已插入 {inserted}/{total_rows} 行")

        except Exception as e:
            print(f"插入第{i}-{min(i + batch_size, total_rows) - 1}行时失败: {e}")
            raise

    print(f"数据上传完成，共插入 {total_rows} 行")
    return True

def to_mysql_data_safe(table_name, upload_mode, df):
    """安全的批量插入 - PostgreSQL适配"""
    engine = get_engine()
    table_name = TABLES[table_name]

    with engine.connect() as conn:
        # PostgreSQL设置语句超时
        conn.execute(text("SET statement_timeout = 300000"))

        if upload_mode == 'replace':
            try:
                # PostgreSQL TRUNCATE不需要禁用外键检查
                conn.execute(text(f"TRUNCATE TABLE {table_name}"))
                print(f"已清空表: {table_name}")
            except Exception as e:
                print(f"TRUNCATE失败，使用DELETE: {e}")
                conn.rollback()
                conn.execute(text(f"DELETE FROM {table_name}"))

        # 将列名转为小写
        df.columns = df.columns.str.lower()

        # 准备插入SQL - 使用PostgreSQL的占位符%s（与MySQL相同）
        columns = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        # 分批插入
        batch_size = 100
        data = [tuple(x) for x in df.itertuples(index=False, name=None)]
        total_rows = len(data)

        for i in range(0, total_rows, batch_size):
            batch_data = data[i:i + batch_size]

            try:
                # 使用executemany批量插入
                with conn.connection.cursor() as cursor:
                    cursor.executemany(sql, batch_data)
                    conn.connection.commit()

                print(f"✅ 已插入 {min(i + batch_size, total_rows)}/{total_rows} 行")

            except Exception as e:
                print(f"❌❌ 批次插入失败: {e}")
                # 尝试单行插入
                for row_data in batch_data:
                    try:
                        with conn.connection.cursor() as cursor:
                            cursor.execute(sql, row_data)
                            conn.connection.commit()
                    except Exception as single_error:
                        print(f"单行插入失败: {single_error}")
                        continue

    print(f"🎉🎉 数据上传完成，共插入 {total_rows} 行")
    return True

    
