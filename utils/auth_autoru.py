import logging
import os

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By

from utils.random_wait import random_wait


def check_auth_page(driver):
    # if 'Авторизуясь на сайте, я принимаю условия' in driver.page_source:
    if 'auth' in driver.current_url or 'Войдите, чтобы пользоваться сервисом дальше' in driver.page_source:
        auth_autoru(driver)


def auth_autoru(driver):
    """
    Авторизация на авто.ру
    """
    logging.info('Авторизуюсь')
    yandex_id_btn = driver.find_element(By.ID, 'yandex')
    yandex_id_btn.click()
    random_wait()
    yandex_login_input = driver.find_element(By.ID, 'passp-field-login')
    yandex_login_input.send_keys(os.environ['YANDEX_EMAIL'])
    yandex_sign_in_btn = driver.find_element(By.ID, 'passp:sign-in')
    yandex_sign_in_btn.click()
    random_wait()
    yandex_password_input = driver.find_element(By.ID, 'passp-field-passwd')
    yandex_password_input.send_keys(os.environ['YANDEX_PASSWORD'])
    yandex_sign_in_btn2 = driver.find_element(By.ID, 'passp:sign-in')
    yandex_sign_in_btn2.click()
    random_wait()

    # Если предложит входить по лицу или отпечатку пальца
    try:
        driver.find_element(By.CLASS_NAME, 'ScreenIcon_icon_shieldGreyFingerprint')
    except NoSuchElementException:
        pass
    else:
    # if 'Входите по лицу или отпечатку пальца' in driver.page_source:
        not_now_btn = driver.find_element(By.XPATH, '//button[contains(., "сейчас")]')
        not_now_btn.click()
        random_wait()
