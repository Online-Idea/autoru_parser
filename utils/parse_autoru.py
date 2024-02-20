import json
import logging
import re
from typing import Union

from bs4 import BeautifulSoup
from bs4.element import PageElement, ResultSet
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from undetected_chromedriver import Chrome, WebElement

from utils.captcha import check_captcha

from utils.captcha import is_captcha

from utils.email_sender import send_email
from utils.geo_changer import change_geo
from utils.random_wait import random_wait


def authorize_autoru(driver: Chrome, login: str, password: str, business: bool):
    """
    Авторизация на авто.ру
    @param driver: driver браузера
    @param login: логин
    @param password: пароль
    @param business: если нужно ходить по cabinet.auto.ru или agency.auto.ru то авторизация чуть другая и нужно
                     передавать business=True
    """
    wait = WebDriverWait(driver, 120)
    if not business:
        driver.get('https://auth.auto.ru/login/?r=https%3A%2F%2Fauto.ru%2F')
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        login_input = 'login'
    else:
        driver.get('https://cabinet.auto.ru')
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        login_input = 'email'

    random_wait()
    login_input = driver.find_element(By.NAME, login_input)
    login_input.send_keys(login)
    login_input.send_keys(Keys.ENTER)

    random_wait()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.send_keys(password)
    password_input.send_keys(Keys.ENTER)
    random_wait()


def page_html(driver: Chrome) -> Union[ResultSet, None]:
    """
    Находит все элементы автомобилей
    @param driver: driver браузера
    @return: элементы bs4 с автомобилями
    """
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    if 'cabinet' in driver.current_url or 'agency' in driver.current_url:
        return soup.find_all("div", class_="Listing__item")

    current_region = soup.find("div", class_="ListingCars_outputType_list")
    try:
        return current_region.find_all("div", class_="ListingItem")
    except AttributeError:
        return


def car_data(car: PageElement, commercial: bool = False) -> dict:
    """
    Собирает данные одного автомобиля
    @param car: элемент от BeautifulSoup
    @param commercial: для коммерческих автомобилей
    @return: словарь с данными автомобиля
    """
    link = car.find('a', class_='ListingItemTitle__link')['href']
    if 'new' in link:  # Комплектация только у новых
        complectation = car.select_one('div.ListingItem__summary > div > div:nth-child(2) > div:nth-child(2)').text
    else:
        complectation = ''

    # Инфо об автомобиле
    mark_model = car.find('a', class_='ListingItemTitle__link').text
    if not commercial:
        engine = car.select_one('div.ListingItem__summary > div > div:nth-child(1) > div:nth-child(1)').text
        transmission = car.select_one('div.ListingItem__summary > div > div:nth-child(1) > div:nth-child(2)').text
        drive = car.select_one('div.ListingItem__summary > div > div:nth-child(2) > div:nth-child(1)').text
        body = car.select_one('div.ListingItem__summary > div > div:nth-child(1) > div:nth-child(3)').text
        modification = '/'.join([body, engine, transmission, drive]).replace('/', ' / ').lower()
    else:
        tech_specs = car.find('div', class_='ListingItemTechSummaryDesktop__column')
        cells = tech_specs.find_all('div', class_='ListingItemTechSummaryDesktop__cell')
        modification = ' / '.join([cell.text for cell in cells])
        print(f'{modification=}')
    year = car.find('div', class_='ListingItem__year').text

    # Цены
    prices = car.find_all('div', class_='ListingItem__price')
    price_with_discount = prices[0].text
    price_no_discount = prices[1].text if len(prices) > 1 else prices[0].text
    # Цена с НДС
    try:
        car.find('div', class_='ListingItem__withNds').text
    except NoSuchElementException:
        with_nds = 'нет'
    except AttributeError:
        with_nds = 'нет'
    else:
        with_nds = 'да'

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
        services = str(car.find('div', class_='ListingItem__placeBlock'))
        services_list = []
        if any(service in services for service in
               ['IconSvg_vas-premium', 'IconSvg_vas-icon-top-small', 'IconSvg_name_SvgVasIconTopSmall']):
            services_list.append('премиум')
        if any(service in services for service in
               ['IconSvg_vas-icon-fresh', 'IconSvg_name_SvgVasIconFresh', 'MetroListPlace__content ']):
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


