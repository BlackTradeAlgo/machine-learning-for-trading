"""
Options Trading Strategies Library
Comprehensive collection of strategies for Indian markets
"""

from .base_strategy import BaseStrategy, Position
from .directional import LongCall, LongPut, BullCallSpread, BearPutSpread
from .non_directional import IronCondor, Straddle, Strangle, Butterfly
from .volatility import LongStraddle, ShortStraddle, CalendarSpread
from .hft_scalping import GammaScalping, ThetaHarvesting

__all__ = [
    'BaseStrategy',
    'Position',
    'LongCall',
    'LongPut',
    'BullCallSpread',
    'BearPutSpread',
    'IronCondor',
    'Straddle',
    'Strangle',
    'Butterfly',
    'LongStraddle',
    'ShortStraddle',
    'CalendarSpread',
    'GammaScalping',
    'ThetaHarvesting'
]
