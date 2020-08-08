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
        self.fees: float = float(0)
        # wether to clean coin stats at boot, if our tickers config doesn't
        # chane for example a reload, we might want to keep the history we have
        # related to the max, min prices recorded for our coins as those will
        # influence our next buy.
        self.clear_coin_stats_at_boot: bool = bool(
            config["CLEAR_COIN_STATS_AT_BOOT"]
        )
        # as above but after each buy
        self.clean_coin_stats_at_sale: bool = bool(
            config["CLEAR_COIN_STATS_AT_SALE"]
        )
        # which bot strategy to use as set in the config file
        self.strategy: str = config["STRATEGY"]
        # if a coin drops in price shortly after reaching its target sale
        # percentage, we force a quick sale and ignore the
        # TRAIL_TARGET_SELL_PERCENTAGE values
        self.sell_as_soon_it_drops: bool = bool(
            config["SELL_AS_SOON_IT_DROPS"]
        )
        # the config filename
        self.config_file: str = config_file
        # a dictionary to old the previous prices available from binance for
        # our coins. Used in logmode to prevent the bot from writing a new
        # price.log line if the price hasn't changed. Common with low volume
        # coins. This reduces our logfiles size and our backtesting times.
        self.oldprice: Dict[str, float] = {}
        # the full config as a dict
        self.cfg = config
        # whether to enable pump and dump checks while the bot is evaluating
        # buy conditions for a coin
        self.enable_pump_and_dump_checks: bool = config.get(
            "ENABLE_PUMP_AND_DUMP_CHECKS", True
        )
        # check if we are looking at a new coin
        self.enable_new_listing_checks: bool = config.get(
            "ENABLE_NEW_LISTING_CHECKS", True
        )
        # disable buying a new coin if this coin is newer than 31 days
        self.enable_new_listing_checks_age_in_days: int = config.get(
            "ENABLE_NEW_LISTING_CHECKS_AGE_IN_DAYS", 31
        )
        # stops the bot as soon we hit a STOP_LOSS. If we are still holding
        # coins, those remain in our wallet.
        # Typically used when MAX_COINS = 1
        self.stop_bot_on_loss: bool = config.get("STOP_BOT_ON_LOSS", False)
        # stops the bot as soon we hit a STALE. If we are still holding
        # coins, those remain in our wallet.
        # Mostly used for quitting a backtesting session early
        self.stop_bot_on_stale: bool = config.get("STOP_BOT_ON_STALE", False)
        # indicates where we found a control/STOP flag file
        self.stop_flag: bool = False
        # set by the bot so to quit safely as soon as possible.
        # used by STOP_BOT_ON_LOSS checks
        self.quit: bool = False
        # define if we want to use MARKET or LIMIT orders
        self.order_type: str = config.get("ORDER_TYPE", "MARKET")
        # generate a md5 hash of the tickers config based on the same method
        # used in the config-endpoint-service. We want a hash to be available
        # at boot so that when we first get the config from config-endpoint-service
        # and if the tickers haven't changed match the bot won't assume the
        # tickers or the config have changed.
        self.pull_config_md5: str = hashlib.md5(
            (json.dumps(dict(config["TICKERS"]), sort_keys=True)).encode(
                "utf-8"
            )
        ).hexdigest()
        self.pull_config_address: str = config.get("PULL_CONFIG_ADDRESS", "")
        self.logs_dir = logs_dir
        self.klines_caching_service_url: str = config.get(
            "KLINES_CACHING_SERVICE_URL", "http://klines:8999"
        )
        # price.log service
        self.price_log_service: str = config["PRICE_LOG_SERVICE_URL"]

    def extract_order_data(
        self, order_details: dict[str, Any], coin: Coin
    ) -> Tuple[bool, Dict[str, Any]]:
        """calculate average price and volume for a buy order"""

        # Each order will be fullfilled by different traders, and made of
        # different amounts and prices. Here we calculate the average over all
        # those different lines in our order.

        total: float = float(0)
        qty: float = float(0)

        logging.debug(f"{coin.symbol} -> order_details:{order_details}")

        for k in order_details["fills"]:
            item_price: float = float(k["price"])
            item_qty: float = float(k["qty"])

            total += item_price * item_qty
            qty += item_qty

        avg: float = total / qty

        ok, _volume = self.calculate_volume_size(coin)
        if ok:
            volume: float = float(_volume)

            logging.debug(f"{coin.symbol} -> volume:{volume} avgPrice:{avg}")

            return (
                True,
                {
                    "avgPrice": float(avg),
                    "volume": float(volume),
                },
            )
        return (False, {})

    def run_strategy(self, coin: Coin) -> bool:
        """runs a specific strategy against a coin"""

        # runs our choosen strategy, here we aim to quit as soon as possible
        # reducing processing time. So we stop validating conditions as soon
        # they are not possible to occur in the chain that follows.

        # the bot won't act on coins not listed on its config.
        if coin.symbol not in self.tickers:
            return False

        # skip any coins that were involved in a recent STOP_LOSS.
        if self.coins[coin.symbol].naughty:
            return False

        # first attempt to sell the coin, in order to free the wallet for the
        # next coin run_strategy run.
        if self.wallet:
            self.target_sell(coi