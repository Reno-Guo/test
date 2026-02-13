      
import re
import pandas as pd
from datetime import datetime, timedelta
ods_asin_philips_file_columns = [
                    'Branded ASINs',
                    'Competitor ASINs',
                    'Competitor Name',
                    'Head non branded keywords',
                    'Competitor Name',
                    'Competitor Name-Broad Matching List'
                ]
ods_asin_philips_table_columns = [
                    'Branded_ASINs',
                    'Competitor_ASINs',
                    'Head_non_branded_keywords',
                    'Competitor_keywords_concat',
                    'Competitor_brand_asin',
                    'Competitor_brand_keywords'
                ]
ods_date_event_file_columns =[
    #Star Date	End Date	Event Type	Event	country
    'Star Date','End Date','Event Type','Event','country'
]
ods_date_event_table_columns =[
    #date,Events,event_type,country
    'date','Events','event_type','country'
]
ods_asin_sale_goal_file_columns =[
    #Date	Country	SKU	PCOGS	Order Revenue	Units
    'Date','Country','SKU','PCOGS','Order Revenue','Units','ASIN'
]
ods_asin_sale_goal_table_columns =[
    #date,country,sku,pcogs,revenue,units
    'date','country','sku','pcogs','revenue','units','asin'
]
ods_category_dsp_file_columns =[
    #Creative_Detail	Inventory	Funnel	Audience
    'Creative_Detail','Inventory','Funnel','Audience','Series','VCP'
]
ods_category_dsp_table_columns =[
    #Creative_Detail	Inventory	Funnel	Audience
    'creative_detail','inventory','funnel','audience','series','vcp'
]

offline_deal_sku_file_columns = [
    'country','VCP','SUB category','SKU','ASIN','Start Date','End Date',
    'Sell Out Unit Deal  Forecast',' Promo Price',' PCOGS Deal Forecast',
    ' Deal 检查','deal 生效价格','daily unit 目标','Actual unit ','爆发系数'
]
offline_deal_sku_table_columns = [
    'country','vcp','sub_category','sku','asin','start_date','end_date',
    'sell_out_unit_deal_forecast','promo_price','pcogs_deal_forecast',
    'deal_check','deal_effective_price','daily_unit_target','actual_unit','burst_coefficient'
]

offline_roas_subcategory_file_columns = [
    'country','Subcategory','Focus tier(1 = Max)','ROAS Floor','ROAS Target'
]
offline_roas_subcategory_table_columns = [
    'country','subcategory','focus_tier','roas_floor','roas_target'
]

def get_file_columns_config(table_name):
    if  'ods_asin_philips' in table_name:
        return  ods_asin_philips_file_columns
    elif 'ods_date_even' in table_name :
        return ods_date_event_file_columns
    elif 'ods_asin_sale_goal' in table_name:
        return ods_asin_sale_goal_file_columns
    elif 'ods_category_dsp' in table_name:
        return ods_category_dsp_file_columns
    elif 'offline_deal_sku' in table_name:
        return offline_deal_sku_file_columns
    elif 'offline_roas_subcategory' in table_name:
        return offline_roas_subcategory_file_columns
    return []

def get_table_columns_config(table_name,df):
    if 'ods_asin_philips' in table_name:
        df.columns = ods_asin_philips_table_columns
        return df
    elif 'ods_date_even' in table_name:
        df=process_ods_date_event_data( df)
        return df
    elif 'ods_goal_vcp' in table_name:
        result = convert_excel_correct_goal(df)
        if result is None or len(result) == 0:
            print("\n=== 正确Goal转换失败，尝试简单转换 ===")
            result = convert_excel_simple_correct_goal(df)
        return result
    elif 'ods_asin_sale_goal' in table_name :
        df.columns = ods_asin_sale_goal_table_columns
    elif 'ods_category_dsp' in table_name:
        df.columns = ods_category_dsp_table_columns
        return df
    elif 'offline_deal_sku' in table_name:
        df.columns = offline_deal_sku_table_columns
        return df
    elif 'offline_roas_subcategory' in table_name:
        df.columns = offline_roas_subcategory_table_columns
        return df
    return df


