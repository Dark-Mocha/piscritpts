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
    """returns the mean value of an array of in