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
    result: float = float(whole) / 100 * float(part)
    return result


@lru_cache(1024)
def add_100(number: float) -> float:
    """adds 100 to a number"""
    return 100 + float(number)


@lru_cache(64)
def c_date_from(day: str) -> float:
    """returns a cached datetime.fromisoformat()"""
    return datetime.fromisoformat(day).timestamp()


@lru_cache(64)
def c_from_timestamp(date: float) -> datetime:
    """returns a cached datetime.fromtimestamp()"""
    return datetime.fromtimestamp(date)


@retry(wait=wait_exponential(multiplier=1, max=3))
def cached_binance_client(access_key: str, secret_key: str) -> Client:
    """retry wrapper for binance client first call"""

    lock = SoftFileLock("state/binance.client.lockfile", timeout=10)
    # when running automated-testing with multiple threads, we will hit
    # api requests limits, this happens during the client initialization
    # which mostly issues a ping. To avoid this when running multiple processes
    # we cache the client in a pickled state on disk and load it if it already
    # exists.
    cachefile = "cache/binance.client"
    with lock:
        if exists(cachefile) and (
            udatetime.now().timestamp() - getctime(cachefile) < (30 * 60)
        ):
            logging.debug("re-using local cached binance.client file")
            with open(cachefile, "rb") as f:
                _client = pickle.load(f)  # nosec
        else:
            try:
                logging.debug("refreshing cached binance.client")
                _client = Client(access_key, secret_key)
            except Exception as err:
                logging.warning(f"API client exception: {err}")
                if "much request weight used" in str(err):
                    timestamp = (
          