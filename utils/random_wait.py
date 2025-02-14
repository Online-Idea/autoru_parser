import logging
import random
import time


def random_wait(min_wait: float = 0.5, max_wait: float = 2.5) -> None:
    seconds = round(random.uniform(min_wait, max_wait), 2)
    logging.info(f"Жду случайные {seconds:.2f} сек.")
    time.sleep(seconds)