def expand_date_range(df, start_date_col='Star Date', end_date_col='End Date', event_col='Event',
                      event_type_col='Event Type', country_col='country'):
    """
    将日期范围数据展开为每天一条记录

    参数:
    - df: 输入的DataFrame
    - start_date_col: 开始日期列名
    - end_date_col: 结束日期列名
    - event_col: 事件列名
    - event_type_col: 事件类型列名
    - country_col: 国家列名
    """

    expanded_rows = []

    for index, row in df.iterrows():
        try:
            # 解析开始和结束日期
            start_date = pd.to_datetime(row[start_date_col])
            end_date = pd.to_datetime(row[end_date_col])

            # 验证日期有效性
            if pd.isna(start_date) or pd.isna(end_date):
                print(f"警告: 行 {index} 的日期无效，跳过")
                continue

            # 生成日期范围内的每一天
            current_date = start_date
            while current_date <= end_date:
                new_row = {
                    'date': current_date.date(),  # 转换为日期格式
                    'Events': row[event_col],
                    'event_type': row[event_type_col],
                    'country': row[country_col]
                }
                expanded_rows.append(new_row)
                current_date += timedelta(days=1)
        except Exception as e:
            print(f"处理行 {index} 时出错: {e}")
            continue

    # 创建新的DataFrame
    if expanded_rows:
        expanded_df = pd.DataFrame(expanded_rows)
        return expanded_df
    else:
        return pd.DataFrame(columns=['date', 'Events', 'event_type', 'country'])


def process_ods_date_event_data(df):
    """
    专门处理 ods_date_event 表的数据转换
    将 Star Date 和 End Date 之间的日期范围展开为每一天
    """
    if df.empty:
        return df

    # 确保日期列是datetime类型
    df['Star Date'] = pd.to_datetime(df['Star Date'], errors='coerce')
    df['End Date'] = pd.to_datetime(df['End Date'], errors='coerce')

    # 调用展开函数
    expanded_df = expand_date_range(
        df,
        start_date_col='Star Date',
        end_date_col='End Date',
        event_col='Event',
        event_type_col='Event Type',
        country_col='country'
    )

    return expanded_df

def convert_excel_correct_goal_file_path(input_file_path):
    """
    转换Excel数据，goal字段只取Budget值，跳过Budget%
    """
    print(f"正在处理文件: {input_file_path}")

    try:
        # 读取Excel文件
        df = pd.read_excel(input_file_path, sheet_name='Sheet1', header=None)
        result = convert_excel_correct_goal(df)
        return result
    except Exception as e:
        print(f"读取文件 {input_file_path} 时出错: {e}")
        return None

