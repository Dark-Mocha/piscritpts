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

        u