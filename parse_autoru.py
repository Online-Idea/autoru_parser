import logging
import re
import time

from bs4 import BeautifulSoup
from bs4.element import PageElement, ResultSet
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from undetected_chromedriver import Chrome

from geo_changer import change_geo
from random_wait import random_wait


def page_html(driver: Chrome) -> ResultSet:
    """
    Находит все элементы автомобилей
    @param driver: driver браузера
    @return: элементы bs4 с автомобилями
    """
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    current_region = soup.find("div", class_="ListingCars_outputType_list")
    try:
        return current_region.find_all("div", class_="ListingItem")
    except AttributeError:
        return


def car_data(car: PageElement) -> dict:
    """
    Собирает данные одного автомобиля
    @param car: элемент от BeautifulSoup
    @return: словарь с данными автомобиля
    """
    # Инфо об автомобиле
    mark_model = car.find('a', class_='ListingItemTitle__link').text
    complectation = car.select_one('div.ListingItem__summary > div > div:nth-child(2) > div:nth-child(2)').text
    engine = car.select_one('div.ListingItem__summary > div > div:nth-child(1) > div:nth-child(1)').text
    transmission = car.select_one('div.ListingItem__summary > div > div:nth-child(1) > div:nth-child(2)').text
    drive = car.select_one('div.ListingItem__summary > div > div:nth-child(2) > div:nth-child(1)').text
    body = car.select_one('div.ListingItem__summary > div > div:nth-child(1) > div:nth-child(3)').text
    modification = '/'.join([body, engine, transmission, drive]).replace('/', ' / ').lower()
    year = car.find('div', class_='ListingItem__year').text

    # Цены
    # prices = car.find_all('div', class_='ListingItemPrice__content')
    prices = car.find_all('div', class_='ListingItem__price')
    price_with_discount = prices[0].text
    price_no_discount = prices[1].text if len(prices) > 1 else prices[0].text
    # Цена с НДС
    try:
        car.find('div', class_='ListingItem__withNds').text
    except NoSuchElementException:
        with_nds = False
    except AttributeError:
        with_nds = False
    else:
        with_nds = True

    link = car.find('a', class_='ListingItemTitle__link')['href']
    condition = car.find('div', class_='ListingItem__kmAge').text
    # Для авто с пробегом
    condition = int(re.findall(r'\d+', condition)[0]) if 'км' in condition else condition

    try:
        in_stock = car.find('div', class_='ListingItem__stock').text.replace('\xa0', ' ')
    except AttributeError:
        in_stock = 'В наличии'

    # Имя дилера. Беру из объявления если оно там есть,
    # иначе остаётся имя нашего дилера т.к. это означает что парсим страницу дилера
    try:
        dealer_name = car.find('a', class_='ListingItem__salonName').text
    except AttributeError:
        dealer_name = ''

    # Услуги
    try:
        # services = str(car.find('div', class_='ListingItem__services'))
        services = str(car.find('div', class_='ListingItem__placeBlock'))
        services_list = []
        if any(service in services for service in ['IconSvg_vas-premium', 'IconSvg_vas-icon-top-small', 'IconSvg_name_SvgVasIconTopSmall']):
            services_list.append('премиум')
        if any(service in services for service in ['IconSvg_vas-icon-fresh', 'IconSvg_name_SvgVasIconFresh', 'MetroListPlace__content ']):
            services_list.append('поднятие в поиске')
        services = ' | '.join(services_list)
    except NoSuchElementException:
        services = ''

    # Стикеры
    try:
        tags = car.find_all('div', class_='Badge')
        tags = [tag.text for tag in tags]
        tags = ' | '.join(tags)
    except NoSuchElementException:
        tags = ''

    # Количество фото
    try:
        photos = car.find('div', class_='BrazzersMore__text').text
        photos = re.sub(r'\D+', '', photos)
    except NoSuchElementException:
        photos = len(car.find_all('div', class_='Brazzers__page'))
    except AttributeError:
        photos = len(car.find_all('div', class_='Brazzers__page'))
    finally:
        photos = int(photos)

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


def parse_autoru(cars_url: str, driver: Chrome, region: str = None, first_page=False) -> list[dict]:
    """
    Парсит страницу дилера
    @param cars_url: ссылка на страницу дилера
    @param driver: driver браузера
    @param region: регион
    @param first_page: если нужна только первая страница, для сбора услуг
    @return: лист словарей с данными автомобилей
    """
    cars = []

    driver.get(cars_url)

    WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Header__secondLine")))

    # Клик по 0, 0 на случай если авто.ру показывает pop up
    actions = ActionChains(driver)
    actions.move_by_offset(0, 0).click().perform()

    # Меняю регион
    if region:
        change_geo(driver, region)
        WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Header__secondLine")))

    # Пагинация
    total_pages = ''
    try:
        next_page = driver.find_element(By.CLASS_NAME, "ListingPagination__next")
    except NoSuchElementException:
        next_page = False
    else:
        total_pages = driver.find_elements(By.CLASS_NAME, 'ListingPagination__page')
        total_pages = list(total_pages)[-1].text
        current_page = 1
        logging.info(f'Страница {current_page:3} из {total_pages:3}')

    # У авто.ру лимит на 99 страниц объявлений - в таких случаях собираю по моделям
    if total_pages == '99':
        try:
            all_models = driver.find_element(By.CLASS_NAME, 'ListingPopularMMM__expandLink')
            all_models.click()
        except NoSuchElementException:
            pass
        models_elements = driver.find_elements(By.CLASS_NAME, 'ListingPopularMMM__itemName')
        models_links = [e.get_attribute('href') for e in models_elements]
        models_links = [f'{link}?output_type=list' for link in models_links]
        for link in models_links:
            cars.extend(parse_autoru(link, driver))
        return cars

    # Первая страница
    rows = page_html(driver)
    if rows:
        for row in rows:
            cars.append(car_data(row))
    else:
        return []

    total_ads = driver.find_element(By.CLASS_NAME, 'ButtonWithLoader__content').text
    total_ads = re.findall(r'\d+', total_ads)[0]
    logging.info(f'Всего объявлений: {total_ads}')

    if first_page:
        return cars

    # Остальные страницы
    while next_page:
        next_page.click()
        current_page += 1
        logging.info(f'Страница {current_page:3} из {total_pages:3}')
        random_wait()
        WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.CLASS_NAME, 'ListingCars_outputType_list')))

        rows = page_html(driver)
        for row in rows:
            cars.append(car_data(row))

        next_page = driver.find_element(By.CLASS_NAME, "ListingPagination__next")
        next_page_class = next_page.get_attribute('class')
        if 'Button_disabled' in next_page_class:
            next_page = False

    return cars