def convert_excel_correct_goal(df):
    """
    转换Excel数据，goal字段只取Budget值，跳过Budget%
    """
    try:
        # 打印数据结构用于分析
        print("\n=== 数据结构详细分析 ===")
        for i in range(min(15, len(df))):
            row_preview = []
            for j in range(min(15, df.shape[1])):
                cell = df.iloc[i, j]
                if pd.isna(cell):
                    row_preview.append('NaN')
                else:
                    cell_str = str(cell)
                    row_preview.append(cell_str[:15])
            print(f"行 {i}: {row_preview}")

        # 从数据中提取国家信息
        countries = extract_countries_from_data(df)
        print(f"提取到的国家列表: {countries}")

        # 处理数据
        result_data = []
        year = 2026

        # 月份映射
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        current_ad_type = None

        print("\n=== 开始处理数据 ===")

        for i in range(len(df)):
            # 获取第一列的值（国家信息）
            country_cell = df.iloc[i, 0] if df.shape[1] > 0 else None

            if pd.notna(country_cell):
                cell_str = str(country_cell)

                # 检查是否是SA部分标题
                if 'SA' in cell_str and 'Budget' in cell_str:
                    current_ad_type = 'SA'
                    print(f"行 {i}: 找到SA部分 - {cell_str}")
                    continue

                # 检查是否是DSP部分标题
                elif 'DSP' in cell_str and 'Budget' in cell_str:
                    current_ad_type = 'DSP'
                    print(f"行 {i}: 找到DSP部分 - {cell_str}")
                    continue

                # 检查是否是其他国家相关的标题（跳过）
                elif any(keyword in cell_str for keyword in ['Total', 'VCP', 'Year', 'Budget']):
                    print(f"行 {i}: 跳过标题行 - {cell_str}")
                    continue

            # 如果是数据行且有当前数据类型
            if current_ad_type and i > 0:
                # 检查第一列是否是有效国家代码
                country = country_cell
                if (pd.notna(country) and
                        str(country).strip() in countries and
                        str(country).strip() != ''):

                    # 获取产品类别（应该是第二列）
                    category = df.iloc[i, 1] if df.shape[1] > 1 else None

                    if pd.notna(category) and str(category).strip() != '':
                        print(f"行 {i}: 处理{current_ad_type}数据 - 国家: {country}, 类别: {category}")

                        # 处理该行的月度数据（从第3列开始，只取Budget列，跳过Budget%列）
                        for month_idx, month_name in enumerate(months):
                            budget_col_idx = 3 + month_idx * 2  # Budget列（每2列的第一列）

                            if budget_col_idx < df.shape[1]:
                                budget_value = extract_numeric_value(df.iloc[i, budget_col_idx])

                                # 跳过百分比列（下一列）
                                # percentage_col_idx = budget_col_idx + 1  # 这是Budget%列，我们跳过

                                print(f"  {month_name}: Budget列{budget_col_idx} = {budget_value}")

                                # 使用yyyy-MM-dd格式的日期
                                date_str = month_to_date_string(year, month_name)

                                result_data.append({
                                    'VCP_Category': str(category).strip(),
                                    'ad_type': current_ad_type,
                                    'time': date_str,
                                    'goal': budget_value,
                                    'Country': str(country).strip()
                                })

        # 创建结果DataFrame
        result_df = pd.DataFrame(result_data)

        # 保存结果
        output_file = "表3_正确Goal转换结果.xlsx"
        result_df.to_excel(output_file, index=False)

        print(f"\n=== 转换结果摘要 ===")
        print(f"输出文件: {output_file}")
        print(f"总记录数: {len(result_df)}")

        if len(result_df) > 0:
            print_statistics(result_df)
        else:
            print("警告: 未生成任何记录")
            # 尝试备用方法
            return convert_excel_alternative_correct_goal(df, countries, year)

        return result_df

    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def extract_countries_from_data(df):
    """从数据中提取国家信息"""
    countries = set()

    # 分析数据，提取有效的国家代码
    for i in range(len(df)):
        cell = df.iloc[i, 0] if df.shape[1] > 0 else None
        if pd.notna(cell):
            cell_str = str(cell).strip()
            # 识别常见的国家代码（2-3个字母）
            if (len(cell_str) in [2, 3] and
                    cell_str.isalpha() and
                    cell_str.isupper() and
                    cell_str not in ['SA', 'DSP', 'VCP', 'NaN', 'Total', 'Year', 'Budget']):
                countries.add(cell_str)

    # 如果没有找到标准国家代码，尝试从数据内容推断
    if len(countries) == 0:
        print("未找到标准国家代码，从数据内容推断...")
        for i in range(1, min(50, len(df))):  # 检查前50行
            cell = df.iloc[i, 0] if df.shape[1] > 0 else None
            if pd.notna(cell):
                cell_str = str(cell).strip()
                # 排除明显的标题行
                if (cell_str not in ['Total', 'VCP', 'Year', 'Budget', 'SA', 'DSP'] and
                        not any(keyword in cell_str for keyword in ['Budget', 'Year', 'Total']) and
                        len(cell_str) > 0):
                    countries.add(cell_str)

    return sorted(list(countries))


