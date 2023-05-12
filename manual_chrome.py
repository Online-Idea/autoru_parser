# Для дебага
import time

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
URL = "https://agency.auto.ru/dashboard/"
options = uc.ChromeOptions()
prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
options.add_experimental_option("prefs", prefs)
driver = uc.Chrome(options=options)
driver.get(URL)
# Клик по 0, 0 на случай если авто.ру показывает pop up
actions = ActionChains(driver)
actions.move_by_offset(0, 0).click().perform()
dealer_url = 'https://auto.ru/diler-oficialniy/cars/all/interavtotim_cheryexeed_volhonskiy_spb/'
driver.get(dealer_url)
# Пагинация
try:
    next_page_btn = driver.find_element(By.CLASS_NAME, "ListingPagination__next")
    if len(next_page_btn) > 0:
        is_multi_page = True
    else:
        is_multi_page = False
except NoSuchElementException:
    is_multi_page = False

if is_multi_page:
    pages = driver.find_element(By.CLASS_NAME, "ListingPagination__pages")
    pages = pages.find_elements(By.CLASS_NAME, "ListingPagination__page")
    for page in pages[2:]:
        page.click()
        time.sleep(5)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("div", class_="ListingItem")







password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
sign_in_btn = driver.find_element(By.XPATH, "//span[text()='Войти']")
sign_in_btn.click()
driver.get("https://agency.auto.ru/price-report/?client_id=51895")
geo = driver.find_element(By.ID, "price_report_geoselect")
geo.click()
current_geo_btn = driver.find_element(By.CLASS_NAME, "GeoSelectPopupRegion")
current_geo_btn.click()
geo_form = driver.find_element(By.CSS_SELECTOR, "div.RichInput.GeoSelectPopup")
geo_input = geo_form.find_element(By.TAG_NAME, "input")
geo_input.send_keys("Санкт-Петербург")
geo_suggest = driver.find_element(By.XPATH, "//div[@class='GeoSelectPopup__suggest-item-region' and text()='Санкт-Петербург']")
geo_suggest.click()
geo_save = geo_form.find_element(By.XPATH, "//span[@class='Button__text' and text()='Сохранить']")
geo_save.click()
actions = ActionChains(driver)
actions.move_by_offset(0, 0).click().perform()
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")
rows = soup.find_all('div', attrs={'class': 'PriceReportTableRow__info'})
# rows = soup.find_all("div", class_="PriceReportTableRow PriceReport__tableRow")
for row in rows:
    print(row.find("div", class_="PriceReportTableRow__title").text)
competition_filter = driver.find_element(By.CLASS_NAME, "PriceReportMarketFilter")
competition_filter.click()
competition_salons = driver.find_elements(By.CLASS_NAME, "PriceReportMarketFilter__title")