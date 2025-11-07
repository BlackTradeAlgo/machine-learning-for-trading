"""
Unified Options Trading Strategies Library
Complete collection optimized for INTRADAY trading on Indian markets

This library consolidates all options strategies with a focus on intraday execution.
All strategies are integrated with Angel One API for live trading.

Strategy Categories:
-------------------
1. HFT/Scalping (Pure Intraday):
   - GammaScalpingStrategy: Delta-neutral with frequent adjustments
   - ZeroDTEStrategy: Expiry day trading (0 Days To Expiry)

2. Range-Bound (Intraday + Multi-day):
   - IronCondor: Limited risk/reward, best in low volatility

3. Volatility (Intraday scalps):
   - LongStraddle: Profit from big moves (long volatility)
   - ShortStraddle: Profit from range-bound (short volatility)

Quick Start:
-----------
>>> from strategies import select_strategy
>>>
>>> # Auto-select best strategy for current market
>>> strategy = select_strategy(
>>>     spot=19500,
>>>     iv=0.18,
>>>     trend='sideways',
>>>     time_of_day='10:00'
>>> )
>>>
>>> # Or use specific strategy
>>> from strategies import GammaScalpingStrategy
>>> gamma = GammaScalpingStrategy(spot_price=19500, ...)

Intraday Optimization:
---------------------
All strategies support intraday parameters:
- Auto exit by 3:15 PM
- Quick adjustment thresholds
- Reduced holding time targets
"""

from .base_strategy import (
    BaseStrategy,
    Position,
    OptionType,
    PositionType
)

from .non_directional.iron_condor import IronCondor
from .non_directional.straddle import (
    Straddle,
    LongStraddle,
    ShortStraddle
)

from .hft_scalping.gamma_scalping import GammaScalpingStrategy
from .hft_scalping.zero_dte_strategy import ZeroDTEStrategy


# ==================== STRATEGY SELECTION HELPERS ====================

