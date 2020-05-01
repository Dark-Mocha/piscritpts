
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
of those tokens. A mix of luck, looking at market charts and identifying
patterns allowed me to fit a set of parameters onto a coin and backtesting it
so that the bot would return a sane profit. And as long the market conditions
remained the same, the bot would return a profit while trading in live mode.

Might be worth pointing out now, that the bot has a few modes of operation,
backtesting, live, testnet, logmode.

At this point I started looking on how I could automate the tasks of finding
the best options for each coin over a period of time.
This lead me to simply automate the same tasks I was running manually which were to
run backtesting multiple times with different parameters and log those returns.
Eventually I added code to strip out any coins that didn't provide a minimum
amount of profit and filtering the best configs for each
one of those tokens automatically, ending with a single optimized config for a
number of crypto tokens.

As I had access to a good chunk of CPU, I refactored the automated backtesting
code to consume all my available CPU cores.
This of course caused the run to start hitting binance API limits.
To avoid those I started added proxies, retrying API calls to binance to avoid
hitting those rate limits and failed backtesting sessions.
For example when the bot finds a coin for the first time in a price log, it
would call binance to retrieve all its klines data from the last 60 min on a
1min interval, last 24 hours on a 1h interval and the last 1000 days on a daily
interval. Additionally for every trade I needed to find the precision to use for
each token. All this data needed to be saved locally as I would be requesting it
multiple times over and over. This new service klines-caching-service that would
deal with interacting with binance for me.

With access to enough CPU and a set of good strategies, I could achieve results
where I would invest $100 in 2017 and the bot would return in an optimized
config just above a million.
Of course this is not representative of how well the bot would behave in live
and that for the amounts involved there would never be enough liquidity in the
market. So I would always took these results with a very large grain of salt.

This lead me to another question, on how could I improve my confidence on the
results provided by these automated backtesting runs ?

I thought of a couple of things, first I would discard any coins on a particular
run that finished the runs with a stop-loss or a stale, or sill holding that
coin in the wallet at the end of the run. And focus the results on getting the
config for a coin that returned not the maximum profit but the highest number of
trades without any losses. This essentially meant that the bot instead of buying
a coin when it dropped in price by 10%, it would instead buy that coin when it
dropped in price by 40%.
This resulted in some side optimizations in backtesting, for example I would
quit backtesting a coin early as soon as I hit a STALE or a STOP LOSS.

The remaining piece was to automate the automated backtesting, instead of
running the backtesting over the last 300 days or so. I refactored the
automated backtesting script into pretending that we were running in live mode.
Essentially I would give a start date, like 2021-01-01 tell the bot to backtest
300 days and then run in pretend *live* mode for 30 days, before repeating this
process from the 2021-02-01 all the end until 2022-12-31.
The feedback was that I could see how a particular set of strategies would
behave in different markets and how well the automated-backtesting would adapt
to those changing markets. Essentially I could simulate what the bot looked to
return in a live scenario by using backtesting data against new price logs that
hadn't been backtested yet.

I could now identify strategies that could return lower consistent returns
insted of higher profits in highly volatile runs that would trigger my anxiety
response if I were to be trading that strategy live.

I called this new automated-backtesting, prove-backtesting.

Around this time I added a new price log service that would serve the price
logs to the backtesting bots. This resulted in removing all the IO I was
experiencing while running 48-96 concurrent bots and saved my SSDs from total
destruction. As part of the donwload klines script, I optimized the download of
klines so that I could have daily price log files for each coin.
This would allow the bot to backtesting a single coin in under a second, even
for a large number of price log files.

As of today, I can backtest around 300 days of logs for 48-96 coins in just a
few seconds on an old dual Xeon for those less permisive configs.

Possibly the final piece was how to collect the optimized backtesting configs I got
from my prove or automated-backtesting runs and feed them to my live bots.
For this I updated the bot to poll a http endpoint for a new set of configs and refresh
itself as soon a new config was available.
I called this the config-endpoint-service, and essentially its a service that
runs a prove-backtesting session (nightly or so) and when it finishes makes that
optimized config available to the live bot on a http endpoint.

With all these changes the original bot is now a collection of services
and is mostly hands-free.


# What tools

So what tools do we have?

There are multiple tool or services in this repo, for example:

* Downloading old klines price log files
* Automating backtesting multiple strategies against a number of kline
    *price.logs*, and producing an optimized strategy to use going forward.
* Reviewing how well our strategy works over a backtested period by re-running
  an automated-backtesting over and over a rolling-window, for example all the
  way back from 2017 to today, simulating a real live scenario.
* A caching proxy for binance klines calls, during automated-backtesting
    sessions, the bot can easily hammer the binance Api and be blocked due to
    rate limits. This caching proxy, keeps track of the number of requests/min
    avoiding going over the Binance Api rate limits.
