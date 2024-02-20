import logging
from time import sleep

import undetected_chromedriver as uc

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from captcha import check_captcha

# cars_url = "https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1120160415-efbef0f4/"
# cars_url = [
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1120160415-efbef0f4/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121315067-396b88ab/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121315068-99d6724c/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1120389791-b46e2a81/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121875809-13fcaa34/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121799354-926a34bd/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1120835241-973a9448/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121315065-b15fd847/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121636012-5f48ed8b/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121875815-f6f8b5ca/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121518753-977c049e/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121518752-18e29318/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121315055-71c6e026/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199108-780f9013/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199104-4bf48dc6/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199076-a209623d/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199077-a0f0892d/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199075-de7dcc9b/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121886817-2e107bb1/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199105-4a4ee515/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199079-0981671b/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199101-7ddbdd8f/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1121322750-16c66f4b/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199052-dacd13f0/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199097-200ceb33/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199054-a1d01396/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199096-5ce74d02/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199109-6db55d71/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199099-b4afaa45/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199057-abeb49fd/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199110-7ad6530b/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199070-2e10f339/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199066-31e8e3ce/',
# 'https://auto.ru/cars/new/group/omoda/c5/23526138/23526165/1122199061-2e0e34e0/',
# ]
cars_url = ['https://auto.ru/showcaptcha?mt=2A9FCCCF981C7249AEDC40AB101E9B377A8A52E6E1266439EE4A6C9510EDE7EB672C9A237AB922AA30F57FD7ED52277F227EDDCFE461B416AF5C06601CCDB8978C7B92791FAC6651DD3D69C70D3CEDEEF11E92FF7EE36E381BDD8EB574D7536023D9B2FAB93DC2B1BBC104A5A030A0DE98E7220BE165B25FAB93F2F65D4369874D490D821A4295039255F6D0CE2BA080943D1AD0970D52C85991CFC38C255742DDCB327F1050E79FA7563D84F5739BE3ED20398493065783E177067FBF90A565EB47D735BAACEEE73FF1AE224306E0DAE1ADD702EF09E45279EC10C2033ABC2F&retpath=aHR0cHM6Ly9hdXRvLnJ1Lz8%2C_4da3a1eb8e8becdae332d79b261fe3b4&t=4/1708422670/992499092143ae94d0efece71d8d5243&u=2bd1e0ae-b402e718-5cd44ceb-b00eb036&s=d5ebd3dcb5093f30bd0aa547d894d12a&state=image']
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)

# Опции для веб-драйвера
options = webdriver.ChromeOptions()
options.add_argument("--incognito")  # Запуск браузера в полноэкранном режиме

# Создаем экземпляр веб-драйвера
driver = webdriver.Chrome(options=options)

wait = WebDriverWait(driver, 120)

for car in cars_url:
    driver.get(car)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    check_captcha(driver)
