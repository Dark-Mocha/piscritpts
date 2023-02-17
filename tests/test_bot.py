
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
                "transactTime": 1507725176595,
                "fills": [
                    {
                        "price": "100",
                        "qty": "0.5",
                        "commission": "1",
                    }
                ],
            },
        ) as _:
            with mock.patch.object(
                bot.client,
                "get_order",
                return_value={
                    "symbol": "BTCUSDT",
                    "orderId": 1,
                    "price": 100,
                    "status": "FILLED",
                },
            ) as _:
                with mock.patch.object(
                    bot.client,
                    "get_all_orders",
                    return_value=[
                        {
                            "symbol": "BTCUSDT",
                            "orderId": 1,
                            "price": 100,
                            "status": "FILLED",
                        }
                    ],
                ) as _:
                    with mock.patch.object(
                        bot, "get_step_size", return_value=(True, "0.00001000")
                    ) as _:
                        assert bot.sell_coin(coin) is True
                        assert bot.wallet == []
                        # assert float(coin.price) == float(100)
                        # assert float(coin.bought_at) == float(0)
                        print(coin.value)
                        assert float(coin.value) == float(0.0)

    def test_sell_coin_using_limit_order_in_testnet(self, bot, coin):
        bot.mode = "testnet"
        bot.order_type = "LIMIT"
        coin.price = 100
        bot.wallet = ["BTCUSDT"]
        bot.coins["BTCUSDT"] = coin

        with mock.patch.object(
            bot.client,
            "create_order",
            return_value={
                "symbol": "BTCUSDT",
                "orderId": "1",
                "transactTime": 1507725176595,
            },
        ) as _:
            with mock.patch.object(
                bot.client,
                "get_order",
                return_value={
                    "symbol": "BTCUSDT",
                    "orderId": 1,
                    "price": 100,
                    "status": "FILLED",
                    "executedQty": 0.5,
                },
            ) as _:
                with mock.patch.object(
                    bot, "get_step_size", return_value=(True, "0.00001000")
                ) as _:
                    with mock.patch.object(
                        bot.client,
                        "get_order_book",
                        return_value={"bids": [[100, 1]]},
                    ) as _:
                        assert bot.sell_coin(coin) is True
                        assert bot.wallet == []
                        assert float(coin.price) == float(100)
                        assert float(coin.bought_at) == float(0)
                        assert float(coin.value) == float(0.0)

    def test_get_step_size(self, bot):
        with mock.patch.object(
            bot.client,
            "get_symbol_info",
            return_value={
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "baseAsset": "BTC",
                "baseAssetPrecision": 8,
                "quoteAsset": "USDT",
                "quotePrecision": 8,
                "quoteAssetPrecision": 8,
                "baseCommissionPrecision": 8,
                "quoteCommissionPrecision": 8,
                "orderTypes": [
                    "LIMIT",
                    "LIMIT_MAKER",
                    "MARKET",
                    "STOP_LOSS_LIMIT",
                    "TAKE_PROFIT_LIMIT",
                ],
                "icebergAllowed": "true",
                "ocoAllowed": "true",
                "quoteOrderQtyMarketAllowed": "true",
                "allowTrailingStop": "true",
                "cancelReplaceAllowed": "true",
                "isSpotTradingAllowed": "true",
                "isMarginTradingAllowed": "true",
                "filters": [
                    {
                        "filterType": "PRICE_FILTER",
                        "minPrice": "0.10000000",
                        "maxPrice": "100000.00000000",
                        "tickSize": "0.10000000",
                    },
                    {
                        "filterType": "LOT_SIZE",
                        "minQty": "0.00100000",
                        "maxQty": "900000.00000000",
                        "stepSize": "0.00001000",
                    },
                    {
                        "filterType": "MIN_NOTIONAL",
                        "minNotional": "10.00000000",
                        "applyToMarket": "true",
                        "avgPriceMins": 5,
                    },
                    {"filterType": "ICEBERG_PARTS", "limit": 10},
                    {
                        "filterType": "MARKET_LOT_SIZE",
                        "minQty": "0.00000000",
                        "maxQty": "15943.07122777",
                        "stepSize": "0.00000000",
                    },
                    {
                        "filterType": "TRAILING_DELTA",
                        "minTrailingAboveDelta": 10,
                        "maxTrailingAboveDelta": 2000,
                        "minTrailingBelowDelta": 10,
                        "maxTrailingBelowDelta": 2000,
                    },
                    {
                        "filterType": "PERCENT_PRICE_BY_SIDE",
                        "bidMultiplierUp": "5",
                        "bidMultiplierDown": "0.2",
                        "askMultiplierUp": "5",
                        "askMultiplierDown": "0.2",
                        "avgPriceMins": 5,
                    },
                    {"filterType": "MAX_NUM_ORDERS", "maxNumOrders": 200},
                    {
                        "filterType": "MAX_NUM_ALGO_ORDERS",
                        "maxNumAlgoOrders": 5,
                    },
                ],
                "permissions": [
                    "SPOT",
                    "MARGIN",
                    "TRD_GRP_004",
                    "TRD_GRP_005",
                ],
                "defaultSelfTradePreventionMode": "NONE",
                "allowedSelfTradePreventionModes": ["NONE"],
            },
        ) as _:
            result = bot.get_step_size("BTCUSDT")
            assert result == (True, "0.00001000")

    def test_extract_order_data(self, bot, coin):
        order_details = {
            "symbol": "BTCSDT",
            "orderId": 832382,
            "orderListId": -1,
            "clientOrderId": "jaksil2Ajbkl39kklapAQp",
            "transactTime": 1681589444803,
            "price": "0.00000000",
            "origQty": "2.31000000",
            "executedQty": "2.31000000",
            "cummulativeQuoteQty": "768.15300000",
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "MARKET",
            "side": "SELL",
            "workingTime": 1681589444803,
            "fills": [
                {
                    "price": "332.60000000",
                    "qty": "0.78000000",
                    "commission": "0.00000000",
                    "commissionAsset": "USDT",
                    "tradeId": 69154,
                },
                {
                    "price": "332.50000000",
                    "qty": "1.53000000",
                    "commission": "0.00000000",
                    "commissionAsset": "USDT",
                    "tradeId": 69155,
                },
            ],
            "selfTradePreventionMode": "NONE",
        }

        bot.calculate_volume_size = mock.MagicMock()
        bot.calculate_volume_size.return_value = (True, 0.5)

        ok, data = bot.extract_order_data(order_details, coin)
        assert ok is True
        assert data["avgPrice"] == 332.53376623376624
        assert data["volume"] == 0.5

    def test_calculate_volume_size(self, bot, coin):
        with mock.patch.object(
            bot, "get_step_size", return_value=(True, "0.00001000")
        ) as _:
            ok, volume = bot.calculate_volume_size(coin)
            assert ok == True
            assert volume == 0.5

    def test_get_binance_prices(self, bot):
        pass

    def test_init_or_update_coin(self, bot, cfg):
        binance_data = {"symbol": "BTCUSDT", "price": "101.000"}

        bot.load_klines_for_coin = mock.Mock()

        result = bot.init_or_update_coin(binance_data)
        assert result is None

        assert float(bot.coins["BTCUSDT"].price) == float(101.0)
        assert bot.coins["BTCUSDT"].buy_at_percentage == float(
            100 + cfg["TICKERS"]["BTCUSDT"]["BUY_AT_PERCENTAGE"]
        )
        assert bot.coins["BTCUSDT"].stop_loss_at_percentage == float(
            100 + cfg["TICKERS"]["BTCUSDT"]["STOP_LOSS_AT_PERCENTAGE"]
        )
        assert bot.coins["BTCUSDT"].sell_at_percentage == float(
            100 + cfg["TICKERS"]["BTCUSDT"]["SELL_AT_PERCENTAGE"]
        )
        assert bot.coins["BTCUSDT"].trail_target_sell_percentage == float(
            100 + cfg["TICKERS"]["BTCUSDT"]["TRAIL_TARGET_SELL_PERCENTAGE"]
        )
        assert bot.coins["BTCUSDT"].trail_recovery_percentage == float(
            100 + cfg["TICKERS"]["BTCUSDT"]["TRAIL_RECOVERY_PERCENTAGE"]
        )
        assert bot.coins["BTCUSDT"].naughty_timeout == int(
            cfg["TICKERS"]["BTCUSDT"]["NAUGHTY_TIMEOUT"]
        )

    def test_process_coins(self, bot, coin):
        # the bot will not buy coins when we have less than 31days of prices
        # so we mock those calls done in process_coins() to so that
        # the new_listing() check doesn't return False
        # as the coin won't have any averages['d'] value
        bot.load_klines_for_coin = mock.Mock()
        bot.new_listing = mock.Mock()

        for x in list(reversed(range(32))):
            coin_time = float(
                lib.bot.udatetime.now().timestamp() - (x * 86400)
            )
            bot.update(coin, coin_time, 0)

        bot.coins["BTCUSDT"] = coin

        with mock.patch.object(
            bot.client,
            "create_order",
            return_value={
                "symbol": "BTCUSDT",
                "orderId": "1",
                "transactTime": 1507725176595,
                "fills": [
                    {
                        "price": "100",
                        "qty": "1",
                        "commission": "1",
                    }
                ],
            },
        ) as _:
            with mock.patch.object(
                bot.client,
                "get_all_orders",
                return_value=[{"symbol": "BTCUSDT", "orderId": 1}],
            ) as _:
                with mock.patch.object(
                    bot, "get_step_size", return_value="0.00001000"
                ) as _:
                    binance_data = [
                        {"symbol": "BTCUSDT", "price": "101.000"},
                        {"symbol": "BTCUSDT", "price": "70.000"},
                        {"symbol": "BTCUSDT", "price": "75.000"},
                    ]
                    with mock.patch.object(
                        bot, "get_binance_prices", return_value=binance_data
                    ) as _:
                        with mock.patch.object(
                            bot, "run_strategy", return_value=None
                        ) as m5:
                            bot.process_coins()
                            assert m5.assert_called() is None

    def test_load_klines_for_coin(self, bot, coin):
        date = float(
            datetime.fromisoformat(
                "2021-12-04 05:23:05.693516",
            ).timestamp()
            / 1000
        )
        r = lib.bot.requests.models.Response()
        r.status_code = 200
        r.headers["Content-Type"] = "application/json"
        response = {}
        for metric in ["lowest", "averages", "highest"]:
            response[metric] = {}
            for unit in ["s", "m", "h", "d"]:
                response[metric][unit] = []

        price = 1
        seconds = 0
        unit = "m"
        for _ in range(60):
            response["lowest"][unit].append((date + seconds, price - 1))
            response["averages"][unit].append((date + seconds, price))
            response["highest"][unit].append((date + seconds, price + 1))
            price = price + 1
            seconds = seconds + 60

        price = 1
        seconds = 0
        unit = "h"
        for _ in range(24):
            response["lowest"][unit].append((date + seconds, price - 1))
            response["averages"][unit].append((date + seconds, price))
            response["highest"][unit].append((date + seconds, price + 1))
            price = price + 1
            seconds = seconds + 3600

        price = 1
        seconds = 0
        unit = "d"
        for _ in range(60):
            response["lowest"][unit].append((date + seconds, price - 1))
            response["averages"][unit].append((date + seconds, price))
            response["highest"][unit].append((date + seconds, price + 1))
            price = price + 1
            seconds = seconds + 86400

        coin.date = date + seconds
        # pylint: disable=protected-access
        r._content = app.json.dumps(response).encode("utf-8")

        with mock.patch("lib.bot.requests.get", return_value=r) as _:
            bot.load_klines_for_coin(coin)

        # upstream we retrieve 1000 days of history, but we only mock 60 days
        # in here. so we should expect 60 days of data
        assert len(coin.lowest["d"]) == 60
        assert len(coin.lowest["h"]) == 24
        assert len(coin.lowest["m"]) == 60

        assert len(coin.averages["d"]) == 60
        assert len(coin.averages["h"]) == 24
        assert len(coin.averages["m"]) == 60

        assert len(coin.highest["d"]) == 60
        assert len(coin.highest["h"]) == 24
        assert len(coin.highest["m"]) == 60

        assert coin.lowest["m"][0] == [1638595.3856935161, 0]
        assert coin.lowest["m"][59] == [1642135.3856935161, 59.0]

        assert coin.averages["m"][0] == [1638595.3856935161, 1]
        assert coin.averages["m"][59] == [1642135.3856935161, 60.0]

        assert coin.highest["m"][0] == [1638595.3856935161, 2]
        assert coin.highest["m"][59] == [1642135.3856935161, 61.0]

        assert coin.lowest["h"][0] == [1638595.3856935161, 0]
        assert coin.lowest["h"][23] == [1721395.3856935161, 23]

        assert coin.averages["h"][0] == [1638595.3856935161, 1]
        assert coin.averages["h"][23] == [1721395.3856935161, 24]

        assert coin.highest["h"][0] == [1638595.3856935161, 2]
        assert coin.highest["h"][23] == [1721395.3856935161, 25]

    def test_new_listing(self, bot, coin):
        for x in list(reversed(range(3600 * 24 * 2 + 3600 + 60 + 1))):
            coin_time = float(lib.bot.udatetime.now().timestamp() - x)
            bot.update(coin, coin_time, 100)

        assert bot.new_listing(coin, 3) is True
        assert bot.new_listing(coin, 1) is False

    def test_refresh_config_from_config_endpoint_service(self, bot):
        bot.pull_config_address = "http://fake"

        lib.bot.requests.get = mock.MagicMock()
        lib.bot.requests.get.return_value.status_code.return_value = 200

        with mock.patch(
            "builtins.open",
            mock.mock_open(read_data=json.dumps({"TICKERS": {}})),
        ) as _:
            # same md5 should return False
            lib.bot.requests.get.return_value.json.return_value = {
                "md5": "fake1",
                "TICKERS": {},
            }

            bot.pull_config_md5 = "fake1"
            assert bot.refresh_config_from_config_endpoint_service() is False

            # different md5 should return True
            bot.pull_config_md5 = "fake2"
            assert bot.refresh_config_from_config_endpoint_service() is True

            # different md5 should update TICKERS
            lib.bot.requests.get.return_value.json.return_value = {
                "md5": "fake3",
                "TICKERS": {"BTCUSDT": {}},
            }
            assert bot.refresh_config_from_config_endpoint_service() is True
            assert bot.pull_config_md5 == "fake3"
            assert bot.tickers == {"BTCUSDT": {}}

            # different md5 should update TICKERS and keep existing WALLET
            lib.bot.requests.get.return_value.json.return_value = {
                "md5": "fake4",
                "TICKERS": {"ETHUSDT": {}},
            }
            bot.tickers = {"BTCUSDT": {}}
            bot.wallet = ["BTCUSDT"]
            assert bot.refresh_config_from_config_endpoint_service() is True
            assert bot.pull_config_md5 == "fake4"
            assert bot.tickers == {"BTCUSDT": {}, "ETHUSDT": {}}

            # different md5 should update TICKERS and remove if not in wallet
            lib.bot.requests.get.return_value.json.return_value = {
                "md5": "fake5",
                "TICKERS": {"ETHUSDT": {}},
            }
            bot.tickers = {"BTCUSDT": {}}
            bot.wallet = []
            assert bot.refresh_config_from_config_endpoint_service() is True
            assert bot.pull_config_md5 == "fake5"
            assert bot.tickers == {"ETHUSDT": {}}

            # an exception should return false
            lib.bot.requests.get.return_value.json.return_value = {
                "md5": "fake9"
            }
            assert bot.refresh_config_from_config_endpoint_service() is False

    def test_run_stategy_gives_False_if_coin_not_in_tickers(self, bot, coin):
        bot.tickers = {}
        assert bot.run_strategy(coin) is False

    def test_run_stategy_gives_False_if_coin_is_naught(self, bot, coin):
        coin.naughty = True
        bot.coins["BTCUSDT"] = coin
        bot.run_strategy(coin) is False

    def test_run_stategy_calls_sale_if_wallet_not_empty(self, bot, coin):
        # if there are coins in WALLET
        bot.wallet = ["XXXX"]
        bot.coins["BTCUSDT"] = coin
        bot.target_sell = mock.MagicMock()
        bot.check_for_sale_conditions = mock.MagicMock()
        bot.new_listing = mock.MagicMock()
        bot.enable_pump_and_checks = mock.MagicMock()
        bot.buy_strategy = mock.MagicMock()

        bot.run_strategy(coin)

        bot.target_sell.assert_called_once()
        bot.check_for_sale_conditions.assert_called_once()

    def test_run_stategy_returns_false_on_new_listing(self, bot, coin):
        bot.wallet = []
        bot.tickers["BTCUSDT"] = {}
        coin.symbol = "BTCUSDT"
        coin.naughty = False
        bot.coins["BTCUSDT"] = coin
        bot.enable_new_listing_checks = True
        bot.enable_new_listing_checks_age_in_days = 30
        bot.new_listing = mock.MagicMock()
        bot.new_listing.return_value = True
        assert bot.run_strategy(coin) is False
        bot.new_listing.assert_called_once()

    def test_run_stategy_returns_false_on_full_wallet(self, bot, coin):
        bot.coins["BTCUSDT"] = coin
        bot.enable_new_listing_checks = False
        bot.wallet = ["BTCUSDT"]
        bot.max_coins = 1
        assert bot.run_strategy(coin) is False

    def test_run_stategy_returns_false_on_a_pump(self, bot, coin):
        bot.coins["BTCUSDT"] = coin
        bot.enable_new_listing_checks = False
        bot.enable_pump_and_dump_checks = True
        bot.wallet = []
        bot.max_coins = 1
        bot.check_for_pump_and_dump = mock.MagicMock()
        bot.check_for_pump_and_dump.return_value = True

        assert bot.run_strategy(coin) is False
        bot.check_for_pump_and_dump.assert_called_once()

    def test_run_stategy_returns_True(self, bot, coin):
        bot.coins["BTCUSDT"] = coin
        bot.enable_new_listing_checks = False
        bot.enable_pump_and_dump_checks = False
        bot.buy_strategy = mock.MagicMock()
        assert bot.run_strategy(coin) is True
        bot.buy_strategy.assert_called_once()

    def test_get_price_log(self, bot):
        session = mock.MagicMock()
        session.get = mock.MagicMock()
        session.get.return_value.status_code = 200
        session.get.return_value.content = "001 SYMBOL 100\n002 SYMBOL 101"

        with mock.patch(
            "builtins.open",
            mock.mock_open(read_data=""),
        ) as _:
            ok, data = bot.get_price_log(session, "http://log/log")
            assert data[0] == "001 SYMBOL 100"
            assert ok is True

    def test_place_sell_order(self, bot, coin):
        bot.extract_order_data = mock.MagicMock()
        bot.client.get_order = mock.MagicMock()
        bot.client.create_order = mock.MagicMock()
        bot.client.get_order_book = mock.MagicMock()

        # empty order_book should return False
        bot.order_type = "LIMIT"
        bot.client.get_order_book.return_value = {
            "lastUpdateId": 1027024,
            "bids": [],
            "asks": [],
        }
        assert bot.place_sell_order(coin) is False

        # a good order_book should return True
        bot.order_type = "MARKET"
        bot.client.get_order_book.return_value = {
            "lastUpdateId": 1027024,
            "bids": [
                [
                    "4.00000000",  # PRICE
                    "431.00000000",  # QTY
                    [],  # Can be ignored
                ]
            ],
            "asks": [["4.00000200", "12.00000000", []]],
        }

        bot.client.get_order.return_value = {
            "symbol": "LTCBTC",
            "orderId": 1,
            "clientOrderId": "myOrder1",
            "price": "0.1",
            "origQty": "1.0",
            "executedQty": "0.0",
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": "BUY",
            "stopPrice": "0.0",
            "icebergQty": "0.0",
            "time": 1499827319559,
        }

        bot.extract_order_data.return_value = (
            True,
            {"avgPrice": 100, "volume": 1},
        )
        assert bot.place_sell_order(coin) is True

        # Expired Sell Order should return False
        bot.order_type = "LIMIT"
        bot.client.get_order_book.return_value = {
            "lastUpdateId": 1027024,
            "bids": [
                [
                    "4.00000000",  # PRICE
                    "431.00000000",  # QTY
                    [],  # Can be ignored
                ]
            ],
            "asks": [["4.00000200", "12.00000000", []]],
        }

        bot.client.get_order.return_value = {
            "symbol": "LTCBTC",
            "orderId": 1,
            "clientOrderId": "myOrder1",
            "price": "0.1",
            "origQty": "1.0",
            "executedQty": "0.0",
            "status": "EXPIRED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": "BUY",
            "stopPrice": "0.0",
            "icebergQty": "0.0",
            "time": 1499827319559,
        }

        assert bot.place_sell_order(coin) is False


