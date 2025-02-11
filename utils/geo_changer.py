from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome

from .auth_autoru import check_auth_page
from .captcha import check_captcha
from .random_wait import random_wait


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
        check_captcha(driver)
        check_auth_page(driver)
        current_geo_btn = driver.find_element(By.CLASS_NAME, "GeoSelectPopupRegion")
        current_geo_btn.click()
        random_wait()
        check_captcha(driver)
        check_auth_page(driver)
        geo_form = driver.find_element(By.CSS_SELECTOR, "div.RichInput.GeoSelectPopup")
        geo_input = geo_form.find_element(By.TAG_NAME, "input")
        geo_input.send_keys(region)
        random_wait()
        check_captcha(driver)
        check_auth_page(driver)
        geo_suggest = driver.find_element(By.XPATH, f"//div[@class='GeoSelectPopup__suggest-item-region' and \
                                                      text()='{region}']")
        geo_suggest.click()
        random_wait()
        check_captcha(driver)
        check_auth_page(driver)
        geo_save = geo_form.find_element(By.XPATH, "//span[@class='Button__text' and text()='Сохранить']")
        geo_save.click()