def parse_autoru_mark(cars_url: str, driver: Chrome, region: str = None) -> list[dict]:
    """
    Здесь начинаю, собираю модели марки и по каждой отдельно парсю
    @param cars_url: ссылка на страницу дилера
    @param driver: driver браузера
    @param region: регион
    @return: лист словарей с данными автомобилей
    """
    cars = []

    driver.get(cars_url)
    check_captcha(driver)

    if is_captcha(driver):
        logging.info('CAPTCHA появилась')
        send_email('evgen0nlin3@gmail.com', 'CAPTCHA появилась', 'Captcha')

    WebDriverWait(driver, 86400).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Header__secondLine")))

    # Клик по 0, 0 на случай если авто.ру показывает pop up
    actions = ActionChains(driver)
    actions.move_by_offset(0, 0).click().perform()

    # Меняю регион
    if region:
        change_geo(driver, region)
        WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Header__secondLine")))

    # Собираю по каждой модели отдельно
    try:
        all_models = driver.find_element(By.CLASS_NAME, 'ListingPopularMMM__expandLink')
        if 'Все модели' in all_models.text:
            all_models.click()
    except NoSuchElementException:
        pass
    models_elements = driver.find_elements(By.CLASS_NAME, 'ListingPopularMMM__itemName')
    models_links = [e.get_attribute('href') for e in models_elements]
    models_links = [f'{link}?output_type=list' if '?' not in link else f'{link}&output_type=list' for link in
                    models_links]

    if models_links:  # По моделям
        for link in models_links:
            logging.info(link)
            cars.extend(parse_autoru_model(link, driver))
            random_wait()
    else:  # Если нет моделей
        cars.extend(parse_autoru_model(cars_url, driver))

    return cars


def parse_autoru_model(cars_url: str, driver: Chrome) -> list[dict]:
    """
    Парсит страницу дилера
    @param cars_url: ссылка на страницу дилера
    @param driver: driver браузера
    @return: лист словарей с данными автомобилей
    """
    cars = []

    driver.get(cars_url)

    # Проверяю если коммерческие автомобили
    category = cars_url.split('/')[4]
    if category != 'cars':
        commercial = True
    else:
        commercial = False

    # Пагинация
    total_pages = ''
    next_page = next_page_check(driver)
    if next_page:
        total_pages = driver.find_elements(By.CLASS_NAME, 'ListingPagination__page')
        total_pages = list(total_pages)[-1].text
        current_page = 1
        logging.info(f'Страница {current_page:3} из {total_pages:3}')

    # Первая страница
    rows = page_html(driver)
    if rows:
        for row in rows:
            cars.append(car_data(row, commercial=commercial))
    else:
        return []

    total_ads = driver.find_element(By.CLASS_NAME, 'ButtonWithLoader__content').text
    total_ads = re.findall(r'\d+', total_ads)
    total_ads = ''.join(total_ads)
    logging.info(f'Всего объявлений: {total_ads}')

    # Остальные страницы
    while next_page:
        try:
            next_page.click()
        except:  # Пробую на любой ошибке при переходе на другую страницу просто обновлять страницу и пробовать снова
            driver.refresh()
            next_page = next_page_check(driver)
            next_page.click()

        current_page += 1
        logging.info(f'Страница {current_page:3} из {total_pages:3}')
        random_wait()
        WebDriverWait(driver, 86400).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'ListingCars_outputType_list')))

        rows = page_html(driver)
        for row in rows:
            cars.append(car_data(row, commercial=commercial))

        # Если какой-нибудь popup появляется
        actions = ActionChains(driver)
        actions.move_by_offset(0, 0).click().perform()

        next_page = next_page_check(driver)
        next_page_class = next_page.get_attribute('class')
        if 'Button_disabled' in next_page_class:
            next_page = False

    return cars


def next_page_check(driver: Chrome) -> Union[WebElement, bool]:
    """
    Проверяет есть ли элемент следующей страницы
    @param driver: driver браузера
    @return: элемент-кнопка следующей страницы либо False
    """
    try:
        next_page = driver.find_element(By.CLASS_NAME, "ListingPagination__next")
    except NoSuchElementException:
        next_page = False
    return next_page


def collect_links(driver: Chrome, link: str) -> list:
    """
    Собирает ссылки на объявления
    @param driver: driver браузера
    @param link: ссылка на список объявлений
    @return: список ссылок на объявления
    """
    # TODO сейчас делаю только для объявлений из кабинета. В дальнейшем сделать со страницы дилера и с выдачи
    if 'cabinet.auto.ru' in link or 'agency.auto.ru' in link:
        ad_link_class = 'OfferSnippetRoyalSpec__title'
    elif 'diler' in link:
        ad_link_class = 'ListingItemTitle__link'
    else:
        raise ValueError(f'Сбор по ссылке:\n{link}\nпока не поддерживается')

    driver.get(link)

    random_wait()
    WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    # WebDriverWait(driver, 86400).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.Header__secondLine")))

    # Если какой-нибудь popup появляется
    actions = ActionChains(driver)
    actions.move_by_offset(0, 0).click().perform()

    next_page = next_page_check(driver)

    links = []
    # Первая страница
    rows = page_html(driver)
    if rows:
        for row in rows:
            ad_link = row.find('a', class_=ad_link_class)['href']
            links.append(ad_link)

    # Остальные страницы
    while next_page:
        next_page.click()
        random_wait()
        WebDriverWait(driver, 86400).until(EC.presence_of_element_located((By.CLASS_NAME, 'Listing__items')))

        rows = page_html(driver)
        for row in rows:
            ad_link = row.find('a', class_=ad_link_class)['href']
            links.append(ad_link)

        next_page = next_page_check(driver)
        next_page_class = next_page.get_attribute('class')
        if 'Button_disabled' in next_page_class:
            next_page = False

    return links