class TestBotCheckForSaleConditions:
    def test_returns_early_on_empty_wallet(self, bot, coin):
        bot.wallet = []
        result = bot.check_for_sale_conditions(coin)
        assert result == (False, "NOT_IN_WALLET")

    def test_returns_early_on_stop_loss(self, bot, coin):
        bot.wallet = ["BTCUSDT"]
        coin.price = 1
        coin.bought_at = 100
        result = bot.check_for_sale_conditions(coin)
        assert result == (True, "STOP_LOSS")

    def test_returns_early_on_stale_coin(self, bot, coin):
        bot.wallet = ["BTCUSDT"]
        coin.price = 1000
        coin.holding_time = 99999
        coin.status = "DIRTY"
        bot.hard_limit_holding_time = 1
        result = bot.check_for_sale_conditions(coin)
        assert result == (True, "STALE")

    def test_returns_early_on_coing_gone_up_and_dropped_when_flagged_on(
        self, bot, coin
    ):
        bot.wallet = ["BTCUSDT"]
        bot.sell_as_soon_it_drops = True
        coin.status = "TARGET_SELL"
        coin.price = 100.5
        coin.last = 120
        coin.bought_at = 100
        result = bot.check_for_sale_conditions(coin)
        print(coin.stop_loss_at_percentage)
        assert result == (True, "GONE_UP_AND_DROPPED")

    def test_returns_early_on_possible_sale(self, bot, coin):
        bot.wallet = ["BTCUSDT"]
        coin.status = "TARGET_SELL"
        coin.bought_at = 1
        coin.price = 50
        coin.last = 100
        coin.tip = 200
        result = bot.check_for_sale_conditions(coin)
        assert result == (True, "TARGET_SELL")

    def test_returns_final_on_past_soft_limit(self, bot, coin):
        bot.wallet = ["BTCUSDT"]
        coin.bought_at = 100
        coin.price = 100
        coin.last = 100
        coin.tip = 100
        result = bot.check_for_sale_conditions(coin)
        assert result == (False, "HOLD")


