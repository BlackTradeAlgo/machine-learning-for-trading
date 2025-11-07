"""
HFT / Scalping Strategies for Intraday Options Trading
Pure intraday strategies optimized for Indian markets

These are the PRIMARY strategies for intraday trading:

1. GammaScalpingStrategy
   - Delta-neutral strategy with frequent adjustments
   - Profits from volatility by hedging with futures
   - Best in high volatility, trending markets
   - Time: Full day (9:30 AM - 3:15 PM)
   - Capital: Rs 15,000-30,000
   - Expected: 1-3% per day

2. ZeroDTEStrategy
   - Zero Days To Expiry (0DTE) - Expiry day only
   - Maximum theta decay on expiry day (Thursday)
   - Multiple sub-strategies: credit spreads, debit spreads, ATM scalps
   - Time: Expiry day only (9:30 AM - 3:20 PM)
   - Capital: Rs 5,000-10,000
   - Expected: 20-50% per trade (HIGH RISK)

Usage:
------
>>> from strategies.hft_scalping import GammaScalpingStrategy, ZeroDTEStrategy
>>>
>>> # Gamma Scalping (for volatile days)
>>> gamma = GammaScalpingStrategy(
>>>     spot_price=19500,
>>>     atm_strike=19500,
>>>     atm_call_price=150,
>>>     atm_put_price=140,
>>>     delta_threshold=0.15,
>>>     profit_target_pct=0.5
>>> )
>>>
>>> # Zero DTE (for expiry day)
>>> zero_dte = ZeroDTEStrategy(
>>>     spot_price=19500,
>>>     strategy_type='credit_spread',
>>>     risk_per_trade=5000,
>>>     profit_target_pct=50,
>>>     stop_loss_pct=100
>>> )
"""

from .gamma_scalping import GammaScalpingStrategy
from .zero_dte_strategy import ZeroDTEStrategy

__all__ = [
    'GammaScalpingStrategy',
    'ZeroDTEStrategy'
]
