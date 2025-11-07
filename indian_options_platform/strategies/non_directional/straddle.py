"""
Straddle Strategy
High volatility play - profits from large moves in either direction

Types:
1. Long Straddle: Buy ATM Call + Buy ATM Put
2. Short Straddle: Sell ATM Call + Sell ATM Put

Long Straddle:
- Max Profit: Unlimited
- Max Loss: Total premium paid
- Best when expecting big move but uncertain of direction
- Best before major events (earnings, budget, election results)

Short Straddle:
- Max Profit: Total premium received
- Max Loss: Unlimited
- Best in low volatility / range-bound markets
- High risk strategy (undefined risk)
"""

from ..base_strategy import BaseStrategy, Position, OptionType, PositionType
from typing import Optional


class Straddle(BaseStrategy):
    """
    Straddle Strategy Implementation

    Long Straddle Example (Nifty @ 19500):
    - Buy 19500 CE @ ₹150
    - Buy 19500 PE @ ₹140

    Total Cost: ₹290 * 75 = ₹21,750
    Breakevens: 19210, 19790
    Max Profit: Unlimited
    Max Loss: ₹21,750
    """

    def __init__(self,
                 strike: float,
                 call_premium: float,
                 put_premium: float,
                 is_long: bool = True,
                 quantity: int = 1,
                 lot_size: int = 75):
        """
        Initialize Straddle

        Parameters:
        -----------
        strike : float
            ATM strike price
        call_premium : float
            Call option premium
        put_premium : float
            Put option premium
        is_long : bool
            True for Long Straddle, False for Short Straddle
        quantity : int
            Number of straddles
        lot_size : int
            Lot size (default: 75 for Nifty)
        """
        strategy_type = "Long Straddle" if is_long else "Short Straddle"
        super().__init__(
            name=strategy_type,
            description=f"{'Bullish' if is_long else 'Bearish'} volatility play"
        )

        position_type = PositionType.LONG if is_long else PositionType.SHORT

        # Add Call position
        self.add_position(Position(
            strike=strike,
            option_type=OptionType.CALL,
            position_type=position_type,
            premium=call_premium,
            quantity=quantity,
            lot_size=lot_size
        ))

        # Add Put position
        self.add_position(Position(
            strike=strike,
            option_type=OptionType.PUT,
            position_type=position_type,
            premium=put_premium,
            quantity=quantity,
            lot_size=lot_size
        ))

        self.strike = strike
        self.is_long = is_long

    @classmethod
    def long_straddle(cls, atm_strike: float, call_premium: float,
                     put_premium: float, quantity: int = 1,
                     lot_size: int = 75) -> 'Straddle':
        """Create Long Straddle"""
        return cls(atm_strike, call_premium, put_premium,
                  is_long=True, quantity=quantity, lot_size=lot_size)

    @classmethod
    def short_straddle(cls, atm_strike: float, call_premium: float,
                      put_premium: float, quantity: int = 1,
                      lot_size: int = 75) -> 'Straddle':
        """Create Short Straddle"""
        return cls(atm_strike, call_premium, put_premium,
                  is_long=False, quantity=quantity, lot_size=lot_size)

    def required_move(self) -> dict:
        """
        Calculate required move for profitability

        Returns:
        --------
        dict : Required moves in points and percentage
        """
        total_premium = abs(self.net_premium() / (self.positions[0].lot_size * self.positions[0].quantity))

        breakevens = self.breakeven_points()

        if len(breakevens) >= 2:
            lower_be, upper_be = breakevens[0], breakevens[-1]
            required_move_pct = ((total_premium / self.strike) * 100)

            return {
                'total_premium_per_share': total_premium,
                'lower_breakeven': lower_be,
                'upper_breakeven': upper_be,
                'required_move_points': total_premium,
                'required_move_pct': required_move_pct,
                'breakeven_range': upper_be - lower_be
            }

        return {}

    def iv_analysis(self, current_iv: float, historical_iv_avg: float) -> dict:
        """
        Analyze if IV is favorable for the strategy

        Parameters:
        -----------
        current_iv : float
            Current implied volatility
        historical_iv_avg : float
            Historical average IV

        Returns:
        --------
        dict : IV analysis
        """
        iv_ratio = current_iv / historical_iv_avg if historical_iv_avg > 0 else 1.0

        if self.is_long:
            # Long straddle: want low IV (cheap options)
            favorable = current_iv < historical_iv_avg
            recommendation = "FAVORABLE" if favorable else "UNFAVORABLE"
            reason = "IV is below average (cheap options)" if favorable else "IV is above average (expensive options)"
        else:
            # Short straddle: want high IV (expensive options to sell)
            favorable = current_iv > historical_iv_avg
            recommendation = "FAVORABLE" if favorable else "UNFAVORABLE"
            reason = "IV is above average (expensive options to sell)" if favorable else "IV is below average (cheap options)"

        return {
            'current_iv': current_iv,
            'historical_avg_iv': historical_iv_avg,
            'iv_ratio': iv_ratio,
            'favorable': favorable,
            'recommendation': recommendation,
            'reason': reason
        }

    def print_detailed_summary(self, current_iv: Optional[float] = None,
                              historical_iv: Optional[float] = None) -> None:
        """Print detailed Straddle summary"""
        self.print_summary()

        print("\n" + "=" * 80)
        print("STRADDLE SPECIFIC METRICS:")
        print("=" * 80)

        move_metrics = self.required_move()

        if move_metrics:
            print(f"{'ATM Strike':<30}: ₹{self.strike:,.0f}")
            print(f"{'Total Premium/Share':<30}: ₹{move_metrics['total_premium_per_share']:,.2f}")
            print(f"{'Lower Breakeven':<30}: ₹{move_metrics['lower_breakeven']:,.2f}")
            print(f"{'Upper Breakeven':<30}: ₹{move_metrics['upper_breakeven']:,.2f}")
            print(f"{'Breakeven Range':<30}: {move_metrics['breakeven_range']:,.0f} points")
            print(f"{'Required Move':<30}: {move_metrics['required_move_points']:,.0f} points ({move_metrics['required_move_pct']:.2f}%)")

        if current_iv and historical_iv:
            print("\n" + "-" * 80)
            print("IV ANALYSIS:")
            print("-" * 80)

            iv_analysis = self.iv_analysis(current_iv, historical_iv)

            print(f"{'Current IV':<30}: {iv_analysis['current_iv']*100:.2f}%")
            print(f"{'Historical Avg IV':<30}: {iv_analysis['historical_avg_iv']*100:.2f}%")
            print(f"{'IV Ratio':<30}: {iv_analysis['iv_ratio']:.2f}x")
            print(f"{'Trade Quality':<30}: {iv_analysis['recommendation']}")
            print(f"{'Reason':<30}: {iv_analysis['reason']}")

        print("\n" + "=" * 80)
        print("TRADE RECOMMENDATIONS:")
        print("=" * 80)

        if self.is_long:
            print("LONG STRADDLE:")
            print("✓ Enter before major events (earnings, budget, RBI policy)")
            print("✓ Buy when IV percentile < 30% (cheap options)")
            print("✓ Exit immediately after the event (before IV crush)")
            print("✓ Manage if moves to 50% of max profit")
            print("✓ Stop loss at 50-75% of premium paid")
            print("⚠ Beware of IV crush after events")
        else:
            print("SHORT STRADDLE:")
            print("⚠ HIGH RISK - Unlimited loss potential")
            print("✓ Enter when IV percentile > 70% (expensive options)")
            print("✓ Best in range-bound markets with low volatility")
            print("✓ Use stop loss at 2x premium received")
            print("✓ Consider Iron Condor instead for defined risk")
            print("✓ Exit at 50% of max profit")

        print("=" * 80)


