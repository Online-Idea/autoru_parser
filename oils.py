import logging
import sys
import time

import pandas as pd
from openpyxl.reader.excel import load_workbook
from openpyxl.workbook import Workbook
from pandas import DataFrame

from utils.auth_autoru import check_auth_page
from utils.browser_driver import browser_driver
from utils.captcha import check_captcha
from utils.email_sender import send_email_to_client
from utils.parse_autoru import parse_autoru_mark
from utils.parse_avito import parse_avito
from utils.random_wait import random_wait
from utils.result_processing import format_work, dealer_data, dealers_pandas, final_file_path


start = time.perf_counter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)

driver = browser_driver()

oils = pd.read_excel('oils.xlsx', sheet_name='oils')

for _, row in oils.iterrows():
    # Путь к готовому файлу
    final_file = final_file_path(row['Название'], 'авито')
    # df = pd.DataFrame({'title': [], 'dealer': [], 'price': [], 'description': [], 'geo': [], 'link': []})

    ads = parse_avito(row['Ссылка'], driver, '', True)

    df = pd.DataFrame.from_records(ads)
    df.price = df.price.fillna(0).astype(int)
    df = df.sort_values(by=['price'])

    with pd.ExcelWriter(final_file, engine='xlsxwriter') as writer:
        df.T.reset_index().T.to_excel(writer, sheet_name='Выдача', header=False, index=False)

    file_after_pandas = load_workbook(final_file)
    sheet = file_after_pandas['Выдача']
    sheet.column_dimensions['A'].width = 40
    sheet.column_dimensions['B'].width = 40
    sheet.column_dimensions['D'].width = 40

    sheet.freeze_panes = 'A1'

    sheet.auto_filter.ref = sheet.dimensions

    file_after_pandas.save(final_file)

    print('ye')
