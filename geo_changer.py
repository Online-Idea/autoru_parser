from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome

from random_wait import random_wait


def change_geo(driver: Chrome, region: str) -> None:
    """
    Меняет регион авто.ру
    @param driver: driver браузера
    @param region: регион на который нужно сменить
    """
    current_geo = driver.find_element(By.CSS_SELECTOR, "span[class*='GeoSelect__titleShrinker']")
    current_geo = current_geo.get_attribute('title')

    if current_geo != region:
        geo = driver.find_element(By.CLASS_NAME, "IconSvg_geo")
        geo.click()
        random_wait()
        current_geo_btn = driver.find_element(By.CLASS_NAME, "GeoSelectPopupRegion")
        current_geo_btn.click()
        random_wait()
        geo_form = driver.find_element(By.CSS_SELECTOR, "div.RichInput.GeoSelectPopup")
        geo_input = geo_form.find_element(By.TAG_NAME, "input")
        geo_input.send_keys(region)
        random_wait()
        geo_suggest = driver.find_element(By.XPATH, f"//div[@class='GeoSelectPopup__suggest-item-region' and \
                                                      text()='{region}']")
        geo_suggest.click()
        random_wait()
        geo_save = geo_form.find_element(By.XPATH, "//span[@class='Button__text' and text()='Сохранить']")
        geo_save.click()
