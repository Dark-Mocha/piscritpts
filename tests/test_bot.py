
""" pytests tests for app.py """
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=import-outside-toplevel
# pylint: disable=no-self-use
from datetime import datetime
from unittest import mock
from flaky import flaky

import app
import lib
import lib.bot
import lib.coin
import pytest
import requests
import json


@pytest.fixture()
def cfg():
    with open("tests/config.yaml") as f:
        config = app.yaml.safe_load(f.read())
        config["MODE"] = "backtesting"
        return config


def test_percent():
    assert lib.bot.percent(0.1, 100.0) == 0.1


@pytest.fixture()
def bot(cfg):
    app.Client = mock.MagicMock()
    lib.bot.requests.get = mock.MagicMock()

    client = app.Client("FAKE", "FAKE")
    bot: lib.bot.Bot = lib.bot.Bot(client, "configfilename", cfg)
    bot.client.API_URL = "https://www.google.com"
    yield bot
    del bot


@pytest.fixture()
def coin(bot):
    coin: lib.coin.Coin = lib.coin.Coin(
        symbol="BTCUSDT",
        date=float(lib.bot.udatetime.now().timestamp() - 3600),
        market_price=float(100.00),
        buy_at=float(bot.tickers["BTCUSDT"]["BUY_AT_PERCENTAGE"]),
        sell_at=float(bot.tickers["BTCUSDT"]["SELL_AT_PERCENTAGE"]),
        stop_loss=float(bot.tickers["BTCUSDT"]["STOP_LOSS_AT_PERCENTAGE"]),
        trail_target_sell_percentage=float(
            bot.tickers["BTCUSDT"]["TRAIL_TARGET_SELL_PERCENTAGE"]
        ),
        trail_recovery_percentage=float(
            bot.tickers["BTCUSDT"]["TRAIL_RECOVERY_PERCENTAGE"]
        ),
        soft_limit_holding_time=int(
            bot.tickers["BTCUSDT"]["SOFT_LIMIT_HOLDING_TIME"]
        ),
        hard_limit_holding_time=int(
            bot.tickers["BTCUSDT"]["HARD_LIMIT_HOLDING_TIME"]
        ),
        naughty_timeout=int(bot.tickers["BTCUSDT"]["NAUGHTY_TIMEOUT"]),
        klines_trend_period=str(bot.tickers["BTCUSDT"]["KLINES_TREND_PERIOD"]),
        klines_slice_percentage_change=float(
            bot.tickers["BTCUSDT"]["KLINES_SLICE_PERCENTAGE_CHANGE"]
        ),
    )
    yield coin
    del coin


class TestCoin:
    def test_update_coin_wont_age_if_not_owned(self, coin, bot):
        coin.holding_time = 0
        coin.status = ""
        bot.update(coin, float(lib.bot.udatetime.now().timestamp()), 100.0)
        assert coin.holding_time == 0

    def test_update_coin_in_target_sell_status_will_age(self, coin, bot):