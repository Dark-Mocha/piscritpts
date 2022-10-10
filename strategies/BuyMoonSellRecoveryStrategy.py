""" bot buy strategy file """
from lib.bot import Bot
from lib.coin import Coin
from lib.helpers import percent


class Strategy(Bot):
    """BuyMoonSellRecoveryStrategy"""

    def buy_strategy(self, coin: Coin) -> bool:
        """BuyMoonSellRecove