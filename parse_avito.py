import logging
import re
import time
import pandas as pd

from bs4 import BeautifulSoup
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from undetected_chromedriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager

from random_wait import random_wait
from result_processing import dealer_data, dealers_pandas, format_work


def page_html(driver: Chrome):
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one('[class*="items-items"]')  # Объявления текущего города
    links = block.select('a[class*="iva-item-sliderLink"]')
    return [f"https://www.avito.ru{link.get('href')}" for link in links]


def ads_links(driver: Chrome):
    links = page_html(driver)

    try:
        next_page = driver.find_element(By.CSS_SELECTOR, "li[class*='styles-module-listItem_arrow_next']")
    except NoSuchElementException:
        next_page = False

    while next_page:
        next_page.click()
        random_wait()
        # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='index-logo']")))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        links += page_html(driver)

        try:
            next_page = driver.find_element(By.CSS_SELECTOR, "li[class*='styles-module-listItem_arrow_next']")
            next_page_class = next_page.find_element(By.TAG_NAME, 'span').get_attribute('class')
        except NoSuchElementException:
            next_page = False
        else:
            if 'styles-module-item_disabled' in next_page_class:
                next_page = False

    return links


def car_data(car, link):
    # Инфо об автомобиле
    mark_model = car.find('span', class_='title-info-title-text').text \
        .split(',')[0]
    generation = car.find(lambda tag: tag.name == 'span' and 'Поколение' in tag.text) \
        .parent.text.replace('Поколение: ', '')
    generation = generation[:generation.find('(')].strip()
    mark_model = f'{mark_model} {generation}'
    complectation = car.find(lambda tag: tag.name == 'span' and 'Комплектация' in tag.text)
    if complectation:
        complectation = complectation.parent.text.replace('Комплектация: ', '')
    try:
        capacity = car.find(lambda tag: tag.name == 'span' and 'Объём двигателя' in tag.text) \
            .parent.text.replace('Объём двигателя: ', '')
    except AttributeError:
        capacity = '0'
    engine = car.find(lambda tag: tag.name == 'span' and 'Модификация' in tag.text) \
        .parent.text.replace('Модификация: ', '')
    power = re.search(r'\((.*?)\)', engine).group(1)
    engine_type = car.find(lambda tag: tag.name == 'span' and 'Тип двигателя' in tag.text) \
        .parent.text.replace('Тип двигателя: ', '')
    transmission = car.find(lambda tag: tag.name == 'span' and 'Коробка передач' in tag.text) \
        .parent.text.replace('Коробка передач: ', '')
    drive = car.find(lambda tag: tag.name == 'span' and 'Привод' in tag.text) \
        .parent.text.replace('Привод: ', '')
    body = car.find(lambda tag: tag.name == 'span' and 'Тип кузова' in tag.text) \
        .parent.text.replace('Тип кузова: ', '').replace('-дверный', ' дв.')
    modification = '/'.join([body, capacity, power, engine_type, transmission, drive]).replace('/', ' / ').lower()
    year = car.find(lambda tag: tag.name == 'span' and 'Год выпуска' in tag.text) \
        .parent.text.replace('Год выпуска: ', '')

    # Цены
    price = car.select_one('[class*="style-price-value-main"]')
    price_with_discount = price.text
    price_no_discount = price.findChild("span").get('content')
    # Цена с НДС (пока по умолчанию False до тех пор пока авито не введёт это поле)
    with_nds = False

    condition = car.select_one('[class*="style-newLabel"]').text
    try:
        in_stock = car.select_one('[class*="CardBadge-title"]').text
    except AttributeError:
        in_stock = 'На заказ'
    dealer_name = car.select_one('[class*="style-seller-info-name"]')
    dealer_name = dealer_name.select_one('a').text

    # Услуги
    services = ''

    # Стикеры
    tags = ''

    # Количество фото
    try:
        photos = len(car.select_one('[class*="images-preview-previewWrapper"]'))
    except TypeError:
        photos = 1

    return {
        "mark_model": mark_model,
        "complectation": complectation,
        "modification": modification,
        "year": year,
        "dealer": dealer_name,
        "price_with_discount": price_with_discount,
        "price_no_discount": price_no_discount,
        "with_nds": with_nds,
        "link": link,
        "condition": condition,
        "in_stock": in_stock,
        "services": services,
        "tags": tags,
        "photos": photos,
    }


def parse_avito(driver: Chrome):
    cars = []
    cars_links = ads_links(driver)
    len_cars_links = len(cars_links)
    for i, car_link in enumerate(cars_links):
        logging.info(f'Объявление {i + 1:4} из {len_cars_links}, {car_link}')
        random_wait(max_wait=4)
        driver.get(car_link)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='index-logo']")))
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        car_element = soup.find("body")
        cars.append(car_data(car_element, car_link))

    return cars


start = time.perf_counter()

URL = 'https://www.avito.ru/moskva/avtomobili/novyy/genesis?radius=0&searchRadius=0'
client = 'БорисХоф Genesis'
autoru_name = client

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

driver.get(URL)

df = pd.DataFrame({'mark_model': [], 'complectation': [], 'modification': [], 'year': [], 'dealer': [],
                   'price_with_discount': [], 'price_no_discount': [], 'with_nds': [], 'link': [], 'condition': [],
                   'in_stock': [], 'services': [], 'tags': [], 'photos': []})

cars = parse_avito(driver)
if cars:
    df = df._append(dealer_data(client, cars))
file_after_pandas = dealers_pandas(df, autoru_name)
file_path_result = format_work(file_after_pandas, autoru_name, client)

driver.quit()

logging.info(f'Общее время парсинга: {time.perf_counter() - start:.3f}')
