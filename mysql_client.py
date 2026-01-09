      
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import pandas as pd

MYSQL_CONFIG = {
    'host': 'ow-masterdata-1.cavkqwqmyvuw.us-west-2.rds.amazonaws.com',
    'port': 3306,
    'database': 'ow_base',
    'user': 'ow_base_user',
    'password': '3we@5y_+05iu',
    'charset': 'utf8mb4',
    'autocommit': False,
    'connect_timeout': 30,
    'read_timeout': 60,
    'write_timeout': 60
}
TABLES = {
    'ASIN_goal_philips': 'ods_asin_goal_philips',
    'ods_category': 'ods_category',
    'ods_asin_philips': 'ods_asin_philips',
    'SI_keyword_philips': 'ods_si_keyword_philips',
    'ods_goal_vcp':'ods_goal_vcp',
    'ods_asin_sale_goal':'ods_asin_sale_goal'
}
def get_engine():
    """创建数据库连接"""
    #mysql+pymysql://root:password@localhost:3306/your_database
    password_encoded = quote_plus(MYSQL_CONFIG['password'])
    connection_string = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{password_encoded}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}?charset=utf8mb4"
    return create_engine(connection_string)

# 列名转小写
def to_mysql_data(table_name, upload_mode, df, batch_size=100):
    """优化的分批插入版本"""
    try:
        to_mysql_data_safe(table_name, upload_mode, df)
        return True
    except Exception as e:
        print(f"安全插入失败: {e}")

    engine = get_engine()
    table_name = TABLES[table_name]

    # 将列名转为小写
    df.columns = df.columns.str.lower()

    # 处理替换模式
    if upload_mode == 'replace':
        with engine.begin() as conn:
            try:
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
                # 为每个批次单独设置
                conn.execute(text("SET innodb_lock_wait_timeout = 300"))
                conn.execute(text("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED"))

                batch_df.to_sql(
                    table_name,
                    engine,
                    if_exists='append',
                    index=False,
                    method=None
                )

            inserted += len(batch_df)
            print(f"已插入 {inserted}/{total_rows} 行")

        except Exception as e:
            print(f"插入第{i}-{min(i + batch_size, total_rows) - 1}行时失败: {e}")
            raise

    print(f"数据上传完成，共插入 {total_rows} 行")
    return True


def to_mysql_data_safe(table_name, upload_mode, df):
    """安全的批量插入，避免list of dictionaries错误"""
    engine = get_engine()
    table_name = TABLES[table_name]

    with engine.connect() as conn:
        # 增加锁等待时间
        conn.execute(text("SET innodb_lock_wait_timeout = 300"))

        if upload_mode == 'replace':
            try:
                # 先禁用外键检查
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                conn.execute(text(f"TRUNCATE TABLE {table_name}"))
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                print(f"已清空表: {table_name}")
            except Exception as e:
                print(f"TRUNCATE失败，使用DELETE: {e}")
                conn.rollback()
                conn.execute(text(f"DELETE FROM {table_name}"))

        # 将列名转为小写
        df.columns = df.columns.str.lower()

        # 准备插入SQL
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
                print(f"❌ 批次插入失败: {e}")
                # 尝试单行插入
                for row_data in batch_data:
                    try:
                        with conn.connection.cursor() as cursor:
                            cursor.execute(sql, row_data)
                            conn.connection.commit()
                    except Exception as single_error:
                        print(f"单行插入失败: {single_error}")
                        continue

    print(f"🎉 数据上传完成，共插入 {total_rows} 行")
    return True

    
