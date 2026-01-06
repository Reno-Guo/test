      
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

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
    'ods_goal_vcp':'ods_goal_vcp'
}
def get_engine():
    """创建数据库连接"""
    #mysql+pymysql://root:password@localhost:3306/your_database
    password_encoded = quote_plus(MYSQL_CONFIG['password'])
    connection_string = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{password_encoded}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}?charset=utf8mb4"
    return create_engine(connection_string)

# 列名转小写
def to_mysql_data(table_name, upload_mode, df, batch_size=100):
    """修复后的版本，分批插入避免锁超时"""
    try:
        engine = get_engine()
        table_name = TABLES[table_name]

        with engine.connect() as conn:
            # 设置锁等待超时
            conn.execute(text("SET innodb_lock_wait_timeout = 300"))
            conn.execute(text("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED"))

            if upload_mode == 'replace':
                try:
                    # 使用TRUNCATE替代DELETE（更快且不记录日志）
                    conn.execute(text(f"TRUNCATE TABLE {table_name}"))
                    conn.execute(text("COMMIT"))
                except Exception as e:
                    # 如果TRUNCATE失败（如有外键约束），使用DELETE
                    print(f"TRUNCATE失败，使用DELETE: {e}")
                    conn.rollback()
                    conn.execute(text(f"DELETE FROM {table_name}"))
                    conn.execute(text("COMMIT"))

            # 将列名转为小写
            df.columns = df.columns.str.lower()

            # 分批插入数据
            total_rows = len(df)
            inserted = 0

            for i in range(0, total_rows, batch_size):
                batch_df = df.iloc[i:i + batch_size]

                try:
                    # 使用事务插入每一批
                    with conn.begin():
                        batch_df.to_sql(
                            table_name,
                            conn.engine,
                            if_exists='append',
                            index=False,
                            method=None  # 不使用multi，避免某些问题
                        )
                    inserted += len(batch_df)
                    print(f"已插入 {inserted}/{total_rows} 行")

                except Exception as e:
                    print(f"插入第{i}-{i + batch_size}行时失败: {e}")
                    raise

        print(f"数据上传完成，共插入 {total_rows} 行")
        return True
    except Exception as e:
        to_mysql_data_fixed(table_name, upload_mode, df)
        return False


def to_mysql_data_fixed(table_name, upload_mode, df):
    """使用原生SQL批量插入，避免pandas to_sql的问题"""
    engine = get_engine()
    table_name = TABLES[table_name]

    with engine.connect() as conn:
        # 开始事务
        trans = conn.begin()
        try:
            if upload_mode == 'replace':
                # 先禁用外键检查
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                conn.execute(text(f"TRUNCATE TABLE {table_name}"))
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

            # 将列名转为小写
            df.columns = df.columns.str.lower()

            # 准备插入SQL
            columns = ', '.join(df.columns)
            placeholders = ', '.join(['%s'] * len(df.columns))
            insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

            # 转换为元组列表
            data = [tuple(x) for x in df.to_numpy()]

            # 分批插入
            batch_size = 100
            for i in range(0, len(data), batch_size):
                batch_data = data[i:i + batch_size]
                conn.execute(text(insert_sql), batch_data)
                # 每批提交一次
                trans.commit()
                trans = conn.begin()  # 开始新的事务
                print(f"已插入 {min(i + batch_size, len(data))}/{len(data)} 行")

            # 最后提交
            trans.commit()

        except Exception as e:
            trans.rollback()
            print(f"上传失败: {e}")
            raise

    print(f"数据上传成功，共插入 {len(df)} 行")
    return True


    