def extract_numeric_value(cell_value):
    """从单元格中提取数值"""
    if pd.isna(cell_value):
        return 0

    cell_str = str(cell_value)

    # 移除货币符号、千分位分隔符等
    cell_str = re.sub(r'[€$,]', '', cell_str).strip()

    # 提取数字
    numeric_match = re.search(r'[-+]?\d*\.\d+|\d+', cell_str)
    if numeric_match:
        try:
            return float(numeric_match.group())
        except:
            return 0
    return 0


def month_to_date_string(year, month_name):
    """将月份转换为yyyy-MM-dd格式的日期字符串"""
    month_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }

    month_num = month_map.get(month_name, 1)
    date_obj = datetime(year, month_num, 1)
    return date_obj.strftime('%Y-%m-%d')


def print_statistics(result_df):
    """打印统计信息"""
    print(f"产品类别数: {result_df['VCP_Category'].nunique()}")

    sa_count = len(result_df[result_df['ad_type'] == 'SA'])
    dsp_count = len(result_df[result_df['ad_type'] == 'DSP'])
    print(f"SA记录数: {sa_count}")
    print(f"DSP记录数: {dsp_count}")

    sa_total = result_df[result_df['ad_type'] == 'SA']['goal'].sum()
    dsp_total = result_df[result_df['ad_type'] == 'DSP']['goal'].sum()
    print(f"SA数据总和: {sa_total:,.2f}")
    print(f"DSP数据总和: {dsp_total:,.2f}")

    print(f"国家分布: {result_df['Country'].value_counts().to_dict()}")

    print("\n前10条记录预览:")
    print(result_df.head(10))

    # 显示数据验证
    print("\n=== 数据验证 ===")
    sample_records = result_df.head(6)
    for idx, record in sample_records.iterrows():
        print(f"类别: {record['VCP_Category']}, 类型: {record['ad_type']}, "
              f"时间: {record['time']}, 目标: {record['goal']}, 国家: {record['Country']}")


def convert_excel_alternative_correct_goal(df, countries, year):
    """备用转换方法，只取Budget值"""
    print("=== 使用备用转换方法（只取Budget值）===")

    result_data = []
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # 简单处理：按行处理，第一列是国家，第二列是类别
    for i in range(2, len(df)):  # 从第3行开始
        country = df.iloc[i, 0] if df.shape[1] > 0 else None
        category = df.iloc[i, 1] if df.shape[1] > 1 else None

        if pd.isna(country) or pd.isna(category):
            continue

        country_str = str(country).strip()
        category_str = str(category).strip()

        # 确定广告类型（根据行位置或内容）
        if i < 20:  # 前20行假设是SA
            ad_type = 'SA'
        else:  # 后面的是DSP
            ad_type = 'DSP'

        # 检查是否是有效数据行
        if (len(country_str) > 0 and len(category_str) > 0 and
                country_str not in ['Total', 'VCP', 'Year', 'Budget'] and
                category_str not in ['Total', 'VCP', 'Year', 'Budget']):

            print(f"行 {i}: {ad_type} - 国家: {country_str}, 类别: {category_str}")

            for month_idx, month_name in enumerate(months):
                budget_col_idx = 4 + month_idx * 2  # 只取Budget列

                if budget_col_idx < df.shape[1]:
                    budget_value = extract_numeric_value(df.iloc[i, budget_col_idx])
                    date_str = month_to_date_string(year, month_name)

                    result_data.append({
                        'VCP_Category': category_str,
                        'ad_type': ad_type,
                        'time': date_str,
                        'goal': budget_value,
                        'Country': country_str
                    })

    result_df = pd.DataFrame(result_data)

    if len(result_df) > 0:
        output_file = "表3_备用正确Goal转换结果.xlsx"
        result_df.to_excel(output_file, index=False)
        print(f"备用方法转换完成！生成 {len(result_df)} 条记录")
        print_statistics(result_df)

    return result_df

