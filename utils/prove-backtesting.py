
""" prove backtesting """
import glob
import json
import os
import re
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime, timedelta
from itertools import islice
from multiprocessing import Pool
from string import Template
from time import sleep
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
import requests
import yaml
from tenacity import retry, wait_exponential


@retry(wait=wait_exponential(multiplier=2, min=1, max=30))
def get_index_json(query: str) -> requests.Response:
    """retry wrapper for requests calls"""
    response: requests.Response = requests.get(query, timeout=5)
    status: int = response.status_code
    if status != 200:
        with open("log/price_log_service.response.log", "at") as l:
            l.write(f"{query} {status} {response}\n")
        response.raise_for_status()
    return response


def log_msg(msg: str) -> None:
    """logs out message prefixed with timestamp"""
    now: str = datetime.now().strftime("%H:%M:%S")
    print(f"{now} PROVE-BACKTESTING: {msg}")


def cleanup() -> None:
    """clean files"""
    for item in glob.glob("configs/coin.*.yaml"):
        os.remove(item)
    for item in glob.glob("results/backtesting.coin.*.txt"):
        os.remove(item)
    for item in glob.glob("results/backtesting.coin.*.log.gz"):
        os.remove(item)
    if os.path.exists("log/backtesting.log"):
        os.remove("log/backtesting.log")


def flag_checks() -> None:
    """checks for flags in control/"""
    while os.path.exists("control/PAUSE"):
        log_msg("control/PAUSE flag found. Sleeping 1min.")
        sleep(60)


def wrap_subprocessing(conf: str, timeout: Optional[int] = 0) -> None:
    """wraps subprocess call"""
    if timeout == 0:
        timeout = None
    subprocess.run(
        "python app.py -m backtesting -s tests/fake.yaml "
        + f"-c configs/{conf} >results/backtesting.{conf}.txt 2>&1",
        shell=True,
        timeout=timeout,
        check=False,
    )


