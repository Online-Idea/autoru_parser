import logging
import time

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from parse_autoru import parse_autoru
from random_wait import random_wait
from result_processing import format_work, dealer_data, dealers_pandas

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

our_clients = pd.read_excel('start.xlsx', sheet_name='По дилеру')['Наш клиент']
dealers_to_parse = pd.read_excel('start.xlsx', sheet_name='Настройки дилера')

for client in our_clients:
    logging.info(f'Клиент {client}')
    client_competition = dealers_to_parse[dealers_to_parse['Наш клиент'] == client]

    df = pd.DataFrame({'mark_model': [], 'complectation': [], 'modification': [], 'year': [], 'dealer': [],
                       'price_with_discount': [], 'price_no_discount': [], 'link': [], 'condition': [], 'in_stock': []})

    for _, competitor in client_competition.iterrows():
        current_dealer = competitor['Дилер']
        dealer_url = competitor['Ссылка']
        region = competitor['Регион']
        logging.info(f'Конкурент {current_dealer}')
        random_wait()
        cars = parse_autoru(dealer_url, driver, dealer_name=current_dealer)
        if cars:
            df = df._append(dealer_data(cars))

    file_after_pandas = dealers_pandas(df, client)
    format_work(file_after_pandas, client)

driver.quit()

logging.info(f'Общее время парсинга: {time.perf_counter() - start:.3f}')
