import datetime
import logging
import time

import pandas as pd
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from utils.parse_autoru import authorize_autoru, collect_links, parse_autoru_ad
from utils.random_wait import random_wait

# Скрипт для парсинга внутри объявлений

start = time.perf_counter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)


service = Service()
options = uc.ChromeOptions()
# Отключаю окно сохранения пароля
prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=options, service=service)
driver.get('https://auto.ru')

wait = WebDriverWait(driver, 120)
# wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Header__secondLine")))

tasks = pd.read_excel('start.xlsx', sheet_name='Внутри объявлений')

for _, task in tasks.iterrows():
    # Только активные
    if str(task['Активно']).lower() != 'да':
        continue

    name = task['Название']
    login = task['Логин']
    password = task['Пароль']
    links_start = task['Где взять ссылки на объявления']

    logging.info(f'{name}\n{links_start}')

    if not pd.isnull(login) and not pd.isnull(password):
        business = True if 'cabinet' in links_start or 'agency' in links_start else False
        authorize_autoru(driver, login, password, business)

    links_start = links_start.split(', ')
    ads_links = []
    for link in links_start:
        logging.info(link)
        ads_links.extend(collect_links(driver, link))

    logging.info(ads_links)

    cars = []
    len_ads_links = len(ads_links)
    for i, ad_link in enumerate(ads_links):
        logging.info(f'Объявление {i + 1:3} из {len_ads_links} {ad_link}')
        cars.append(parse_autoru_ad(driver, ad_link))
        random_wait()

    df = pd.DataFrame(cars)

    today = datetime.date.today().strftime('%d.%m.%Y')
    df.to_csv(f'results/ads/Объявления {name} {today}.csv', sep=';', header=True, encoding='utf8', index=False, decimal=',')

logging.info(f'Общее время парсинга: {time.perf_counter() - start:.3f}')
