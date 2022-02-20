""" Coin class """

from typing import Dict, List, Optional
from lib.helpers import add_100


class Coin:  # pylint: disable=too-few-public-methods
    """Coin Class"""

    offset: Optional[Dict[str, int]] = {"s": 60, "m": 3600, "h": 86400}

    def __init__(
        self,
        symbol: str,
        date: float,
        market_price: float,
        buy_at: float,
        sell_at: float,
        stop_loss: float,
        trail_target_sell_percentage: float,
        trail_recovery_percentage: float,
        soft_limit_holding_time: int,
        hard_limit_holding_time: int,
        naughty_timeout: int,
        klines_trend_period: str,
        klines_slice_percentage_change: float,
    ) -> None:
        """Coin object"""
        self.symbol = symbol
        # number of units of a coin held
        self.volume: float = float(0)
        # what price we bought the coin
        self.bought_at: float = float(0)
        # minimum coin price recorded since reset
        self.min = float(market_price)
     