import os
import sys
from datetime import datetime
import logging
import time

import pandas as pd
from pandas import DataFrame

from result_processing import data_work, format_work, dealer_data, dealers_pandas
from parse_page import parse_page
from random_wait import random_wait
from email_sender import send_email_to_client

import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

start = time.perf_counter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)

options = uc.ChromeOptions()
# Отключаю окно сохранения пароля
prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
options.add_experimental_option("prefs", prefs)

driver = uc.Chrome(driver_executable_path=ChromeDriverManager().install(), options=options)

wait = WebDriverWait(driver, 10)
wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

if len(sys.argv) > 1 and sys.argv[1] == '--by_request':  # Одинарный запуск
    marks = pd.read_excel('start.xlsx', sheet_name='По марке (по запросу)')
else:  # Для автоматического запуска
    marks = pd.read_excel('start.xlsx', sheet_name='По марке (автоматом)')

# Сортирую по региону и марке чтобы не парсить одну и ту же марку для разных клиентов
marks = marks.sort_values(by=['Регион', 'Марка'])

previous_mark = ''
previous_df: DataFrame

for _, mark in marks.iterrows():
    # Только активные
    if str(mark['Активно']).lower() != 'да':
        continue

    logging.info(f'\n{mark}')
    client = mark['Наш клиент']
    autoru_name = mark['Имя клиента на авто.ру']
    mark_name = mark['Марка']
    mark_url = mark['Ссылка']
    region = mark['Регион']
    client_email = mark['Почты клиентов']

    # Если текущая марка не равна прошлой марке значит парсим
    if mark_name != previous_mark:
        df = pd.DataFrame({'mark_model': [], 'complectation': [], 'modification': [], 'year': [], 'dealer': [],
                           'price_with_discount': [], 'price_no_discount': [], 'with_nds': [], 'link': [], 'condition': [],
                           'in_stock': [], 'services': [], 'tags': [], 'photos': []})

        random_wait()
        cars = parse_page(mark_url, driver, region)
        if cars:
            df = df._append(dealer_data(client, cars))

        file_after_pandas = dealers_pandas(df, autoru_name)

    # Иначе берём уже спарсенные объявления
    else:
        file_after_pandas = dealers_pandas(previous_df, autoru_name)

    file_path_result = format_work(file_after_pandas, autoru_name, client)

    send_email_to_client(client_email, file_path_result)

    previous_mark = mark_name
    previous_df = df


driver.quit()

logging.info(f'Общее время парсинга: {time.perf_counter() - start:.3f}')