def select_strategy(spot: float,
                   iv: float,
                   trend: str = 'sideways',
                   time_of_day: str = None,
                   risk_appetite: str = 'moderate') -> dict:
    """
    Recommend best intraday strategy based on market conditions

    Parameters:
    -----------
    spot : float
        Current spot price
    iv : float
        Current implied volatility (e.g., 0.15 for 15%)
    trend : str
        Market trend: 'up', 'down', 'sideways', 'volatile'
    time_of_day : str
        Time in HH:MM format (e.g., '10:30')
    risk_appetite : str
        'conservative', 'moderate', 'aggressive'

    Returns:
    --------
    dict : Strategy recommendation with setup parameters

    Examples:
    ---------
    >>> # Volatile market, morning time
    >>> rec = select_strategy(19500, 0.20, 'volatile', '10:00', 'moderate')
    >>> print(rec['strategy_name'])
    'GammaScalpingStrategy'

    >>> # Range-bound, high IV
    >>> rec = select_strategy(19500, 0.18, 'sideways', '11:00', 'conservative')
    >>> print(rec['strategy_name'])
    'IronCondor'
    """
    from datetime import datetime, time as dt_time

    # Parse time
    current_time = None
    if time_of_day:
        hour, minute = map(int, time_of_day.split(':'))
        current_time = dt_time(hour, minute)

    recommendations = []

    # Check if it's expiry day (Thursday for Nifty weekly)
    is_expiry_day = datetime.now().weekday() == 3  # Thursday

    # Time-based filtering
    if current_time and current_time >= dt_time(15, 0):
        return {
            'strategy_name': None,
            'reason': 'Too late in the day for new trades',
            'recommendation': 'Exit existing positions by 3:15 PM'
        }

    # === EXPIRY DAY (Thursday) ===
    if is_expiry_day and current_time and current_time < dt_time(15, 20):
        recommendations.append({
            'strategy_name': 'ZeroDTEStrategy',
            'class': ZeroDTEStrategy,
            'score': 95,
            'reason': 'Expiry day - Maximum theta decay',
            'setup': {
                'strategy_type': 'credit_spread' if trend == 'sideways' else 'atm_scalp',
                'risk_per_trade': 5000,
                'profit_target_pct': 50,
                'stop_loss_pct': 100
            },
            'capital_required': '₹5,000-10,000',
            'expected_return': '20-50% per trade',
            'risk_level': 'HIGH'
        })

    # === GAMMA SCALPING (High volatility intraday) ===
    if iv >= 0.15 and trend in ['volatile', 'up', 'down']:
        score = 85
        if trend == 'volatile':
            score = 90
        if risk_appetite == 'aggressive':
            score += 5

        recommendations.append({
            'strategy_name': 'GammaScalpingStrategy',
            'class': GammaScalpingStrategy,
            'score': score,
            'reason': 'High volatility perfect for gamma scalping',
            'setup': {
                'delta_threshold': 0.15,
                'profit_target_pct': 0.5,
                'max_adjustments': 10
            },
            'capital_required': '₹15,000-30,000',
            'expected_return': '1-3% per day',
            'risk_level': 'MODERATE'
        })

    # === IRON CONDOR (Range-bound, low volatility) ===
    if trend == 'sideways' and iv < 0.20:
        score = 80
        if iv > 0.15:  # Higher IV = better premium
            score += 10
        if risk_appetite == 'conservative':
            score += 5

        recommendations.append({
            'strategy_name': 'IronCondor',
            'class': IronCondor,
            'score': score,
            'reason': 'Range-bound market with decent premiums',
            'setup': {
                'distance_from_spot': 150,
                'put_width': 100,
                'call_width': 100
            },
            'capital_required': '₹20,000-40,000',
            'expected_return': '2-5% per day',
            'risk_level': 'LOW-MODERATE',
            'note': 'Best if held to expiry, but can exit intraday at 50% profit'
        })

    # === LONG STRADDLE (Expecting big move, low IV) ===
    if trend == 'volatile' and iv < 0.15:
        score = 75
        if risk_appetite == 'aggressive':
            score += 5

        recommendations.append({
            'strategy_name': 'LongStraddle',
            'class': LongStraddle,
            'score': score,
            'reason': 'Low IV - cheap options before expected volatility',
            'setup': {
                'strike': round(spot / 50) * 50,  # ATM
                'exit_target_pct': 15
            },
            'capital_required': '₹15,000-25,000',
            'expected_return': '5-15% per trade',
            'risk_level': 'MODERATE-HIGH',
            'note': 'Exit quickly when profit target hit or if no move within 1 hour'
        })

    # === SHORT STRADDLE (Range-bound, high IV) ===
    if trend == 'sideways' and iv > 0.18 and risk_appetite == 'aggressive':
        recommendations.append({
            'strategy_name': 'ShortStraddle',
            'class': ShortStraddle,
            'score': 70,
            'reason': 'High IV - expensive options to sell',
            'setup': {
                'strike': round(spot / 50) * 50,  # ATM
                'stop_loss_multiplier': 2
            },
            'capital_required': '₹20,000-35,000',
            'expected_return': '3-8% per day',
            'risk_level': 'VERY HIGH',
            'warning': '⚠️ UNLIMITED RISK - Use strict stop loss'
        })

    # Sort by score
    recommendations.sort(key=lambda x: x['score'], reverse=True)

    if not recommendations:
        return {
            'strategy_name': None,
            'reason': 'No favorable strategy for current conditions',
            'recommendation': 'Wait for better setup or reduce position size'
        }

    return recommendations[0]


def get_strategy_comparison() -> str:
    """
    Get comparison table of all intraday strategies

    Returns:
    --------
    str : Formatted comparison table
    """
    comparison = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    INTRADAY STRATEGIES COMPARISON TABLE                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────┬──────────────┬──────────────┬─────────────┬─────────────┐
