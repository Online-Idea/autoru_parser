import re

from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder


def extract_digits_regex(text):
    """Extracts digits from a string and combines them into a single number, handling spaces.

    Args:
        text: The string to extract digits from.

    Returns:
        The extracted number as an integer, or 0 if no digits are found.
    """
    # Combine digits and optional spaces
    match = re.search(r"\d+\s*\d*", text)
    return int(match.group(0).replace(" ", "")) if match else 0


def close_popup(driver):
    """
    Клик по левой стороне плюс 1 пиксель, на случай если появляется popup
    @param driver:
    @return:
    """
    action = ActionBuilder(driver)
    action.pointer_action.move_to_location(0, 0)
    action.perform()


def extract_text_with_newlines(element):
    children = element.find_all(['span', 'br'])
    result = []
    for child in children:
        if child.name == 'br':
            # Add newline character for <br/>
            result.append('\n')
        else:
            # Extract text from span elements
            result.append(child.get_text())
    return ''.join(result)