class TestBuyCoin:
    def test_buy_coin_when_coin_already_on_wallet(self, bot, coin):
        bot.wallet = ["BTCUSDT"]
        bot.buy_coin(coin)
        assert bot.wallet == ["BTCUSDT"]

    def test_buy_coin_when_wallet_is_full(self, bot, coin):
        bot.wallet = ["BTCUSDT", "ETHUSDT"]
        bot.buy_coin(coin)
        assert bot.wallet == ["BTCUSDT", "ETHUSDT"]

    def test_buy_coin_when_coin_is_naughty(self, bot, coin):
        coin.naughty = True
        bot.buy_coin(coin)
        assert bot.wallet == []

    @mock.patch("lib.bot.Bot.get_step_size", return_value=(True, "0.00001000"))
    def test_buy_coin_in_backtesting(self, _, bot, coin):
        bot.mode = "backtesting"
        coin.price = 100

        bot.buy_coin(coin)
        assert bot.wallet == ["BTCUSDT"]
        assert coin.bought_at == 100
        assert coin.volume == 0.5

    def test_buy_coin_using_market_order_in_testnet(self, bot, coin):
        bot.mode = "testnet"
        coin.price = 100

        with mock.patch.object(
            bot.client,
            "create_order",
            return_value={
                "symbol": "BTCUSDT",
                "orderId": "1",
                "transactTime": 1507725176595,
                "fills": [
                    {
                        "price": "100",
                        "qty": "0.5",
                        "commission": "0.00000000",
                        "commissionAsset": "BNB",
                        "tradeId": 3616061,
                    }
                ],
            },
        ) as _:
            with mock.patch.object(
                bot.client,
                "get_order",
                return_value={
                    "symbol": "BTCUSDT",
                    "orderId": 1,
                    "price": 100,
                    "status": "FILLED",
                    "executedQty": 0.5,
                },
            ) as _:
                with mock.patch.object(
                    bot.client,
                    "get_all_orders",
                    return_value=[
                        {
                            "symbol": "BTCUSDT",
                            "orderId": 1,
                            "status": "FILLED",
                            "price": 100,
                            "executedQty": 0.5,
                        }
                    ],
                ) as _:
                    with mock.patch.object(
                        bot, "get_step_size", return_value=(True, "0.00001000")
                    ) as _:
                        assert bot.buy_coin(coin) is True
                        assert bot.wallet == ["BTCUSDT"]
                        assert coin.bought_at == 100
                        assert coin.volume == 0.5
                        # TODO: assert that clear_all_coins_stats

    def test_buy_coin_using_limit_order_in_testnet(self, bot, coin):
        bot.mode = "testnet"
        bot.debug = True
        bot.order_type = "LIMIT"
        coin.price = 100

        with mock.patch.object(
            bot.client,
            "create_order",
            return_value={
                "symbol": "BTCUSDT",
                "orderId": "1",
                "transactTime": 1507725176595,
            },
        ) as _:
            with mock.patch.object(
                bot.client,
                "get_order",
                return_value={
                    "symbol": "BTCUSDT",
                    "orderId": 1,
                    "status": "FILLED",
                    "price": 100,
                    "executedQty": 0.5,
                },
            ) as _: