import logging
import re
import time
from typing import List, Dict

import bs4.css
import requests
from bs4 import BeautifulSoup, PageElement
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome

from utils.functions import extract_digits_regex, close_popup
from utils.random_wait import random_wait

RANDOM_MIN = 3
RANDOM_MAX = 4


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
            mark_model = car.find('h1', itemprop='name').text \
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


def parse_avito(cars_url: str, driver: Chrome, mark: str, oils: bool = False) -> list[dict]:
    """
    Парсит авито
    @param cars_url: ссылка на страницу с объявлениями
    @param driver: driver браузера
    @param mark:
    @param oils: если нужно парсить объявления по моторным маслам
    @return: лист словарей с данными автомобилей
    """
    # cars_url += '?localPriority' if 'localPriority' not in cars_url else ''
    if 'localPriority' not in cars_url:
        if '?' in cars_url:
            cars_url += '&localPriority=1'
        else:
            cars_url += '?localPriority=1'

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

    # Если какой-нибудь popup появляется
    close_popup(driver)

    # Если количество объявлений больше 5000 значит надо дробить на марки и/или модели
    ads_count = total_ads_count(driver)

    cars_links = None

    if ads_count > 5000:
        show_all_marks(driver)
        links = get_sub_categories(driver)
        for link in links:
            cars.extend(parse_avito(link, driver, mark))

    else:
        # Собираю ссылки на легковые объявления, чтобы дальше парсить с заходом в каждое объявление
        if 'avtomobili' in cars_url:
            cars_links = page_html(driver)
        elif oils:
            cars.extend(parse_pages_for_oils(driver))
        # Парсинг коммерческих автомобилей со страницы со списком объявлений
        else:
            cars.extend(parse_pages(driver))

        # Пагинация
        # Следующая страница
        try:
            # TODO попробовать идти на следующую страницу беря ссылку из кнопки следующей страницы вместо клика по этой кнопке
            next_page = driver.find_element(By.CSS_SELECTOR, "li[class*='styles-module-listItem_arrow_next']")
        except NoSuchElementException:
            next_page = False

        # Другие города
        try:
            other_cities = driver.find_element(By.CSS_SELECTOR, 'div[class*="items-extraTitle"]')
        except NoSuchElementException:
            other_cities = False

        while next_page and not other_cities:
            # next_page.click()
            next_page_link = next_page.find_element(By.TAG_NAME, 'a').get_attribute('href')
            if 'localPriority=1' not in next_page_link:
                next_page_link = f'{next_page_link}&localPriority=1'
            driver.get(next_page_link)
            random_wait(RANDOM_MIN, RANDOM_MAX)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            if 'avtomobili' in cars_url:
                cars_links += page_html(driver)
            elif oils:
                cars.extend(parse_pages_for_oils(driver))
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

    if cars_links:
        cars.extend(parse_ads(driver, cars_links))

    return cars


def total_ads_count(driver):
    keep_refreshing = True
    while keep_refreshing:
        try:
            ads_count = driver.find_element(By.CSS_SELECTOR, 'span[data-marker="page-title/count"]').text
        except NoSuchElementException:
            try:
                show_ads_btn = driver.find_element(By.CSS_SELECTOR,
                                                   'button[data-marker="search-filters/submit-button"]')
            except NoSuchElementException:
                # Если на странице нет количества объявлений значит что-то не так, пробую обновить
                logging.info('Нет количества объявлений, обновлю через 30 секунд')
                time.sleep(30)
                driver.refresh()
            else:
                # Если по ссылке вообще нет объявлений то возвращаю 0
                if show_ads_btn.text == 'Показать объявления':
                    ads_count_digits = 0
                    keep_refreshing = False
        else:
            ads_count_digits = int(re.sub(r'\D', '', ads_count))
            keep_refreshing = False
    return ads_count_digits


def get_sub_categories(driver):
    """
    Авито даёт посмотреть максимум 5000 объявлений на запрос (50 объявлений * 100 страниц).
    Если их больше 5000 то нужно дробить на меньшие подзапросы.
    Я это делаю через блок с популярными марками/моделями, собирая ссылки на них и проходя по ним.
    @param driver:
    @return:
    """
    # Ссылки на марки/модели
    categories = driver.find_elements(By.CSS_SELECTOR, 'a[data-marker="popular-rubricator/link"]')
    return [category.get_attribute('href') for category in categories]


def show_all_marks(driver):
    # Кнопка Все которая показывает все марки/модели, её может не быть
    try:
        popular_all_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-marker="popular-rubricator/controls/all"]')
    except NoSuchElementException:
        return
    else:
        popular_all_btn.click()


def parse_ads(driver, cars_links):
    # Парсинг объявлений
    wait = WebDriverWait(driver, 540)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    cars = []
    len_cars_links = len(cars_links)
    for i, car_link in enumerate(cars_links):
        logging.info(f'Объявление {i + 1:4} из {len_cars_links}, {car_link}')

        random_wait(RANDOM_MIN, RANDOM_MAX)
        driver.get(car_link)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='logo']")))

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
        if '404' in driver.title:
            continue
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
    ads = soup.select('div[data-marker="catalog-serp"] div[data-marker="item"]')
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

        # Регион
        # try:
        #     region = ad.select_one('div[class*="geo-root"]').text
        # except AttributeError:
        #     breakpoint()

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
            # "region": region,
        })

    return cars


def parse_pages_for_oils(driver):
    # Парсинг страниц объявлений (первоначально писал под коммерческие, возможно для других нужно переписать)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    ads = soup.select('div[data-marker="item"]')
    oils = []

    for ad in ads:
        title = ad.select_one('h3[itemprop="name"]').text
        try:
            dealer = ad.select_one('div[class*="iva-item-sellerInfo"] p').text
        except AttributeError:
            dealer = ''
        price = ad.select_one('p[data-marker="item-price"]').text
        price = re.sub(r'\D', '', price)
        price = 0 if price == '' else price
        description = ad.select_one('meta[itemprop="description"]')['content']
        geo = ad.select_one('div[class^="geo-root"]').text
        link = ad.select_one('a[itemprop="url"]')['href']
        link = 'https://www.avito.ru' + link

        oils.append({
            'title': title,
            'dealer': dealer,
            'price': price,
            'geo': geo,
            'link': link,
            'description': description,
        })
    return oils


def count_by_mark(driver) -> List[Dict[str, str]]:
    """
    Собирает количество объявлений по маркам
    @param driver:
    @return:
    """
    show_all_marks(driver)
    marks = driver.find_elements(By.CSS_SELECTOR, 'div[data-marker="popular-rubricator/links/row"]')
    result = []
    for mark in marks:
        name = mark.find_element(By.CSS_SELECTOR, 'a[data-marker="popular-rubricator/link"]').text
        count = mark.find_element(By.CSS_SELECTOR, 'span[data-marker="popular-rubricator/count"]').text
        count = extract_digits_regex(count)
        result.append({"mark": name, "count": count})

    return result
