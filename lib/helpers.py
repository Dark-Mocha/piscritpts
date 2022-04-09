""" helpers module """
import logging
import math
import pickle  # nosec
import re
from datetime import datetime
from functools import lru_cache
from os.path import exists, getctime
from time import sleep, time

import udatetime
from binance.client import Client
from filelock import SoftFileLock
from tenacity import retry, wait_exponential


def mean(values: list[float]) -> float:
    """returns the mean value of an array of integers"""
    return sum(values) / len(values)


@lru_cache(1024)
def percent(part: float, whole: float) -> float:
    """returns the percentage value of a number"""
    result: float = float(whole) / 100 