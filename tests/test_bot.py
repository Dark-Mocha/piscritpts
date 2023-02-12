
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
        coin.holding_time = 0
        coin.status = "TARGET_SELL"
        coin.bought_date = float(lib.bot.udatetime.now().timestamp() - 3600)
        bot.update(coin, float(lib.bot.udatetime.now().timestamp()), 100.0)
        assert coin.holding_time == 3600

    def test_update_coin_in_hold_status_will_age(self, coin, bot):
        coin.holding_time = 0
        coin.status = "HOLD"
        coin.bought_date = float(lib.bot.udatetime.now().timestamp() - 3600)
        bot.update(coin, float(lib.bot.udatetime.now().timestamp()), 100.0)
        assert coin.holding_time == 3600

    def test_update_coin_in_naughty_reverts_to_non_naughty_after_timeout_(
        self, coin, bot
    ):
        coin.naughty_timeout = 3599
        coin.naughty = True
        coin.naughty_date = float(lib.bot.udatetime.now().timestamp() - 3600)
        bot.update(coin, float(lib.bot.udatetime.now().timestamp()), 100.0)
        assert coin.naughty is False

    def test_update_coin_in_naughty_remains_naughty_before_timeout_(
        self, coin, bot
    ):
        coin.naughty_timeout = 7200
        coin.naughty = True
        coin.naughty_date = float(lib.bot.udatetime.now().timestamp() - 3600)
        bot.update(coin, float(lib.bot.udatetime.now().timestamp()), 100.0)
        assert coin.naughty is True

    def test_update_reached_new_min(self, coin, bot):
        coin.min = 200
        bot.update(coin, float(lib.bot.udatetime.now().timestamp()), 100.0)
        assert coin.min == 100

    def test_update_reached_new_max(self, coin, bot):
        coin.max = 100
        bot.update(coin, float(lib.bot.udatetime.now().timestamp()), 200.0)
        assert coin.max == 200

    def test_update_value_is_set(self, coin, bot):
        coin.volume = 2
        bot.update(coin, float(lib.bot.udatetime.now().timestamp()), 100.0)
        assert coin.value == 200

    def test_update_coin_updates_state_dip(self, coin, bot):
        coin.status = "TARGET_DIP"
        coin.dip = 150
        bot.update(coin, float(lib.bot.udatetime.now().timestamp()), 120.00)
        assert coin.dip == 120.00

    def test_update_coin_updates_seconds_averages(self, coin, bot):
        now = float(lib.bot.udatetime.now().timestamp())
        bot.update(coin, now, 120.00)

        # coin.averages['unit'] is a list of [date, price]
        assert [now, 120.00] in coin.averages["s"]

        # expect one element (date, price)
        assert 120.00 == coin.averages["s"][0][1]
        assert len(coin.averages["s"]) == 1

    @flaky
    def test_update_coin_updates_minutes_averages(self, coin, bot):
        for x in list(reversed(range(60 * 2 + 1))):
            coin_time = float(lib.bot.udatetime.now().timestamp() - x)
            bot.update(coin, coin_time, 100)

        assert len(coin.averages["s"]) == 61

        assert len(coin.averages["m"]) == 2

        for _, v in list(coin.averages["s"]):
            assert v == 100

        assert list(coin.averages["m"])[0][1] == 100.0

    @flaky
    def test_update_coin_updates_hour_averages(self, coin, bot):
        for x in list(reversed(range(60 * 60 + 60 + 1))):
            coin_time = float(lib.bot.udatetime.now().timestamp() - x)
            bot.update(coin, coin_time, 100)

        assert len(coin.averages["s"]) == 61

        assert len(coin.averages["m"]) == 60

        for _, v in list(coin.averages["m"]):
            assert v == 100

        assert list(coin.averages["h"])[0][1] == 100.0

    @flaky
    def test_update_coin_updates_days_averages(self, coin, bot):
        for x in list(reversed(range(3600 * 24 + 3600 + 60 + 1))):
            coin_time = float(lib.bot.udatetime.now().timestamp() - x)
            bot.update(coin, coin_time, 100)

        assert len(coin.averages["h"]) == 24

        for _, v in list(coin.averages["h"]):
            assert v == 100

        assert len(coin.averages["d"]) == 1
        assert list(coin.averages["d"])[0][1] == 100.0

    @flaky
    def test_update_coin_updates_minutes_lowest_highest(self, coin, bot):
        price = 100
        for x in list(reversed(range(60 * 2 + 1))):
            coin_time = float(lib.bot.udatetime.now().timestamp() - x)
            bot.update(coin, coin_time, price)
            price = price + 1

        assert len(coin.lowest["m"]) == 2
        assert list(coin.lowest["m"])[0][1] == 100.0
        assert list(coin.highest["m"])[0][1] == 160.0

        assert list(coin.lowest["m"])[-1][1] == 159.0
        assert list(coin.highest["m"])[-1][1] == 220.0

    @flaky
    def test_update_coin_updates_hour_lowest_highest(self, coin, bot):
        price = 100
        for x in list(reversed(range(60 * 60 + 60 + 1))):
            coin_time = float(lib.bot.udatetime.now().timestamp() - x)
            bot.update(coin, coin_time, price)
            price = price + 1

        assert len(coin.lowest["m"]) == 60
        assert len(coin.highest["m"]) == 60
        assert len(coin.lowest["h"]) == 1
        assert len(coin.highest["h"]) == 1

        assert list(coin.lowest["h"])[0][1] == 100.0
        assert list(coin.highest["h"])[0][1] == 3760.0

    @flaky
    def test_update_coin_updates_day_lowest_highest(self, coin, bot):
        price = 100
        for x in list(reversed(range(3600 * 24 + 3600 + 60 + 1))):
            coin_time = float(lib.bot.udatetime.now().timestamp() - x)
            bot.update(coin, coin_time, price)
            price = price + 1

        assert len(coin.lowest["h"]) == 24
        assert len(coin.highest["h"]) == 24
        assert len(coin.lowest["d"]) == 1
        assert len(coin.highest["d"]) == 1

        assert list(coin.lowest["d"])[0][1] == 100.0
        assert list(coin.highest["d"])[0][1] == 90160.0

    def test_trim_averages(self, coin, bot):
        price = 100
        now = lib.bot.udatetime.now().timestamp()

        for x in list(reversed(range(3600 * 48 + 3600 + 60 + 1))):
            coin_time = float(now - x)
            bot.update(coin, coin_time, price)

        assert coin.averages["s"][0] == [now - 60, 100.0]
        assert coin.averages["s"][59] == [now - 1, 100.0]

        assert coin.averages["m"][0] == [now - 3600, 100.0]
        assert coin.averages["m"][59] == [now - 60, 100.0]

        assert coin.averages["h"][0] == [now - 86400, 100.0]
        assert coin.averages["h"][23] == [now - 3600, 100.0]

    def test_for_pump_and_dump_returns_true_on_pump(self, coin, bot):
        # pylint: disable=attribute-defined-outside-init
        self.enable_pump_and_dump_checks = True
        now = lib.bot.udatetime.now().timestamp()

        coin.klines_trend_period = "2h"
        coin.klines_slice_percentage_change = float(1)

        bot.update(coin, now - 3600 * 2, 100)
        bot.update(coin, now - 3600 * 1, 1500)
        # price has gone up 500%
        bot.update(coin, now, 200)

        assert bot.check_for_pump_and_dump(coin) is True

        coin.klines_trend_period = "0h"
        assert bot.check_for_pump_and_dump(coin) is True

    def test_for_pump_and_dump_returns_false_on_pump(self, coin, bot):
        now = lib.bot.udatetime.now().timestamp()

        coin.klines_trend_period = "1h"
        coin.klines_slice_percentage_change = float(1)

        bot.update(coin, now - 3600 * 3, 100)
        bot.update(coin, now - 3600 * 2, 100)
        bot.update(coin, now - 3600, 100)
        # price has gone up 500%
        bot.update(coin, now, 500)

        assert bot.check_for_pump_and_dump(coin) is False


class TestBot:
    def test_sell_coin_using_market_order_in_testnet(self, bot, coin):
        bot.mode = "testnet"
        bot.order_type = "MARKET"
        coin.price = 100
        bot.wallet = ["BTCUSDT"]
        bot.coins["BTCUSDT"] = coin

        with mock.patch.object(
            bot.client,
            "create_order",
            return_value={
                "symbol": "BTCUSDT",
                "orderId": "1",