def parse_autoru_ad(driver: Chrome, ad_link: str):
    """
    Парсит одно объявление полностью
    @param driver: driver браузера
    @param ad_link: ссылка на объявление
    @return: словарь с данными автомобиля
    """
    driver.get(ad_link)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    car = soup.find(id='sale-data-attributes')['data-bem']
    car = json.loads(car)['sale-data-attributes']

    mark = car['markName']
    model = car['modelName']
    complectation = soup.find('span', class_='CardInfoGroupedRow__cellValue_complectationName').text
    price = car['price']
    # with_nds =  # Пока нет возможности

    # Технические характеристики
    body_label = soup.select_one('div.CardInfoGroupedRow__cellTitle:-soup-contains("Кузов")')
    body = body_label.find_next_sibling('a', 'CardInfoGroupedRow__cellValue').text
    modification_label = soup.select_one('div.CardInfoGroupedRow__cellTitle:-soup-contains("Двигатель")')
    modification = modification_label.find_next_sibling('div').text
    if 'электро' in modification:
        volume = ''
    else:
        volume = float(modification.split(' ')[0])
    power = car['power']
    transmission = car['transmission']
    engine_type = car['engine-type']
    drive_label = soup.select_one('div.CardInfoGroupedRow__cellTitle:-soup-contains("Привод")')
    drive = drive_label.find_next_sibling('div', 'CardInfoGroupedRow__cellValue').text
    year = car['year']

    color_label = soup.select_one('div.CardInfoGroupedRow__cellTitle:-soup-contains("Цвет")')
    color = color_label.find_next_sibling('a', 'CardInfoGroupedRow__cellValue').text

    description = soup.find('div', class_='CardDescriptionHTML').text

    vin_label = soup.select_one('div.CardInfoGroupedRow__cellTitle:-soup-contains("VIN")')
    vin = vin_label.find_next_sibling('div', 'CardInfoGroupedRow__cellValue').text

    # Скидки
    def int_from_next_sibling(label_element):
        element = label_element.find_next_sibling('div', 'CardDiscountList__itemValue').text
        return int(re.sub(r'\D', '', element))

    trade_in_label = soup.select_one('div.CardDiscountList__itemName:-soup-contains("В трейд-ин")')
    credit_label = soup.select_one('div.CardDiscountList__itemName:-soup-contains("В кредит")')
    insurance_label = soup.select_one('div.CardDiscountList__itemName:-soup-contains("С каско")')
    max_discount_label = soup.select_one('div.CardDiscountList__itemName:-soup-contains("Максимальная")')
    trade_in = int_from_next_sibling(trade_in_label) if trade_in_label else None
    credit = int_from_next_sibling(credit_label) if credit_label else None
    insurance = int_from_next_sibling(insurance_label) if insurance_label else None
    max_discount = int_from_next_sibling(max_discount_label) if max_discount_label else None

    if 'new' in ad_link:
        condition = 'новая'
    elif 'used' in ad_link:
        condition = 'с пробегом'
    else:
        condition = ''

    run_label = soup.select_one('div.CardInfoRow__cell:-soup-contains("Пробег")')
    run = int_from_next_sibling(run_label) if run_label else ''

    tags_elements = soup.find_all('div', 'CardDescription__badgesItem')
    tags = '|'.join([tag.text for tag in tags_elements])

    # TODO ссылка на ютуб где-то внутри iframe, нужно через Selenium переключаться на него и уже его html давать bs4
    # video_url = soup.find('link', rel='canonical')['href']
    in_stock = soup.find('div', 'CardImageGallery__badges').text

    return {
        'mark': mark,
        'model': model,
        'complectation': complectation,
        'price': price,
        'body': body,
        'volume': volume,
        'power': power,
        'transmission': transmission,
        'engine_type': engine_type,
        'drive': drive,
        'year': year,
        'color': color,
        'description': description,
        'vin': vin,
        'trade_in': trade_in,
        'credit': credit,
        'insurance': insurance,
        'max_discount': max_discount,
        'condition': condition,
        'run': run,
        'tags': tags,
        # 'video_url': video_url,
        'in_stock': in_stock
    }
