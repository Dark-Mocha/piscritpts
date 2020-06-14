
""" load_klines_for_coin: manages the cache/ directory """
import json
import logging
import sys
import threading
from datetime import datetime
from functools import lru_cache
from hashlib import md5
from os import getpid, mkdir
from os.path import exists
from time import sleep

import colorlog  # pylint: disable=E0401
import requests
from flask import Flask, request  # pylint: disable=E0401
from pyrate_limiter import Duration, Limiter, RequestRate
from tenacity import retry, wait_exponential

rate: RequestRate = RequestRate(
    600, Duration.MINUTE
)  # 600 requests per minute
limiter: Limiter = Limiter(rate)

DEBUG = False
PID = getpid()

LOCK = threading.Lock()

c_handler = colorlog.StreamHandler(sys.stdout)
c_handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s[%(levelname)s] %(message)s",
        log_colors={
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
)
c_handler.setLevel(logging.INFO)

if DEBUG:
    f_handler = logging.FileHandler("log/debug.log")
    f_handler.setLevel(logging.DEBUG)

    logging.basicConfig(
        level=logging.DEBUG,
        format=" ".join(
            [
                "(%(asctime)s)",
                f"({PID})",
                "(%(lineno)d)",
                "(%(funcName)s)",
                "[%(levelname)s]",
                "%(message)s",
            ]
        ),
        handlers=[f_handler, c_handler],
        datefmt="%Y-%m-%d %H:%M:%S",
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        handlers=[c_handler],
    )


app = Flask(__name__)