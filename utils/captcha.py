

def is_captcha(driver):
    """
    Проверяет появились ли капча. Смотрит по тегу title
    @param driver:
    @return: True если капча
    """
    title = driver.title.lower()
    return 'капча' in title or 'captcha' in title
