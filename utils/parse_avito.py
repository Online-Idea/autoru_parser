import logging
import re

import requests
from bs4 import BeautifulSoup, PageElement
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome

from utils.random_wait import random_wait


RANDOM_MIN = 10
RANDOM_MAX = 15


def page_html(driver: Chrome) -> list[str]:
    """
    Собирает ссылки на объявления с текущей страницы
    @param driver: driver браузера
    @return: лист со ссылками
    """
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one('[class*="items-items"]')  # Объявления текущего города
    links = block.select('a[class*="iva-item-sliderLink"]')
    return [f"https://www.avito.ru{link.get('href')}" for link in links]


def car_data(car: PageElement, link: str) -> dict:
    """
    Собирает данные одного автомобиля
    @param car: элемент от BeautifulSoup
    @param link: ссылка на объявление
    @return: словарь с данными автомобиля
    """
    # Инфо об автомобиле
    try:
        try:
            mark_model = car.find('span', class_='title-info-title-text').text \
                .split(',')[0]
        except AttributeError:
            logging.info(car)
            return {}
        try:
            generation = car.find(lambda tag: tag.name == 'span' and 'Поколение' in tag.text) \
                .parent.text.replace('Поколение: ', '')
            generation = generation[:generation.find('(')].strip()
        except AttributeError:
            generation = ''
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
        # Цена с НДС (пока по умолчанию False до тех пор, пока авито не введёт это поле)
        with_nds = 'нет'

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
    except:
        return {}


def parse_avito(cars_url: str, driver: Chrome, mark: str) -> list[dict]:
    """
    Парсит авито
    @param cars_url: ссылка на страницу с объявлениями
    @param driver: driver браузера
    @return: лист словарей с данными автомобилей
    """
    driver.get(cars_url)

    cars = []

    wait = WebDriverWait(driver, 360)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Если прямая ссылка на марку возвращает 403 или 404 то выбираю эту марку со страницы всех автомобилей
    response = requests.get(driver.current_url)
    if response.status_code in [403, 404] and 'avtomobili' in cars_url:
        url_with_region = cars_url[:cars_url.find('avtomobili')]
        avito_autos_url = f'{url_with_region}/transport'
        driver.get(avito_autos_url)
        try:
            all_marks = driver.find_element(By.CSS_SELECTOR, 'button[data-marker="popular-rubricator/controls/all"]')
            all_marks.click()
        except StaleElementReferenceException:
            all_marks = driver.find_element(By.CSS_SELECTOR, 'button[data-marker="popular-rubricator/controls/all"]')
            all_marks.click()
        mark_on_site = driver.find_element(By.CSS_SELECTOR, f'a[title={mark}]')
        mark_on_site.click()
        new = driver.find_element(By.XPATH, "//span[contains(text(),'Новые')]")
        new.click()
        submit = driver.find_element(By.CSS_SELECTOR, 'button[data-marker="search-filters/submit-button"')
        submit.click()

        try:
            third_page = driver.find_element(By.CSS_SELECTOR, 'a[aria-label="Страница 3"]')
        except NoSuchElementException:
            pass
        else:
            third_page.click()
            random_wait(RANDOM_MIN, RANDOM_MAX)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            first_page = driver.find_element(By.CSS_SELECTOR, 'a[aria-label="Страница 1"]')
            first_page.click()
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            final_url = driver.current_url.replace('cd=1&', '')
            driver.get(final_url)

    # Клик по 0, 0 на случай если авито показывает pop up
    actions = ActionChains(driver)
    actions.move_by_offset(0, 0).click().perform()

    if 'avtomobili' in cars_url:
        cars_links = page_html(driver)
    else:
        cars.extend(parse_pages(driver))

    # Пагинация
    # Следующая страница
    try:
        next_page = driver.find_element(By.CSS_SELECTOR, "li[class*='styles-module-listItem_arrow_next']")
    except NoSuchElementException:
        next_page = False

    # Другие города
    try:
        other_cities = driver.find_element(By.CSS_SELECTOR, 'div[class*="items-extraTitle"]')
    except NoSuchElementException:
        other_cities = False

    while next_page and not other_cities:
        next_page.click()
        random_wait(RANDOM_MIN, RANDOM_MAX)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        if 'avtomobili' in cars_url:
            cars_links += page_html(driver)
        else:
            cars.extend(parse_pages(driver))

        try:
            next_page = driver.find_element(By.CSS_SELECTOR, "li[class*='styles-module-listItem_arrow_next']")
        except NoSuchElementException:
            next_page = False
        else:
            try:
                next_page_class = next_page.find_element(By.TAG_NAME, 'span').get_attribute('class')
            except NoSuchElementException:
                pass
            else:
                if 'styles-module-item_disabled' in next_page_class:
                    next_page = False
        try:
            other_cities = driver.find_element(By.CSS_SELECTOR, 'div[class*="items-extraTitle"]')
        except NoSuchElementException:
            other_cities = False

    return cars