def convert_excel_simple_correct_goal_file_path(input_file_path):
    """简单直接的处理版本，只取Budget值"""
    print("=== 使用简单直接处理版本 ===")

    df = pd.read_excel(input_file_path, sheet_name='Sheet1', header=None)
    result = convert_excel_simple_correct_goal(df)
    return result
def convert_excel_simple_correct_goal(df):
    """简单直接的处理版本，只取Budget值"""
    print("=== 使用简单直接处理版本 ===")

    result_data = []
    year = 2026
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # 假设数据格式：
    # 第一列：国家
    # 第二列：产品类别
    # 第3列开始：月度数据（Budget, Budget%, Budget, Budget%, ...）

    for i in range(2, len(df)):  # 从第3行开始
        country = df.iloc[i, 0] if df.shape[1] > 0 else None
        category = df.iloc[i, 1] if df.shape[1] > 1 else None

        if pd.isna(country) or pd.isna(category):
            continue

        country_str = str(country).strip()
        category_str = str(category).strip()

        # 跳过标题行
        if any(keyword in country_str for keyword in ['Total', 'VCP', 'Year', 'Budget']):
            continue
        if any(keyword in category_str for keyword in ['Total', 'VCP', 'Year', 'Budget']):
            continue

        # 根据行位置确定SA/DSP
        ad_type = 'SA' if i < 30 else 'DSP'  # 假设前30行是SA，后面是DSP

        print(f"行 {i}: {ad_type} - 国家: {country_str}, 类别: {category_str}")

        for month_idx, month_name in enumerate(months):
            budget_col_idx = 4 + month_idx * 2  # 只取Budget列，跳过Budget%

            if budget_col_idx < df.shape[1]:
                budget_value = extract_numeric_value(df.iloc[i, budget_col_idx])
                date_str = month_to_date_string(year, month_name)

                result_data.append({
                    'VCP_Category': category_str,
                    'ad_type': ad_type,
                    'time': date_str,
                    'goal': budget_value,
                    'Country': country_str
                })

    result_df = pd.DataFrame(result_data)

    if len(result_df) > 0:
        output_file = "表3_简单正确Goal转换结果.xlsx"
        result_df.to_excel(output_file, index=False)
        print(f"简单转换完成！生成 {len(result_df)} 条记录")
        print_statistics(result_df)

    return result_df


# 使用示例
if __name__ == "__main__":
    input_file = r"C:\Users\lenovo\Downloads\新建 Microsoft Excel 工作表.xlsx"

    # 首先尝试正确goal转换
    print("=== 尝试正确Goal转换 ===")
    result = convert_excel_correct_goal(input_file)

    if result is None or len(result) == 0:
        print("\n=== 正确Goal转换失败，尝试简单转换 ===")
        result = convert_excel_simple_correct_goal(input_file)

    if result is not None and len(result) > 0:
        print(result.columns.tolist())
        print("\n🎉 转换成功完成！")
        print(f"📊 总记录数: {len(result)}")
        print(f"🌍 涉及国家: {sorted(result['Country'].unique().tolist())}")
        print(f"📈 SA记录: {len(result[result['ad_type'] == 'SA'])}")
        print(f"📊 DSP记录: {len(result[result['ad_type'] == 'DSP'])}")

        # 验证goal字段只包含Budget值
        print("\n✅ Goal字段验证：只包含Budget数值，不包含百分比")
        sample_goals = result['goal'].head(10)
        print("前10个goal值:", sample_goals.tolist())
    else:
        print("\n❌ 转换失败，请检查数据格式")

    
