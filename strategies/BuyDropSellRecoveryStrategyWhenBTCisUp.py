""" bot buy strategy file """
from lib.bot import Bot
from lib.coin import Coin
from lib.helpers import c_from_timestamp, logging, percent


class Strategy(Bot):
    """BuyDropSellRecoveryStrategyWhenBTCisUp"""

    def buy_strategy(self, coin: Coin) -> bool:
        """BuyDropSellRecoveryStrategyWhenBTCisUp buy_strategy

        this strategy 