def parse_ads(driver, cars_links):
    # Парсинг объявлений
    wait = WebDriverWait(driver, 360)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    cars = []
    len_cars_links = len(cars_links)
    for i, car_link in enumerate(cars_links):
        logging.info(f'Объявление {i + 1:4} из {len_cars_links}, {car_link}')

        random_wait(RANDOM_MIN, RANDOM_MAX)
        driver.get(car_link)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='index-logo']")))

        html = driver.page_source
        # response = requests.get(car_link)
        # if response.status_code == 404:
        #     continue
        # else:
        #     soup = BeautifulSoup(response.content, "html.parser")
        #     car_element = soup.find("body")
        #     cars.append(car_data(car_element, car_link))
        #     random_wait(3.0, 4.0)

        # 404
        try:
            driver.find_element(By.XPATH, "//h1[contains(text(), 'Такой страницы нe')]")
        except NoSuchElementException:
            # Если объявление сняли
            try:
                driver.find_element(By.XPATH, "//span[contains(text(), 'Объявление снято с публикации')]")
            except NoSuchElementException:
                soup = BeautifulSoup(html, "html.parser")
                car_element = soup.find("body")
                cars.append(car_data(car_element, car_link))
                # random_wait(3.0, 4.0)
            else:
                continue
        else:
            continue
    return cars


def parse_pages(driver):
    # Парсинг страниц объявлений (первоначально писал под коммерческие, возможно для других нужно переписать)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    ads = soup.select('div[data-marker="item"]')
    cars = []

    for ad in ads:
        title = ad.select_one('h3[itemprop="name"]').text.split(',')
        mark_model = title[0]
        try:
            tech_params = ad.select_one('p[data-marker="item-specific-params"]').text
        except AttributeError:
            tech_params = ''
        if 'моточас' in tech_params:
            # писал по примеру: 1 моточас, ковш 0.9 м3,экспл. масса 21.4 т
            try:
                modification = tech_params.split(',')[1]
            except IndexError:  # если только моточас без остального текста
                modification = ''
        else:
            modification = tech_params
        modification = modification.lower()

        year = title[-1]

        try:
            dealer_name = ad.select_one('div[class*="iva-item-sellerInfo"] p').text
        except AttributeError:
            dealer_name = ''

        # Цены
        price = ad.select_one('p[data-marker="item-price"]').text
        price_with_discount = re.sub(r'\D', '', price)
        price_no_discount = price_with_discount
        with_nds = 'да' if 'с НДС' in price else 'нет'

        if 'моточас' in tech_params:
            condition = tech_params.split(',')[0]
        else:
            condition = 'новый'

        try:
            badge = ad.select_one('span[class*="SnippetBadge-title-oSImJ"]').text
            if 'В наличии' in badge:
                in_stock = 'В наличии'
            else:
                in_stock = badge
        except AttributeError:
            in_stock = 'На заказ'

        services = ''
        tags = ''

        link_element = ad.select_one('a[itemprop="url"]')
        link = f"https://www.avito.ru/{link_element['href']}"

        start = int(link_element['title'].find('»')) + 2
        photos = re.sub(r'\D', '', link_element['title'][start:])

        cars.append({
            "mark_model": mark_model,
            "complectation": '',
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
        })

    return cars
