import csv
import datetime
import logging
import time

import openpyxl
import requests
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from utils.random_wait import random_wait

# Скрипт на сбор телефонов из объявлений

start = time.perf_counter()

# Для авторизации
YANDEX_EMAIL = 'mirow.ev'
YANDEX_PASSWORD = '7Sk4ldfDS'

# Ссылка на список объявлений
CARS_URL = 'https://auto.ru/moskva/cars/exeed/all/?km_age_to=100'

# Фильтры выдачи
DATETIME_AFTER = '2024-01-23'
DATETIME_BEFORE = '2024-01-23'
REGION = 'Москва'
MARK = 'Audi'
MODEL = 'Q8'

# Секунд между запросами
MIN_WAIT = 2.0
MAX_WAIT = 3.0

today = datetime.date.today().strftime('%d.%m.%Y')
FILENAME = f'{MARK} {MODEL} телефоны объявлений {today}.xlsx'

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

wait = WebDriverWait(driver, 120)
wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

url = 'https://auto.ru'
driver.get(url)

WebDriverWait(driver, 86400).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Header__secondLine")))

# Клик по 0, 0 на случай если авто.ру показывает pop up
actions = ActionChains(driver)
actions.move_by_offset(0, 0).click().perform()

# Авторизация
login_btn = driver.find_element(By.CLASS_NAME, 'HeaderUserMenu__loginButton')
login_btn.click()

# Через Яндекс ID
yandex_id_btn = driver.find_element(By.ID, 'yandex')
yandex_id_btn.click()
random_wait()
yandex_login_input = driver.find_element(By.ID, 'passp-field-login')
yandex_login_input.send_keys(YANDEX_EMAIL)
yandex_sign_in_btn = driver.find_element(By.ID, 'passp:sign-in')
yandex_sign_in_btn.click()
random_wait()
yandex_password_input = driver.find_element(By.ID, 'passp-field-passwd')
yandex_password_input.send_keys(YANDEX_PASSWORD)
yandex_sign_in_btn2 = driver.find_element(By.ID, 'passp:sign-in')
yandex_sign_in_btn2.click()
random_wait()

# Собираю данные объявлений
# driver.get(CARS_URL)

# cars = parse_autoru_mark(CARS_URL, driver)
endpoint = 'http://stats.onllline.ru/api/v1/autoru_parsed_ads/filter'
params = {
    'datetime_after': DATETIME_AFTER,
    'datetime_before': DATETIME_BEFORE,
    'region': REGION,
    'mark': MARK,
    'model': MODEL,
}
response = requests.get(endpoint, params=params)
if response.status_code == 200:
    cars = response.json()
else:
    print('Не удалось получить данные выдачи')

# Беру уже собранные телефоны
# TODO возможно что авто.ру даёт временный телефон, не на всю жизнь объявления. Тогда брать уже собранные нет смысла
with open('parsed_phones.csv', 'r', encoding='cp1251') as csvfile:
    csv_reader = csv.reader(csvfile)
    next(csv_reader)  # Пропуск заголовка
    parsed_phones = {row[0]: row[1] for row in csv_reader}

# Сохраняю в csv чтобы при ошибках не идти повторно по уже собранным объявлениям
with open('parsed_phones.csv', 'a', newline='', encoding='cp1251') as csvfile:
    writer = csv.writer(csvfile)

    # Иду по объявлениям, собираю телефоны
    total_cars = len(cars)
    for i, car in enumerate(cars):
        # Пропускаю если телефон уже собран
        if car['link'] in parsed_phones:
            continue

        # Пропуск по имени дилера
        if 'авилон' in car['dealer'].lower():
            logging.info('Авилон, пропускаю')
            continue

        try:
            driver.get(car['link'])
            logging.info(f'Объявление {i + 1:3} из {total_cars:3} {car["link"]}')

            # 404
            if '404' in driver.title:
                logging.info('404 Страница не найдена')
                random_wait(MIN_WAIT, MAX_WAIT)
                continue

            WebDriverWait(driver, 86400).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Header__secondLine")))

            # Собираю телефон
            try:
                show_phone_btn = driver.find_element(By.CLASS_NAME, 'OfferPhone__showPhoneText')
            except NoSuchElementException:
                car['phone'] = 'автомобиль продан'
            else:
                show_phone_btn.click()

            random_wait(MIN_WAIT, MAX_WAIT)

            try:
                phone = driver.find_element(By.CLASS_NAME, 'SellerPopup__phoneNumber')
            except NoSuchElementException:
                car['phone'] = 'ошибка при получении номера'
            else:
                car['phone'] = phone.text

            writer.writerow([car['link'], car['phone']])

        except TimeoutException:
            continue


# Сохраняю в xlsx
wb = openpyxl.Workbook()
ws = wb.active
cols = list(cars[0].keys())
ws.append(cols)

for car in cars:
    values = (car[k] for k in cols if k in car)
    ws.append(values)
wb.save(FILENAME)


driver.quit()

logging.info(f'Общее время парсинга: {time.perf_counter() - start:.3f}')
