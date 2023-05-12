from datetime import datetime
import logging
import time

import pandas as pd

from result_processing import data_work, format_work, dealer_data, dealers_pandas
from parse_page import parse_page
from random_wait import random_wait

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

marks = pd.read_excel('start.xlsx', sheet_name='По марке')

for _, mark in marks.iterrows():
    logging.info(mark)
    client = mark['Наш клиент']
    mark_name = mark['Марка']
    mark_url = mark['Ссылка']
    region = mark['Регион']

    df = pd.DataFrame({'mark_model': [], 'complectation': [], 'modification': [], 'year': [], 'dealer': [],
                       'price_with_discount': [], 'price_no_discount': [], 'with_nds': [], 'link': [], 'condition': [],
                       'in_stock': [], 'services': [], 'tags': [], 'photos': []})

    random_wait()
    cars = parse_page(mark_url, driver, region)
    if cars:
        df = df._append(dealer_data(cars))

    # TODO убрать
    df_all = pd.DataFrame.from_records(cars)
    today = datetime.now().strftime('%d.%m.%Y')
    file_name = f'results/Выдача {client} {today}.xlsx'
    df_all.T.reset_index().T.to_excel(file_name, sheet_name='Все', header=False, index=False)

    file_after_pandas = dealers_pandas(df, client)
    format_work(file_after_pandas, client)

driver.quit()

logging.info(f'Общее время парсинга: {time.perf_counter() - start:.3f}')
