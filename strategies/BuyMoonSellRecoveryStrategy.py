""" bot buy strategy file """
from lib.bot import Bot
from lib.coin import Coin
from lib.helpers import percent


class Strategy(Bot):
    """BuyMoonSellRecoveryStrategy"""

    def buy_strategy(self, coin: Coin) -> bool:
        """BuyMoonSellRecoveryStrategy buy_strategy

        this strategy looks for a price change between the last price recorded
        the current price, and if it was gone up by BUY_AT_PERCENTAGE
        it buys the coin.

        """