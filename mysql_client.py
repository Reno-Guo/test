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
    connection_string = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{password_encoded}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    return create_engine(connection_string)

# 列名转小写
def to_mysql_data(table_name,upload_mode,df):
    engine=get_engine()
    table_name=TABLES[table_name]
    with engine.connect() as conn:
        if upload_mode == 'replace':
            try:
                conn.execute(text(f"DELETE FROM {table_name}"))
            except Exception as truncate_e:
                conn.execute(text(f"DELETE FROM {table_name}"))
        df.columns = df.columns.str.lower()
        df.to_sql(table_name, engine, if_exists='append', index=False)



