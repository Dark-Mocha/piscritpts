""" Bot Class """

import hashlib
import json
import logging
import pprint
from datetime import datetime
from functools import lru_cache
from os import fsync, unlink
from os.path import basename, exists
from time import sleep
from typing import Any, Dict, List, Tuple

import requests
import udatetime
import yaml
from binance.client import Client
from binance.exceptions import BinanceAPIException
from pyrate_limiter import Duration, Limiter, RequestRate
from tenacity import retry, wait_exponential

from lib.coin import Coin
from lib.helpers import (
    add_100,
    c_date_from,
    c_from_timestamp,
    floor_value,
    mean,
    percent,
)

rate = RequestRate(600, Duration.MINUTE)  # 600 requests per minute
limiter = Limiter(rate)


class Bot:
    """Bot Class"""

    def __init__(
        self,
        conn: Client,
        config_file: str,
        config: Dict[str, Any],
       