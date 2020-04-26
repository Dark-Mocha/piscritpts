
# CryptoBot - Binance Trading Bot

A python based trading bot for Binance, which relies heavily on backtesting.

![CryptoBot components](./cryptobot.jpg)

 1. [Overview](#overview)
 2. [History](#history)
    * [How does it work](#how-does-it-work)
 3. [Discord](#discord)
 4. [Getting started](#getting-started)
 5. [Usage](#usage)
 6. [Automated Backtesting](#automated-backtesting)
 7. [Prove automated-backtesting results](#prove-automated-backtesting-results)
 8. [config-endpoint-service](#config-endpoint-service)
 9. [Control Flags](#control-flags)
10. [Config settings](#config-settings)
    * [PAIRING](#pairing)
    * [INITIAL_INVESTMENT](#initial_investment)
    * [RE_INVEST_PERCENTAGE](#re_invest_percentage)
    * [PAUSE_FOR](#pause_for)
    * [STRATEGY](#strategy)
      * [BuyMoonSellRecoveryStrategy](#buymoonsellrecoverystrategy)
      * [BuyDropSellRecoveryStrategy](#buydropsellrecoverystrategy)
      * [BuyOnGrowthTrendAfterDropStrategy](#buyongrowthtrendafterdropstrategy)
      * [RSA/EMA](#rsa/ema)
    * [BUY_AT_PERCENTAGE](#buy_at_percentage)
    * [SELL_AT_PERCENTAGE](#sell_at_percentage)
    * [STOP_LOSS_AT_PERCENTAGE](#stop_loss_at_percentage)
    * [TRAIL_TARGET_SELL_PERCENTAGE](#trail_target_sell_percentage)
    * [TRAIL_RECOVERY_PERCENTAGE](#trail_recovery_percentage)
    * [HARD_LIMIT_HOLDING_TIME](#hard_limit_holding_time)
    * [SOFT_LIMIT_HOLDING_TIME](#soft_limit_holding_time)
    * [KLINES_TREND_PERIOD](#klines_trend_period)
    * [KLINES_SLICE_PERCENTAGE_CHANGE](#klines_slice_percentage_change)
    * [CLEAR_COIN_STATS_AT_BOOT](#clear_coin_stats_at_boot)
    * [NAUGHTY_TIMEOUT](#naughty_timeout)
    * [CLEAR_COIN_STATS_AT_SALE](#clear_coin_stats_at_sale)
    * [SELL_AS_SOON_AS_IT_DROPS](#sell_as_soon_as_it_drops)
    * [DEBUG](#debug)
    * [MAX_COINS](#max_coins)
    * [TICKERS](#tickers)
    * [TRADING_FEE](#trading_fee)
    * [PRICE_LOGS](#price_logs)
    * [ENABLE_PUMP_AND_DUMP_CHECKS](#enable_pump_and_dump_checks)
    * [ENABLE_NEW_LISTING_CHECKS](#enable_new_listing_checks)
    * [ENABLE_NEW_LISTING_CHECKS_AGE_IN_DAYS](#enable_new_listing_checks_age_in_days)
    * [STOP_BOT_ON_LOSS](#stop_bot_on_loss)
    * [ORDER_TYPE](#order_type)
    * [PULL_CONFIG_ADDRESS](#pull_config_address)
    * [PRICE_LOG_SERVICE_URL](#price_log_service_url)
    * [KLINES_CACHING_SERVICE_URL](#klines_caching_service_url)
    * [CONCURRENCY](#concurrency)
    * [SORT_BY](#sort_by)
      * [max_profit_on_clean_wins](#max_profit_on_clean_wins)
      * [number_of_clean_wins](#number_of_clean_wins)
      * [greed](#greed)
11. [Bot command center](#bot-command-center)
12. [Development/New features](#development/new-features)


## Overview

CryptoBot is a python based bot which relies heavily on automation and
backtesting to work across different trends of the market.

## History

I built this bot due to my own negative experience in other opensource bots that
lacked backtesting support and which had farly convoluted codebases, with no
tests making them hard to extend or modify with the features I wanted.

Essentially, I was looking for a bot where I could consume binance data and run
backtesting using different strategies. My initial goal was for a
bot that would buy a particular coin when that coin price went down by x% and
then sell it when the coin price raised by %y.

I added new functionality as I felt I need it, for example the bot started
by using a mode *logmode* which would save the current price for all the coins
with a 1s or less granularity. By having prices logged over a number of days I
could run backtesting strategies and identify the best options over the past days
in detail.
As the time to backtest increased with the number of logs, I added options to
consume price information from the logs every N seconds. For example only
consuming the price records entries price records every 60 seconds or so.
This allowed me to have a quick glance of how a particular backtesting strategy
would behave on a number of available price logs for the last N days.
I could then pick the best strategy and reduce the interval back to 1 second to
understand how that strategy would behave in a *normal* trade day.

Several rounds of refactoring and profiling the code improved the execution time,
down from minutes to around 30 seconds per daily log.

As saving daily logs through the *logmode* forced to have to run the bot for a
number of days before I could get any useful data to backtest, I looked into
automating the download of klines from binance using the minimum 1min interval
and saving them into the price log format consumed by the bot.
With this new tool I could now download price log files going back until 2017 from
binance and run backtesting since the beggining of time.

At this point, backtesting was time consuming and tricky to identify the best
crypto tokens to backtest as well as what parameters to apply to each one