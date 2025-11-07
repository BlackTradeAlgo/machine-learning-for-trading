"""
Iron Condor Strategy
Popular range-bound/neutral strategy

Description:
Combination of Bull Put Spread + Bear Call Spread
Profits when underlying stays within a range

Construction:
1. Sell OTM Put (lower strike)
2. Buy further OTM Put (protection)
3. Sell OTM Call (upper strike)
4. Buy further OTM Call (protection)

Characteristics:
- Limited profit (net credit received)
- Limited risk (width of spread - net credit)
- Profits from low volatility / range-bound market
- High probability of profit
- Best in low IV environments
"""

from ..base_strategy import BaseStrategy, Position, OptionType, PositionType
from typing import Optional


class IronCondor(BaseStrategy):
    """
    Iron Condor Strategy Implementation

    Example (Nifty @ 19500):
    - Buy 19300 PE @ ₹30
    - Sell 19400 PE @ ₹60
    - Sell 19600 CE @ ₹55
    - Buy 19700 CE @ ₹25

    Net Credit: (60 + 55 - 30 - 25) = ₹60 per share
    Total Credit: ₹60 * 75 (lot size) = ₹4,500
    Max Profit: ₹4,500
    Max Loss: (100 - 60) * 75 = ₹3,000
    Profit Range: 19340 to 19660 (approx)
    """

    def __init__(self,
                 lower_long_put_strike: float,
                 lower_short_put_strike: float,
                 upper_short_call_strike: float,
                 upper_long_call_strike: float,
                 lower_long_put_premium: float,
                 lower_short_put_premium: float,
                 upper_short_call_premium: float,
                 upper_long_call_premium: float,
                 quantity: int = 1,
                 lot_size: int = 75):
        """
        Initialize Iron Condor

        Parameters:
        -----------
        lower_long_put_strike : float
            Strike of long put (lowest strike)
        lower_short_put_strike : float
            Strike of short put
        upper_short_call_strike : float
            Strike of short call
        upper_long_call_strike : float
            Strike of long call (highest strike)
        *_premium : float
            Premiums for each option
        quantity : int
            Number of Iron Condors
        lot_size : int
            Lot size (default: 75 for Nifty)
        """
        super().__init__(
            name="Iron Condor",
            description="Range-bound strategy with limited risk and reward"
        )

        # Validate strikes
        assert lower_long_put_strike < lower_short_put_strike < upper_short_call_strike < upper_long_call_strike, \
            "Invalid strike order"

        # Buy lower put (protection)
        self.add_position(Position(
            strike=lower_long_put_strike,
            option_type=OptionType.PUT,
            position_type=PositionType.LONG,
            premium=lower_long_put_premium,
            quantity=quantity,
            lot_size=lot_size
        ))

        # Sell put (credit)
        self.add_position(Position(
            strike=lower_short_put_strike,
            option_type=OptionType.PUT,
            position_type=PositionType.SHORT,
            premium=lower_short_put_premium,
            quantity=quantity,
            lot_size=lot_size
        ))

        # Sell call (credit)
        self.add_position(Position(
            strike=upper_short_call_strike,
            option_type=OptionType.CALL,
            position_type=PositionType.SHORT,
            premium=upper_short_call_premium,
            quantity=quantity,
            lot_size=lot_size
        ))

        # Buy higher call (protection)
        self.add_position(Position(
            strike=upper_long_call_strike,
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            premium=upper_long_call_premium,
            quantity=quantity,
            lot_size=lot_size
        ))

        self.lower_long_put_strike = lower_long_put_strike
        self.lower_short_put_strike = lower_short_put_strike
        self.upper_short_call_strike = upper_short_call_strike
        self.upper_long_call_strike = upper_long_call_strike

    @classmethod
    def create_balanced(cls,
                       spot: float,
                       put_width: float = 100,
                       call_width: float = 100,
                       distance_from_spot: float = 100,
                       put_credit: float = 30,
                       call_credit: float = 30,
                       quantity: int = 1,
                       lot_size: int = 75) -> 'IronCondor':
        """
        Create a balanced Iron Condor around current spot

        Parameters:
        -----------
        spot : float
            Current spot price
        put_width : float
            Width of put spread
        call_width : float
            Width of call spread
        distance_from_spot : float
            Distance of short strikes from spot
        put_credit : float
            Net credit from put spread
        call_credit : float
            Net credit from call spread
        """
        # Short strikes
        short_put_strike = spot - distance_from_spot
        short_call_strike = spot + distance_from_spot

        # Long strikes (protection)
        long_put_strike = short_put_strike - put_width
        long_call_strike = short_call_strike + call_width

        # Calculate premiums (simplified)
        # In reality, you'd fetch these from market data
        short_put_premium = put_credit + 10
        long_put_premium = 10
        short_call_premium = call_credit + 10
        long_call_premium = 10

        return cls(
            lower_long_put_strike=long_put_strike,
            lower_short_put_strike=short_put_strike,
            upper_short_call_strike=short_call_strike,
            upper_long_call_strike=long_call_strike,
            lower_long_put_premium=long_put_premium,
            lower_short_put_premium=short_put_premium,
            upper_short_call_premium=short_call_premium,
            upper_long_call_premium=long_call_premium,
            quantity=quantity,
            lot_size=lot_size
        )

    def profit_zone(self) -> tuple:
        """Return the profit zone (range where strategy is profitable)"""
        breakevens = self.breakeven_points()
        if len(breakevens) >= 2:
            return (breakevens[0], breakevens[-1])
        return (0, 0)

    def max_profit_zone(self) -> tuple:
        """Return the maximum profit zone"""
        return (self.lower_short_put_strike, self.upper_short_call_strike)

    def risk_metrics(self) -> dict:
        """Calculate specific risk metrics for Iron Condor"""
        net_credit = self.net_premium()
        put_spread_width = self.lower_short_put_strike - self.lower_long_put_strike
        call_spread_width = self.upper_long_call_strike - self.upper_short_call_strike

        max_profit = net_credit
        max_loss_put_side = (put_spread_width * self.positions[0].lot_size * self.positions[0].quantity) - net_credit
        max_loss_call_side = (call_spread_width * self.positions[0].lot_size * self.positions[0].quantity) - net_credit

        profit_zone = self.profit_zone()
        max_profit_zone = self.max_profit_zone()

        return {
            'net_credit': net_credit,
            'max_profit': max_profit,
            'max_loss_put_side': -max_loss_put_side,
            'max_loss_call_side': -max_loss_call_side,
            'max_loss': min(-max_loss_put_side, -max_loss_call_side),
            'put_spread_width': put_spread_width,
            'call_spread_width': call_spread_width,
            'profit_zone': profit_zone,
            'max_profit_zone': max_profit_zone,
            'profit_zone_width': profit_zone[1] - profit_zone[0] if profit_zone[0] > 0 else 0
        }

    def print_detailed_summary(self) -> None:
        """Print detailed Iron Condor summary"""
        self.print_summary()

        print("\n" + "=" * 80)
        print("IRON CONDOR SPECIFIC METRICS:")
        print("=" * 80)

        metrics = self.risk_metrics()

        print(f"{'Put Spread Width':<30}: {metrics['put_spread_width']:.0f} points")
        print(f"{'Call Spread Width':<30}: {metrics['call_spread_width']:.0f} points")
        print(f"{'Profit Zone':<30}: ₹{metrics['profit_zone'][0]:,.0f} - ₹{metrics['profit_zone'][1]:,.0f}")
        print(f"{'Profit Zone Width':<30}: {metrics['profit_zone_width']:.0f} points")
        print(f"{'Max Profit Zone':<30}: ₹{metrics['max_profit_zone'][0]:,.0f} - ₹{metrics['max_profit_zone'][1]:,.0f}")
        print(f"{'Max Loss (Put Side)':<30}: ₹{metrics['max_loss_put_side']:,.2f}")
        print(f"{'Max Loss (Call Side)':<30}: ₹{metrics['max_loss_call_side']:,.2f}")

        print("\n" + "=" * 80)
        print("TRADE RECOMMENDATIONS:")
        print("=" * 80)
        print("✓ Enter when IV Rank > 50% (high IV environment)")
        print("✓ Target profit: 50-75% of max profit")
        print("✓ Exit if one side breaches short strike")
        print("✓ Best for low volatility, range-bound markets")
        print("✓ Manage at 21 DTE if using weekly options")
        print("=" * 80)


if __name__ == "__main__":
    # Example 1: Manual Iron Condor
    print("EXAMPLE 1: Manual Iron Condor (Nifty @ 19500)")
    print()

    ic = IronCondor(
        lower_long_put_strike=19300,
        lower_short_put_strike=19400,
        upper_short_call_strike=19600,
        upper_long_call_strike=19700,
        lower_long_put_premium=30,
        lower_short_put_premium=60,
        upper_short_call_premium=55,
        upper_long_call_premium=25,
        quantity=1,
        lot_size=75
    )

    ic.print_detailed_summary()

    # Example 2: Balanced Iron Condor
    print("\n\n")
    print("EXAMPLE 2: Balanced Iron Condor (Auto-generated)")
    print()

    ic_balanced = IronCondor.create_balanced(
        spot=19500,
        put_width=100,
        call_width=100,
        distance_from_spot=150,
        put_credit=30,
        call_credit=30,
        quantity=2,
        lot_size=75
    )

    ic_balanced.print_detailed_summary()

    # Uncomment to see payoff diagram
    # ic.plot_payoff(current_spot=19500)
