from selenium.common import WebDriverException
from user_agent import generate_user_agent
import logging
import sys
import time

import pandas as pd
import undetected_chromedriver as uc
from pandas import DataFrame
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from email_sender import send_email_to_client
from parse_autoru import parse_autoru
from parse_avito import parse_avito
from random_wait import random_wait
from result_processing import format_work, dealer_data, dealers_pandas



start = time.perf_counter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)

cars = []

for _ in range(10):
    options = uc.ChromeOptions()
    # Отключаю окно сохранения пароля
    prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
    options.add_experimental_option("prefs", prefs)

    random_user_agent = generate_user_agent(os=['win', 'linux', 'mac'], navigator=['chrome', 'firefox'])
    logging.info(random_user_agent)
    options.add_argument(f'--user-agent={random_user_agent}')

    driver = uc.Chrome(driver_executable_path=ChromeDriverManager().install(), options=options)

    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    if len(sys.argv) > 1 and sys.argv[1] == '--by_request':  # Одинарный запуск
        marks = pd.read_excel('start.xlsx', sheet_name='По марке (по запросу)')
    else:  # Для автоматического запуска
        marks = pd.read_excel('start.xlsx', sheet_name='По марке (автоматом)')

    # Сортирую по сайту, региону и марке чтобы не парсить одно и то же для разных клиентов
    marks = marks.sort_values(by=['Сайт', 'Регион', 'Марка'])

    for _, mark in marks.iterrows():
        # Только активные
        if str(mark['Активно']).lower() != 'да':
            continue

        logging.info(f'\n{mark}')
        client = mark['Наш клиент']
        autoru_name = mark['Имя клиента на авто.ру']
        mark_name = mark['Марка']
        site = mark['Сайт'].lower()
        mark_url = mark['Ссылка']
        region = mark['Регион']
        client_email = mark['Почты клиентов']

        df = pd.DataFrame({'mark_model': [], 'complectation': [], 'modification': [], 'year': [], 'dealer': [],
                           'price_with_discount': [], 'price_no_discount': [], 'with_nds': [], 'link': [],
                           'condition': [], 'in_stock': [], 'services': [], 'tags': [], 'photos': []})

        if site in ['авто.ру', 'автору']:
            try:
                cars += parse_autoru(mark_url, driver, region, first_page=True)
            except WebDriverException:
                pass

    driver.quit()

    random_wait()

if cars:
    df = df._append(dealer_data(client, cars))

file_after_pandas = dealers_pandas(df, autoru_name)

file_path_result = format_work(file_after_pandas, autoru_name, client)

if str(client_email) != 'nan':
    send_email_to_client(client_email, file_path_result)
