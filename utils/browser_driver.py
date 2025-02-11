from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def browser_driver():
    """
    Создаёт драйвер браузера
    @return:
    """
    service = Service()
    options = uc.ChromeOptions()
    # Отключаю окно сохранения пароля
    prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
    options.add_experimental_option("prefs", prefs)

    # driver = uc.Chrome(driver_executable_path=ChromeDriverManager().install(), options=options)
    driver = webdriver.Chrome(options=options, service=service)
    # driver = uc.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 120)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    return driver