class ProveBacktesting:
    """ProveBacktesting"""

    def __init__(self, cfg: Dict[str, Any]) -> None:
        """init"""
        self.min: float = float(cfg["MIN"])
        self.filter_by: str = cfg["FILTER_BY"]
        self.from_date: datetime = datetime.strptime(
            str(cfg["FROM_DATE"]), "%Y%m%d"
        )
        self.end_date: datetime = datetime.strptime(
            str(cfg["END_DATE"]), "%Y%m%d"
        )
        self.roll_backwards: int = int(cfg["ROLL_BACKWARDS"])
        self.roll_forward: int = int(cfg["ROLL_FORWARD"])
        self.strategy: str = cfg["STRATEGY"]
        self.runs: Dict[str, Any] = dict(cfg["RUNS"])
        self.pause_for: float = float(cfg["PAUSE_FOR"])
        self.initial_investment: float = float(cfg["INITIAL_INVESTMENT"])
        self.re_invest_percentage: float = float(cfg["RE_INVEST_PERCENTAGE"])
        self.max_coins: int = int(cfg["MAX_COINS"])
        self.pairing: str = str(cfg["PAIRING"])
        self.clear_coin_stats_at_boot: bool = bool(
            cfg["CLEAR_COIN_STATS_AT_BOOT"]
        )
        self.clear_coin_stats_at_sale: bool = bool(
            cfg["CLEAR_COIN_STATS_AT_SALE"]
        )
        self.debug: bool = bool(cfg["DEBUG"])
        self.trading_fee: float = float(cfg["TRADING_FEE"])
        self.sell_as_soon_it_drops: bool = bool(cfg["SELL_AS_SOON_IT_DROPS"])
        self.stop_bot_on_loss: bool = bool(cfg["STOP_BOT_ON_LOSS"])
        self.stop_bot_on_stale: bool = bool(cfg["STOP_BOT_ON_STALE"])
        self.enable_new_listing_checks: bool = bool(
            cfg["ENABLE_NEW_LISTING_CHECKS"]
        )
        self.enable_new_listing_checks_age_in_days: int = int(
            cfg["ENABLE_NEW_LISTING_CHECKS_AGE_IN_DAYS"]
        )
        self.klines_caching_service_url: str = cfg[
            "KLINES_CACHING_SERVICE_URL"
        ]
        self.price_log_service_url: str = cfg["PRICE_LOG_SERVICE_URL"]
        self.concurrency: int = int(cfg["CONCURRENCY"])
        self.start_dates: List[str] = self.generate_start_dates(
            self.from_date, self.end_date, self.roll_forward
        )
        self.sort_by: str = cfg["SORT_BY"]

    def check_for_invalid_values(self) -> None:
        """check for invalid values in the config"""

        if self.sort_by not in [
            "max_profit_on_clean_wins",
            "number_of_clean_wins",
            "greed",
        ]:
            log_msg("SORT_BY set to invalid value")
            sys.exit(1)

    def generate_start_dates(
        self, start_date: datetime, end_date: datetime, jump: Optional[int] = 7
    ) -> List[str]:
        """returns a list of dates, with a gap in 'jump' days"""
        dates = pd.date_range(start_date, end_date, freq="d").strftime(
            "%Y%m%d"
        )
        start_dates: List[str] = list(islice(dates, 0, None, jump))
        return start_dates

    def rollback_dates_from(self, end_date: str) -> List[str]:
        """returns a list of dates, up to 'days' before the 'end_date'"""
        dates: List[str] = (
            pd.date_range(
                datetime.strptime(str(end_date), "%Y%m%d")
                - timedelta(days=self.roll_backwards - 1),
                end_date,
                freq="d",
            )
            .strftime("%Y%m%d")
            .tolist()
        )
        return dates

    def rollforward_dates_from(self, end_date: str) -> List[str]:
        """returns a list of dates, up to 'days' past the 'end_date'"""
        start_date: datetime = datetime.strptime(
            str(end_date), "%Y%m%d"
        ) + timedelta(days=1)
        _end_date: datetime = datetime.strptime(
            str(end_date), "%Y%m%d"
        ) + timedelta(days=self.roll_forward)
        dates: List[str] = (
            pd.date_range(start_date, _end_date, freq="d")
            .strftime("%Y%m%d")
            .tolist()
        )
        return dates

    def generate_price_log_list(
        self, dates: List[str], symbol: Optional[str] = None
    ) -> List[str]:
        """makes up the price log url list"""
        urls: List[str] = []
        for day in dates:
            if symbol:
                if self.filter_by in symbol:
                    urls.append(f"{symbol}/{day}.log.gz")
            else:
                urls.append(f"{day}.log.gz")
        return urls

    def write_single_coin_config(
        self, symbol: str, _price_logs: List[str], thisrun: Dict[str, Any]
    ) -> None:
        """generates a config.yaml for a coin"""

        if self.filter_by not in symbol:
            return

        tmpl: Template = Template(
            """{
        "CLEAR_COIN_STATS_AT_BOOT": $CLEAR_COIN_STATS_AT_BOOT,
        "CLEAR_COIN_STATS_AT_SALE": $CLEAR_COIN_STATS_AT_SALE,
        "DEBUG": $DEBUG,
        "ENABLE_NEW_LISTING_CHECKS": $ENABLE_NEW_LISTING_CHECKS,
        "ENABLE_NEW_LISTING_CHECKS_AGE_IN_DAYS": $ENABLE_NEW_LISTING_CHECKS_AGE_IN_DAYS,
        "INITIAL_INVESTMENT": $INITIAL_INVESTMENT,
        "KLINES_CACHING_SERVICE_URL": "$KLINES_CACHING_SERVICE_URL",
        "MAX_COINS": 1,
        "PAIRING": "$PAIRING",
        "PAUSE_FOR": $PAUSE_FOR,
        "PRICE_LOGS": $PRICE_LOGS,
        "PRICE_LOG_SERVICE_URL": "$PRICE_LOG_SERVICE_URL",
        "RE_INVEST_PERCENTAGE": $RE_INVEST_PERCENTAGE,
        "SELL_AS_SOON_IT_DROPS": $SELL_AS_SOON_IT_DROPS,
        "STOP_BOT_ON_LOSS": $STOP_BOT_ON_LOSS,
        "STOP_BOT_ON_STALE": $STOP_BOT_ON_STALE,
        "STRATEGY": "$STRATEGY",
        "TICKERS": {
          "$COIN": {
              "BUY_AT_PERCENTAGE": "$BUY_AT_PERCENTAGE",
              "SELL_AT_PERCENTAGE": "$SELL_AT_PERCENTAGE",
              "STOP_LOSS_AT_PERCENTAGE": "$STOP_LOSS_AT_PERCENTAGE",
              "TRAIL_TARGET_SELL_PERCENTAGE": "$TRAIL_TARGET_SELL_PERCENTAGE",
              "TRAIL_RECOVERY_PERCENTAGE": "$TRAIL_RECOVERY_PERCENTAGE",
              "SOFT_LIMIT_HOLDING_TIME": "$SOFT_LIMIT_HOLDING_TIME",
              "HARD_LIMIT_HOLDING_TIME": "$HARD_LIMIT_HOLDING_TIME",
              "NAUGHTY_TIMEOUT": "$NAUGHTY_TIMEOUT",
              "KLINES_TREND_PERIOD": "$KLINES_TREND_PERIOD",
              "KLINES_SLICE_PERCENTAGE_CHANGE": "$KLINES_SLICE_PERCENTAGE_CHANGE"
          }
         },
        "TRADING_FEE": $TRADING_FEE,
        }"""
        )

        # on our coin backtesting runs, we want to quit early if we are using
        # a sort_by mode that discards runs with STALES or LOSSES
        if self.sort_by == "greed":
            stop_bot_on_loss = False
            stop_bot_on_stale = False
        else:
            stop_bot_on_loss = True
            stop_bot_on_stale = True

        with open(f"configs/coin.{symbol}.yaml", "wt") as c:
            c.write(
                tmpl.substitute(
                    {
                        "CLEAR_COIN_STATS_AT_BOOT": self.clear_coin_stats_at_boot,
                        "CLEAR_COIN_STATS_AT_SALE": self.clear_coin_stats_at_sale,
                        "COIN": symbol,
                        "DEBUG": self.debug,
                        "ENABLE_NEW_LISTING_CHECKS": False,
                        "ENABLE_NEW_LISTING_CHECKS_AGE_IN_DAYS": 1,
                        "INITIAL_INVESTMENT": self.initial_investment,
                        "KLINES_CACHING_SERVICE_URL": self.klines_caching_service_url,
                        # each coin backtesting run should only use one coin
                        # MAX_COINS will only be applied to the final optimized run
                        "MAX_COINS": 1,
                        "PAIRING": self.pairing,
                        "PAUSE_FOR": self.pause_for,
                        "PRICE_LOGS": _price_logs,
                        "PRICE_LOG_SERVICE_URL": self.price_log_service_url,
                        "RE_INVEST_PERCENTAGE": 100,
                        "SELL_AS_SOON_IT_DROPS": self.sell_as_soon_it_drops,
                        "STOP_BOT_ON_LOSS": stop_bot_on_loss,
                        "STOP_BOT_ON_STALE": stop_bot_on_stale,
                        "STRATEGY": self.strategy,
                        "TRADING_FEE": self.trading_fee,
                        "BUY_AT_PERCENTAGE": thisrun["BUY_AT_PERCENTAGE"],
                        "SELL_AT_PERCENTAGE": thisrun["SELL_AT_PERCENTAGE"],
                        "STOP_LOSS_AT_PERCENTAGE": thisrun[
                            "STOP_LOSS_AT_PERCENTAGE"
                        ],
                        "TRAIL_TARGET_SELL_PERCENTAGE": thisrun[
                            "TRAIL_TARGET_SELL_PERCENTAGE"
                        ],
                        "TRAIL_RECOVERY_PERCENTAGE": thisrun[
                            "TRAIL_RECOVERY_PERCENTAGE"
                        ],
                        "SOFT_LIMIT_HOLDING_TIME": thisrun[
                            "SOFT_LIMIT_HOLDING_TIME"
                        ],
                        "HARD_LIMIT_HOLDING_TIME": thisrun[
                            "HARD_LIMIT_HOLDING_TIME"
                        ],
                        "NAUGHTY_TIMEOUT": thisrun["NAUGHTY_TIMEOUT"],
                        "KLINES_TREND_PERIOD": thisrun["KLINES_TREND_PERIOD"],
                        "KLINES_SLICE_PERCENTAGE_CHANGE": thisrun[
                            "KLINES_SLICE_PERCENTAGE_CHANGE"
                        ],
                    }
                )
            )

    def write_optimized_strategy_config(
        self,
        _price_logs: List[str],
        _tickers: Dict[str, Any],
        s_balance: float,
    ) -> None:
        """generates a config.yaml for a coin"""

        # we keep "state" between optimized runs, by soaking up an existing
        # optimized config file and an existing wallet.json file
        # while this could cause the bot as it starts to run  to pull old
        # optimized config files from old runs, we only consume those for
        # matching ticker info to the contents of our wallet.json, and we clean
        # up the json files at the start and end of the prove-backtesting.
        # so we don't expect to ever consume old tickers info from an old
        # config file.
        old_tickers: Dict[str, Any] = {}
        old_wallet: List[str] = []