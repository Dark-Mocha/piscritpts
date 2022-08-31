""" bot buy strategy file """
from lib.bot import Bot
from lib.coin import Coin
from lib.helpers import c_from_timestamp, logging, percent


class Strategy(Bot):
    """BuyDropSellRecoveryStrategy"""

    def buy_strategy(self, coin: Coin) -> bool:
        """BuyDropSellRecoveryStrategy buy_strategy

        this strategy, looks for the recovery point in price for a coin after
        a drop in price.
        when a coin drops by BUY_AT_PERCENTAGE the bot marks that coin
        as TARGET_DIP, and then monitors its price recording the lowest
        price it sees(the dip).
        As soon the coin goes above the dip by TRAIL_RECOVERY_PERCENTAGE
        the bot buys the coin."""

        if (
            # as soon the price goes below BUY_AT_PERCENTAGE, mark coin as
            # TARGET_DIP
            coin.status == ""
            and not coin.naughty
            and coin.price < percent(coin.buy_at_percentage, coin.max)
        ):
            coin.dip = coin.price
            logging.info(
                f"{c_from_timestamp(coin.date)}: {coin.symbol} [{coin.status}] "
                + f"-> [TARGET_DIP] ({coin.price})"
            )
            coin.status = "TARGET_DIP"

        if coin.status != "TARGET_DIP