class LongStraddle(Straddle):
    """Long Straddle - Buy ATM Call + Buy ATM Put"""

    def __init__(self, strike: float, call_premium: float,
                 put_premium: float, quantity: int = 1, lot_size: int = 75):
        super().__init__(strike, call_premium, put_premium,
                        is_long=True, quantity=quantity, lot_size=lot_size)


class ShortStraddle(Straddle):
    """Short Straddle - Sell ATM Call + Sell ATM Put"""

    def __init__(self, strike: float, call_premium: float,
                 put_premium: float, quantity: int = 1, lot_size: int = 75):
        super().__init__(strike, call_premium, put_premium,
                        is_long=False, quantity=quantity, lot_size=lot_size)


if __name__ == "__main__":
    # Example 1: Long Straddle (expecting big move)
    print("EXAMPLE 1: Long Straddle (Before Budget Day)")
    print()

    long_straddle = LongStraddle(
        strike=19500,
        call_premium=150,
        put_premium=140,
        quantity=1,
        lot_size=75
    )

    long_straddle.print_detailed_summary(
        current_iv=0.12,  # 12% current IV
        historical_iv=0.15  # 15% historical avg
    )

    # Example 2: Short Straddle (expecting no movement)
    print("\n\n")
    print("EXAMPLE 2: Short Straddle (High IV, Range-bound Expected)")
    print()

    short_straddle = ShortStraddle(
        strike=19500,
        call_premium=180,
        put_premium=170,
        quantity=1,
        lot_size=75
    )

    short_straddle.print_detailed_summary(
        current_iv=0.20,  # 20% current IV
        historical_iv=0.15  # 15% historical avg
    )

    # Uncomment to see payoff diagram
    # long_straddle.plot_payoff(current_spot=19500)
    # short_straddle.plot_payoff(current_spot=19500)