│ Strategy            │ Best Market  │ Capital Req  │ Risk Level  │ Time Frame  │
├─────────────────────┼──────────────┼──────────────┼─────────────┼─────────────┤
│ Gamma Scalping      │ High Vol     │ ₹15K-30K     │ MODERATE    │ Full Day    │
│                     │ Volatile     │              │             │ (multiple   │
│                     │              │              │             │ adjustments)│
├─────────────────────┼──────────────┼──────────────┼─────────────┼─────────────┤
│ Zero DTE            │ Expiry Day   │ ₹5K-10K      │ HIGH        │ 9:30-3:20   │
│ (0 Days to Expiry)  │ Sideways/    │              │             │ (Thu only)  │
│                     │ Trending     │              │             │             │
├─────────────────────┼──────────────┼──────────────┼─────────────┼─────────────┤
│ Iron Condor         │ Range-bound  │ ₹20K-40K     │ LOW-MOD     │ Can hold    │
│                     │ Low Vol      │              │             │ to expiry   │
├─────────────────────┼──────────────┼──────────────┼─────────────┼─────────────┤
│ Long Straddle       │ Before Event │ ₹15K-25K     │ MODERATE    │ 10-60 min   │
│                     │ Low IV       │              │             │ (quick in/  │
│                     │              │              │             │ out)        │
├─────────────────────┼──────────────┼──────────────┼─────────────┼─────────────┤
│ Short Straddle      │ High IV      │ ₹20K-35K     │ VERY HIGH   │ Full Day    │
│                     │ Range-bound  │              │ (Unlimited) │ (watch      │
│                     │              │              │             │ closely)    │
└─────────────────────┴──────────────┴──────────────┴─────────────┴─────────────┘

Expected Returns (Intraday):
─────────────────────────────
• Gamma Scalping:      1-3% per day  (from hedge profits)
• Zero DTE:            20-50% per trade (or -100% loss)
• Iron Condor:         2-5% per day  (if hit profit target)
• Long Straddle:       5-15% per trade (quick scalp)
• Short Straddle:      3-8% per day  (theta decay)

Best Practices:
──────────────
✓ Always use stop losses
✓ Exit all positions by 3:15 PM
✓ Risk max 2% of capital per trade
✓ Don't trade first 15 minutes (9:15-9:30)
✓ Track daily loss limits
✓ Start with paper trading first

⚠️  All returns are NOT guaranteed. Options trading is risky.
"""
    return comparison


def print_strategy_guide():
    """Print comprehensive intraday strategy selection guide"""
    print(get_strategy_comparison())

    print("\n" + "="*80)
    print("STRATEGY SELECTION FLOWCHART")
    print("="*80)
    print("""
START → Is it expiry day (Thursday)?
        │
        ├─ YES → ZeroDTEStrategy ✓
        │        (Best for expiry day trading)
        │
        └─ NO → Check market volatility:
                │
                ├─ HIGH VOLATILITY (IV > 15%) + Trending?
                │  └─ YES → GammaScalpingStrategy ✓
                │           (Scalp gamma with hedges)
                │
                ├─ RANGE-BOUND + Normal/Low Vol (IV < 20%)?
                │  └─ YES → IronCondor ✓
                │           (Collect premium in range)
                │
                ├─ EXPECTING BIG MOVE + Low IV (< 15%)?
                │  └─ YES → LongStraddle ✓
                │           (Buy cheap options, exit fast)
                │
                └─ HIGH IV (> 18%) + Range-bound + Aggressive?
                   └─ YES → ShortStraddle ⚠️
                            (High risk - unlimited loss!)

    """)
    print("="*80)


# ==================== MODULE EXPORTS ====================

__all__ = [
    # Base classes
    'BaseStrategy',
    'Position',
    'OptionType',
    'PositionType',

    # Intraday strategies (primary)
    'GammaScalpingStrategy',
    'ZeroDTEStrategy',

    # Range-bound strategies
    'IronCondor',

    # Volatility strategies
    'Straddle',
    'LongStraddle',
    'ShortStraddle',

    # Helper functions
    'select_strategy',
    'get_strategy_comparison',
    'print_strategy_guide'
]


# Version
__version__ = '2.0.0'  # Unified intraday-focused version
