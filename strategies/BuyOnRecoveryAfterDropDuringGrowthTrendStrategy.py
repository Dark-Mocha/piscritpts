""" bot buy strategy file """
from lib.bot import Bot
from lib.coin import Coin
from lib.helpers import c_from_timestamp, logging, percent


class Strategy(Bot):
    """BuyOnRecoveryAfterDropDuringGrowthTrendStrategy"""

    def buy_strategy(self, coin: Coin) -> bool:
        """BuyOnRecoveryAfterDropDuringGrowthTrendStrategy buy_strategy

        This strategy looks for coins that have gone up by
        KLINES_SLICE_PERCENTAGE_CHANGE in each slice (m,h,d) of the
        KLINES_TREND_PERIOD.
        Then it checkous that the current price for those is
        lower than the BUY_AT_PERCENTAGE over the maximum price recorded.
        if it is, then mark the coin as TARGET_DIP
        and buy it as soon we're over the dip by TRAIL_RECOVERY_PERCENTAGE.
        """

        unit = str(coin.klines_trend_period[-1:]).lower()
        klines_trend_period = int(coin.klines_trend_period[:-1])

        last_period = list(coin.averages[unit])[-klines_trend_period:]

        # we need at least a full period of klines before we can
        # make a buy decision
        if len(last_period) < klines_trend_period:
            return False

        last_period_slice = last_period[0][1]
        # i