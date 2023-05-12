import logging
import random
import time


def random_wait():
    seconds = round(random.uniform(2.11, 10.98), 2)
    logging.info(f"Жду случайные {seconds:.2f} сек.")
    time.sleep(seconds)
