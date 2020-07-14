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
        logs_dir: str = "log",
    ) -> None:
        """Bot object"""

        # Binance API handler
        self.client = conn
        # amount available to the bot to invest as set in the config file
        self.initial_investment: float = float(config["INITIAL_INVESTMENT"])
        # current investment amount
        self.investment: float = float(config["INITIAL_INVESTMENT"])
        # re-investment percentage
        self.re_invest_percentage: float = float(
            config.get("RE_INVEST_PERCENTAGE", 100.0)
        )
        # number of seconds to pause between price checks
        self.pause: float = float(config["PAUSE_FOR"])
        # list of price.logs to use during backtesting
        self.price_logs: List[str] = config["PRICE_LOGS"]
        # dictionary for all coin data
        self.coins: Dict[str, Coin] = {}
        # number of wins record by this bot run
        self.wins: int = 0
        # number of losses record by this bot run
        self.losses: int = 0
        # number of stale coins (which didn't sell before their
        # HARD_LIMIT_HOLDING_TIME) record by this bot run
        self.stales: int = 0
        # total profit for this bot run
        self.profit: float = float(0)
        # a wallet is for the coins we hold
        self.wallet: List[str] = []
        # the list of tickers and the config for each one, in terms of
        # BUY_AT_PERCENTAGE, SELL_AT_PERCENTAGE, etc...
        self.tickers: dict[str, Any] = dict(config["TICKERS"])
        # running mode for the bot [BACKTESTING, LIVE, TESTNET]
        self.mode: str = config["MODE"]
        # Binance trading fee for each buy/sell trade, in percentage points
        self.trading_fee: float = float(config["TRADING_FEE"])
        # Enable/Disable debug, debug information gets logged in debug.log
        self.debug: bool = bool(config["DEBUG"])
        # maximum number of coins that the bot will hold in its wallet.
        self.max_coins: int = int(config["MAX_COINS"])
        # which pair to use [USDT|BUSD|BNB|BTC|ETH...]
        self.pairing: str = config["PAIRING"]
        # total amount of fees paid during this bot run
        s