* A config service, which listens on a particular http port and runs
    automated-backtesting periodically or on-demand, providing the tuned config
    through HTTP. The bot can be configured to replace its existing config with
    the provided by this service as soon as it becomes available. We can for
    example trigger a run of the automated-backtesting just after 00:00 and the
    bot will then consume a config that is optimized up to the last few minutes.
* A price_log http server, this can be used to serve price.log files from a
    central location to the different backtesting runners.

### How does it work

This bot looks to buy coins that at have gone down in price recently and are
now recovering from that downtrend. It relies on us specifying different
buy and sell points for each coin individually. For example, we can tell the
bot to buy BTCUSDT when the price drops by at least 6% and recovers by 1%. And
then set it to sell when the price increases by another 2%.
Or we may choose trade differently with another more volatile coin
where we buy the coin when the price drops by 25%, wait for it to recover by 2%
and then sell it at 5% profit.

In order to understand what are the best percentages on when to buy and sell for
each one of the coins available in binance, we use backtesting strategies
against a number of logfiles containing dated coin prices. Let's call them
klines price.logs.
These *price.logs* can be downloaded in 1 min interval klines from binance using a
[tool available in this repository](#obtaining-old-price-log-files).

With these price.log files we can run the bot in *backtesting* mode
which would run our buy/sell strategy against those price.log files and simulate
what sort of returns we would get from a particular strategy and a time frame
of the market.

In order to help us identify the best buy/sell percentages for each coin, there
is a helper tool in this repo which runs a form of
[automated-backtesting](#prove-backtesting) against
all the coins in binance and a number of buy/sell percentages and strategies
and returns the best config for each one of those coins for a specific period in
time.
This tool can be used to verify how a strategy behaves across changing markets
conditions and how well the bot adapts to those changes.

The way the bot chooses when to buy is based on a set of strategies which are
defined in the [strategies/](./strategies/) folder in this repo.
You can choose to build your own strategy and place it on the
[strategies/](./strategies) folder,

This bot currently provides different strategies:

* [*BuyDropSellRecoveryStrategy*](./strategies/BuyDropSellRecoveryStrategy.py)
* [*BuyMoonSellRecoveryStrategy*](./strategies/BuyMoonSellRecoveryStrategy.py)
* [*BuyOnGrowthTrendAfterDropStrategy*](./strategies/BuyOnGrowthTrendAfterDropStrategy.py)
* [*BuyOnRecoveryAfterDropDuringGrowthTrendStrategy*](./strategies/BuyOnRecoveryAfterDropDuringGrowthTrendStrategy.py)
* [*BuyOnRecoveryAfterDropFromAverageStrategy*](./strategies/BuyOnRecoveryAfterDropDuringGrowthTrendStrategy.py)

The way some of these strategies work is described later in this README. The
others can be found in the strategy files themselves.

While the price for every available coin is recorded in the *price.log*
logfiles, the bot will only act to buy or sell coins for coins listed
specifically on its configuration.

Each coin needs to be added to the configuration with a set of values for when to
buy and sell. This allows us to tell the Bot how it handles different coins
regarding their current state. For example, a high volatile coin that drops 10%
in price is likely to continue dropping further, versus a coin like BTCUSDT that
is relatively stable in price.

With that in mind, we can for example tell the Bot to when this coin drops *x%*
buy it, and when that coin drops *y%* buy it.

We could also let the bot do the opposite, for coins that are going on through
an uptrend, we can tell the bot to as soon a coin increases in value by % over a
period of time, we tell the bot to buy them.

For these different settings we apply to each coin, let's call them profiles for
now. These profile is essentially how the bot makes decisions on which coins to
buy and sell.

So for example for the *BuyDropSellRecoveryStrategy*:

I specify that I want the bot to buy *BTCUSDT* when the price initially drops
by at least 10%, followed by a recovery of at least 1%.

It should then look into selling that coin at a 6% profit upwards,
and that when it reaches 6% profit, the bot will sell the coin when the price
then drops by at least 1%.

To prevent loss, in case something goes wrong in the market.
I set the STOP LOSS at -10% over the price paid for the coin.

To avoid periods of volatility, in case after a stop-loss I set that I don't
want to buy any more BTCUSDT for at least 86400 seconds. After than the bot will
start looking at buying this coin again.

Some coins might be slow recovering from the price we paid, and take some time
for their price to raise all the way to the 6% profit we aim for.

To avoid having a bot coin slot locked forever, we set a kind of TimeToLive
on the coins the bot buys. We call this limit *HARD_LIMIT_HOLDING_TIME*.
The bot will forcefully sell the coin regardless of its price when this period expires.

To improve the chances of selling a coin during a slow recovery, we decrease
the target profit percentage gradually until we reach that *HARD_LIMIT_HOLDING_TIME*.

This is done through the setting *SOFT_LIMIT_HOLDING_TIME*, with this
setting we set the number of seconds to wait before the bot starts decreasing
the profit target percentage. Essentially we reduce the target profit until it
meets the current price of the coin.
