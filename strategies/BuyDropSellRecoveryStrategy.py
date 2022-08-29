""" bot buy strategy file """
from lib.bot import Bot
from lib.coin import Coin
from lib.helpers import c_from_timestamp, logging, percent


class Strategy(Bot):
    """BuyDropSellRecoveryStrategy"""

    def buy_strategy(self, coin: Coin) -> bool:
        """BuyDropSellRecoveryStrategy buy_strategy

        this strategy, looks for the recovery point in price for a c