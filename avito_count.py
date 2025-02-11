import logging
import time

import pandas as pd

from utils.browser_driver import browser_driver
from utils.parse_avito import total_ads_count, count_by_mark

COLUMNS_RUS = {
    'region': 'Регион',
    'goods_type': 'GoodsType',
    'type_of_vehicle': 'TypeOfVehicle',
    'body_type': 'BodyType',
    'url': 'Ссылка',
    'total_count': 'Количество',
    'mark': 'Марка',
    'count': 'Количество',
}

# Этот скрипт собирает только количество объявлений авито
start = time.perf_counter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)

driver = browser_driver()

marks = pd.read_excel('start.xlsx', sheet_name='Количество авито')

# df = pd.DataFrame({'region': [], 'goods_type': [], 'type_of_vehicle': [], 'body_type': [], 'url': [],
# 'total_count': []})
rows_total_count = []
rows_count_by_mark = []
count_by_mark2 = []

for _, mark in marks.iterrows():
    # Только активные
    if str(mark['Активно']).lower() != 'да':
        continue

    # Настройки парсера
    logging.info(f'\n{mark}')
    region = mark['Регион']
    goods_type = mark['GoodsType']
    type_of_vehicle = mark['TypeOfVehicle']
    body_type = mark['BodyType']
    url = mark['Полная ссылка']

    driver.get(url)

    total_count = total_ads_count(driver)
    count_by_mark_ = count_by_mark(driver)

    new_row = {
        'region': region,
        'goods_type': goods_type,
        'type_of_vehicle': type_of_vehicle,
        'body_type': body_type,
        'url': url,
        'total_count': total_count,
    }
    rows_total_count.append(new_row)

    for row in count_by_mark_:
        row2 = row | new_row
        count_by_mark2.append(row2)

df = pd.DataFrame(rows_total_count)
df_by_mark = pd.DataFrame(count_by_mark2)
df_by_mark['count'] = df_by_mark['count'].astype(int)

# Перевожу имена столбцов
df = df.rename(columns=COLUMNS_RUS)
df_by_mark = df_by_mark.rename(columns=COLUMNS_RUS)

# Сохраняю
file_name = 'avito_count.xlsx'
with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
    df.T.reset_index().T.to_excel(writer, sheet_name='Общее', header=False, index=False)
    df_by_mark.T.reset_index().T.to_excel(writer, sheet_name='По маркам', header=False, index=False)
