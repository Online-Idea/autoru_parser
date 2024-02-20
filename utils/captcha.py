from datetime import datetime
from typing import Union, Dict

from dotenv import load_dotenv
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from twocaptcha import TwoCaptcha
import os
import sys
import logging
from time import sleep
from bs4 import BeautifulSoup
from io import BytesIO
import requests
from PIL import Image




def is_captcha(driver: WebDriver) -> bool:
    """
    Проверяет появилась ли капча. Смотрит по тегу title
    @param driver:
    @return: True если капча
    """
    title = driver.title.lower()
    return 'капча' in title or 'captcha' in title


def check_captcha(driver: WebDriver) -> None:
    """
    Определяет тип капчи и вызывает соответствующую функцию для ее решения
    """
    while is_captcha(driver):  # Цикл, пока капча присутствует на странице
        logging.info('CHECK CAPTCHA!')
        sleep(1)
        result = None  # Инициализация переменной результата
        if "Нажмите, чтобы продолжить" in driver.page_source:
            logging.debug('Simple CAPTCHA!')
            result = click_captcha(driver)  # Вызов функции click_captcha для решения простой капчи
        elif "Нажмите в таком порядке" in driver.page_source:
            logging.info('Coordinates CAPTCHA!')
            result = solve_captcha(driver)  # Вызов функции solve_captcha для решения капчи с координатами
        else:
            # Если не удалось определить тип CAPTCHA
            logging.info('Не удалось определить тип CAPTCHA')
            save_screenshot(driver)
        # Если капча не удалось решить, обновляем страницу
        if is_captcha(driver) and (result is None or not result['status success']):
            logging.info('Обновление страницы с CAPTCHA')
            driver.refresh()


def load_image(url: str) -> Union[Image.Image, Dict[str, bool]]:
    """
    Загрузка изображения по URL.
    """
    try:
        response = requests.get(url)  # Отправка GET на URL картинки
        response.raise_for_status()  # Проверка успешности запроса
        image = Image.open(
            BytesIO(response.content))  # Открытие изображения из байтового потока, полученного из ответа на запрос
        return image
    except Exception as e:
        logging.error(f"Error loading image: {e}")
        return {'status success': False}


def combine_images(image1: Image, image2: Image) -> Union[Image, Dict[str, bool]]:
    """
    Слияние двух изображений.
    """
    if not image1 or not image2:  # Если одно изображение отсутствует
        logging.warning(f"Failed to combine images.")
        return {'status success': False}

    # Получение размеров
    width1, height1 = image1.size
    width2, height2 = image2.size

    max_width = width1  # Максимальная ширина равна ширине первой капчи

    if width2 > max_width:  # Если ширина второго изображения больше максимальной ширины
        new_height = int(max_width * height2 / width2)  # Рассчитываем новую высоту для второго изображения
        image2 = image2.resize((max_width, new_height))  # Изменяем размер второго изображения

    new_height = height1 + new_height  # Рассчитываем высоту нового изображения

    new_image = Image.new('RGBA', (max_width, new_height), (255, 255, 255, 255))  # Создаем новое изображение

    new_image.paste(image1, (0, 0))  # Вставляем первое изображение в верхний левый угол нового изображения
    new_image.paste(image2, (0, height1), mask=image2)  # Вставляем второе изображение под первым, с учетом прозрачности

    return new_image  # Возвращаем новое изображение


def solve_captcha(driver: WebDriver) -> Union[Dict[str, bool], None]:
    """
    Решение капчи.
    """
    html_page = driver.page_source
    soup = BeautifulSoup(html_page, 'html.parser')
    img_tag = soup.find('img')

    captcha_image_url = img_tag['src']  # Получение URL изображения капчи
    try:
        response = requests.head(captcha_image_url, allow_redirects=True)  # Отправка HEAD-запроса по URL изображения
        url_image = response.url  # Получение реального URL изображения после редиректа
        url_task = url_image.replace("data=img", "data=task&service=autoru")  # Формирование URL для задачи капчи
    except requests.exceptions.RequestException as e:
        logging.error(f"Error: {e}")
        return {'status success': False}
        # sys.exit(e)  # Выход из программы в случае ошибки

    image1 = load_image(url_image)  # Загрузка изображения капчи
    image2 = load_image(url_task).convert("RGBA")  # Загрузка изображения с заданием капчи и преобразование его в RGBA

    new_image = combine_images(image1, image2)  # Объединение изображений
    if not new_image:
        return {'status success': False}

    new_image.save('captcha.png')  # Сохранение объединенного изображения в файл
    logging.info(f"Images combined and saved as 'captcha.png'")

    load_dotenv()
    api_key = os.getenv('APIKEY_2CAPTCHA')
    solver = TwoCaptcha(api_key, defaultTimeout=120, pollingInterval=5)

    try:
        # Получение координат для кликов с rucaptcha
        logging.info(f'Waiting for response from "Rucaptcha" service....')
        result = solver.coordinates('captcha.png', lang='en')
        if 'code' not in result or 'ERROR_CAPTCHA_UNSOLVABLE' == result:
            logging.error(f'Failed: {result}')
            return {'status success': False}

        action = ActionChains(driver)  # ActionChains для управления мышью на веб-страницей
        captcha_image = driver.find_element(By.CSS_SELECTOR,
                                            ".AdvancedCaptcha-ImageWrapper")  # Контейнер с изображением капчи

        pairs = result['code'].split(':')[1]  # Разбиваем координаты на отдельные пары x и y
        pairs = pairs.split(';')
        for idx, pair in enumerate(pairs):
            x, y = pair.split(',')
            x_coordinate = int(x[2:])
            y_coordinate = int(y[2:])

            # Сбрасываем положение мыши в верхний левый угол капчи после каждого клика
            action.move_to_element_with_offset(captcha_image, -150, -90).perform()

            # Смещаем координаты клика относительно текущего положения мыши
            action.move_by_offset(x_coordinate, y_coordinate).click().perform()

            sleep(.5)  # Пауза между кликами
        print(4)
        # Находим и нажимаем на кнопку отправки капчи по атрибуту data-testid
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='submit']"))
        )
        submit_button.click()

        logging.info(f'Captcha has been sent!')
        return {'status success': True}
    except Exception as e:
        logging.error(f"Error: {e}")
        return {'status success': False}
        # sys.exit(e)  # Выход из программы в случае ошибки


def click_captcha(driver: WebDriver) -> Dict[str, bool]:
    """
    Прожимает простю капчу
    @param driver:
    @return:
    """
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'js-button')))

        # Находим чекбокс и кликаем по нему
        checkbox = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'js-button')))
        checkbox.click()
        logging.debug(f'Captcha "simple click" successfully!')
        return {'status success': True}
    except Exception as e:
        logging.error(f"Error: {e}")
        return {'status success': False}


def save_screenshot(driver: WebDriver) -> None:
    """
    Сохраняет скриншот страницы.
    """
    try:
        # Создаем папку для сохранения скриншотов, если ее еще нет
        if not os.path.exists('captcha_failed'):
            os.makedirs('captcha_failed')
        # Получаем текущую дату и время
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Формируем имя файла для скриншота
        screenshot_name = f"captcha_failed/captcha_{now}.png"
        # Сохраняем скриншот страницы
        driver.save_screenshot(screenshot_name)
        logging.info(f"Скриншот страницы сохранен: {screenshot_name}")
    except Exception as e:
        logging.error(f"Error saving screenshot: {e}")


if __name__ == "__main__":
    pass
