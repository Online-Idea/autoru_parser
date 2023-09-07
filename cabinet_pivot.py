import logging
import os
import time

from geo_changer import change_geo
from result_processing import data_work, format_work
from random_wait import random_wait

import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager


def clean(s):
    """
    Текст в число
    """
    return int(s.replace('\xa0', '')) if s else s


def table_row(dealer, row, our_cars=False):
    """
    Обрабатывает строку таблицы авто.ру
    :param dealer: имя дилера
    :param row: строка из таблицы как элемент bs4
    :param our_cars: True если нужно собрать данные нашего дилера, False если нужны данные конкурента
    :return: словарь с данными автомобиля
    """
    # Информация об автомобиле
    mark_model = row.find("div", class_="PriceReportTableRow__title").text
    complectation = row.find("div", class_="PriceReport__tableCell PriceReport__tableCell_complectation").text
    modification = row.find("div", class_="PriceReportTableRow__titleNote").text
    modification = modification.replace('\u2009', ' ')
    modification = modification.split(" / ")[:2]
    modification = " / ".join(modification)
    year = int(row.find("div", class_="PriceReport__tableCell PriceReport__tableCell_year").text)

    # Блок со складом и ценами
    warehouse = row.find_all("div", class_="PriceReport__tableCell PriceReport__tableCell_availability")
    warehouse_competitor = warehouse[1]
    link = warehouse_competitor.find("a", class_="Link HoveredTooltip__trigger").get("href")
    # Наши данные
    if our_cars:
        warehouse_ours = warehouse[0].text
        stock, for_order = warehouse_ours.split("/")
    # Конкурент
    else:
        stock, for_order = warehouse_competitor.text.split("/")
        # Здесь перехожу на блок конкурента
        row = row.find("div", class_="PriceReport__tableCol PriceReport__tableCol_filter")

    return {
        "mark_model": mark_model,
        "complectation": complectation,
        "modification": modification,
        "year": year,
        "dealer": dealer,
        "min_price_with_discount": clean(row.find("span", class_="PriceReportTableRow__minPriceDiscount").text),
        "min_price_no_discount": clean(row.find("span", class_="PriceReportTableRow__minPrice").text),
        "max_price": clean(row.find("span", class_="PriceReportTableRow__maxPrice").text),
        "stock": int(stock),
        "for_order": int(for_order),
        "link": link,
    }


def cabinet_pivot():
    """
    Полный цикл парсинга сводной таблицы с кабинета авто.ру
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    current_dealer = 'РОЛЬФ Витебский EXEED'
    current_dealer_id = 51895
    region = 'Санкт-Петербург'
    # current_dealer = 'Fresh Auto Chery Москва Левобережный'
    # current_dealer_id = 50793
    # region = 'Москва'

    options = uc.ChromeOptions()
    # Отключаю окно сохранения пароля
    prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(driver_executable_path=ChromeDriverManager().install(), options=options)

    driver.get('https://agency.auto.ru/dashboard/')
    wait = WebDriverWait(driver, 120)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Авторизация
    random_wait()
    login_input = driver.find_element(By.NAME, "login")
    login_input.send_keys(os.environ["login"])
    login_input.send_keys(Keys.ENTER)

    random_wait()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.send_keys(os.environ["password"])
    sign_in_btn = driver.find_element(By.XPATH, "//span[text()='Войти']")
    sign_in_btn.click()

    # Иду по клиентам
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href='/clients/']")))
    driver.get(f"https://agency.auto.ru/price-report/?client_id={current_dealer_id}")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "PriceReportMarketFilter")))
    random_wait()

    # Клик по 0, 0 на случай если авто.ру показывает pop up
    actions = ActionChains(driver)
    actions.move_by_offset(0, 0).click().perform()

    # Меняю регион
    change_geo(driver, region)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "PriceReportMarketFilter")))

    # Выбор конкурентов
    competition_filter = driver.find_element(By.CLASS_NAME, "PriceReportMarketFilter")
    competition_filter.click()
    competition_salons = driver.find_elements(By.CLASS_NAME, "PriceReportMarketFilter__title")
    dealer_names = [dealer.text for dealer in competition_salons if dealer.text]

    cars = []

    # Парсинг страницы
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    # rows = soup.select("div.PriceReportTableRow.PriceReport__tableRow")
    rows = soup.find_all("div", class_="PriceReportTableRow__info")
    for row in rows:
        cars.append(table_row(current_dealer, row, our_cars=True))

    # Данные конкурентов
    for dealer in dealer_names:
        logging.info(f"Собираю данные {dealer}")
        if dealer in ['Рынок', current_dealer]:
            continue
        competition_filter.click()
        salon_in_filter = driver.find_element(By.XPATH, f"//div[text()='{dealer}']")
        salon_in_filter.click()
        random_wait()

        # Парсинг страницы
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        # rows = soup.select("div.PriceReportTableRow.PriceReport__tableRow")
        rows = soup.find_all("div", class_="PriceReportTableRow__info")
        for row in rows:
            cars.append(table_row(dealer, row))

        # Убираю курсор в угол чтобы не наводился на лишние элементы, которые могут перекрыть фильтр
        actions.move_by_offset(0, 0).click().perform()

    logging.info("Парсинг закончен")
    time.sleep(2)
    driver.quit()

    # Обрабатываю результат
    xlsx_file = data_work(cars, current_dealer)
    logging.info("Pandas закончил")

    # Форматирую результат
    format_work(xlsx_file, current_dealer)

    logging.info("Файл с результатом готов")
