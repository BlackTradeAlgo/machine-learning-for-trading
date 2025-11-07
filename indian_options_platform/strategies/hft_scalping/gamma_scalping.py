"""
Gamma Scalping Strategy (Intraday)
Delta-neutral strategy that profits from volatility

Concept:
- Buy ATM straddle (long gamma position)
- When spot moves, delta changes (due to gamma)
- Hedge by trading underlying/futures
- Capture profits from delta adjustments
- Best in high volatility markets

Risk: Limited (premium paid)
Reward: Unlimited (from scalping)
Time: Intraday (5-30 minutes per adjustment)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GammaScalpingStrategy:
    """
    Gamma Scalping Intraday Strategy

    Steps:
    1. Buy ATM call + ATM put (long gamma)
    2. Calculate portfolio delta
    3. When delta exceeds threshold, hedge with futures
    4. Take profit on hedge when spot reverts
    5. Repeat throughout the day

    Parameters:
    -----------
    spot_price : float
        Current spot price
    atm_call_price : float
        ATM call premium
    atm_put_price : float
        ATM put premium
    delta_threshold : float
        Delta threshold for hedging (e.g., 0.2 = 20 delta)
    profit_target_pct : float
        Profit target on hedges (%)
    max_adjustments : int
        Maximum adjustments per day

    Example:
    --------
    strategy = GammaScalpingStrategy(
        spot_price=19500,
        atm_call_price=150,
        atm_put_price=140,
        delta_threshold=0.15,
        profit_target_pct=0.5
    )

    # Initialize position
    strategy.enter_position()

    # Throughout the day
    while market_open:
        current_spot = get_current_spot()
        action = strategy.check_adjustment(current_spot)

        if action:
            execute_hedge(action)
    """

    def __init__(self,
                 spot_price: float,
                 atm_strike: float,
                 atm_call_price: float,
                 atm_put_price: float,
                 call_delta: float = 0.5,
                 put_delta: float = -0.5,
                 call_gamma: float = 0.01,
                 put_gamma: float = 0.01,
                 lot_size: int = 75,
                 delta_threshold: float = 0.15,
                 profit_target_pct: float = 0.5,
                 max_adjustments: int = 10):
        """Initialize Gamma Scalping Strategy"""

        self.initial_spot = spot_price
        self.atm_strike = atm_strike
        self.atm_call_price = atm_call_price
        self.atm_put_price = atm_put_price
        self.call_delta = call_delta
        self.put_delta = put_delta
        self.call_gamma = call_gamma
        self.put_gamma = put_gamma
        self.lot_size = lot_size
        self.delta_threshold = delta_threshold
        self.profit_target_pct = profit_target_pct
        self.max_adjustments = max_adjustments

        # Position state
        self.position_active = False
        self.entry_cost = 0
        self.current_delta = 0
        self.futures_position = 0  # +ve = long, -ve = short
        self.futures_entry_price = 0
        self.adjustments_count = 0
        self.realized_pnl = 0

        # Track adjustments
        self.adjustment_history: list = []

    def enter_position(self) -> Dict:
        """
        Enter initial straddle position

        Returns:
        --------
        dict : Entry details
        """
        # Cost of straddle
        self.entry_cost = (self.atm_call_price + self.atm_put_price) * self.lot_size

        # Initial portfolio delta (should be near 0 for ATM straddle)
        self.current_delta = self.call_delta + self.put_delta

        self.position_active = True

        entry_details = {
            'timestamp': datetime.now(),
            'action': 'ENTER_STRADDLE',
            'spot': self.initial_spot,
            'strike': self.atm_strike,
            'call_price': self.atm_call_price,
            'put_price': self.atm_put_price,
            'total_cost': self.entry_cost,
            'initial_delta': self.current_delta
        }

        logger.info(f"✅ Entered gamma scalping position")
        logger.info(f"   Cost: ₹{self.entry_cost:,.2f}")
        logger.info(f"   Initial Delta: {self.current_delta:.4f}")

        return entry_details

    def update_greeks(self, spot: float, call_delta: float, put_delta: float,
                     call_gamma: float, put_gamma: float) -> None:
        """
        Update Greeks based on current spot price

        Parameters:
        -----------
        spot : float
            Current spot price
        call_delta : float
            Current call delta
        put_delta : float
            Current put delta
        call_gamma : float
            Current call gamma
        put_gamma : float
            Current put gamma
        """
        self.call_delta = call_delta
        self.put_delta = put_delta
        self.call_gamma = call_gamma
        self.put_gamma = put_gamma

        # Calculate portfolio delta
        options_delta = self.call_delta + self.put_delta

        # Add futures delta (if any)
        futures_delta = self.futures_position / self.lot_size  # Normalized

        self.current_delta = options_delta + futures_delta

    def check_adjustment(self, current_spot: float) -> Optional[Dict]:
        """
        Check if adjustment (hedge) is needed

        Parameters:
        -----------
        current_spot : float
            Current spot price

        Returns:
        --------
        dict or None : Adjustment action if needed
        """
        if not self.position_active:
            return None

        if self.adjustments_count >= self.max_adjustments:
            logger.warning("⚠️  Max adjustments reached for the day")
            return None

        # Check if delta exceeds threshold
        if abs(self.current_delta) > self.delta_threshold:
            # Need to hedge

            # Calculate hedge quantity
            # If delta is positive (bullish), sell futures to neutralize
            # If delta is negative (bearish), buy futures to neutralize
            hedge_quantity = -int(self.current_delta * self.lot_size)

            action = {
                'timestamp': datetime.now(),
                'action': 'HEDGE',
                'spot': current_spot,
                'portfolio_delta': self.current_delta,
                'hedge_side': 'SELL' if hedge_quantity < 0 else 'BUY',
                'hedge_quantity': abs(hedge_quantity),
                'reason': f"Delta {self.current_delta:.4f} exceeds threshold {self.delta_threshold}"
            }

            logger.info(f"🔄 Adjustment needed:")
            logger.info(f"   Portfolio Delta: {self.current_delta:.4f}")
            logger.info(f"   Action: {action['hedge_side']} {abs(hedge_quantity)} futures")

            return action

        # Check if existing hedge can be closed for profit
        if self.futures_position != 0:
            # Calculate hedge P&L
            if self.futures_position > 0:  # Long futures
                hedge_pnl = (current_spot - self.futures_entry_price) * abs(self.futures_position)
            else:  # Short futures
                hedge_pnl = (self.futures_entry_price - current_spot) * abs(self.futures_position)

            # Check profit target
            hedge_cost = self.futures_entry_price * abs(self.futures_position)
            hedge_pnl_pct = (hedge_pnl / hedge_cost) * 100 if hedge_cost > 0 else 0

            if hedge_pnl_pct >= self.profit_target_pct:
                action = {
                    'timestamp': datetime.now(),
                    'action': 'CLOSE_HEDGE',
                    'spot': current_spot,
                    'hedge_side': 'BUY' if self.futures_position < 0 else 'SELL',  # Opposite
                    'hedge_quantity': abs(self.futures_position),
                    'hedge_pnl': hedge_pnl,
                    'hedge_pnl_pct': hedge_pnl_pct,
                    'reason': f"Profit target {self.profit_target_pct}% reached"
                }

                logger.info(f"💰 Closing hedge for profit:")
                logger.info(f"   P&L: ₹{hedge_pnl:,.2f} ({hedge_pnl_pct:.2f}%)")

                return action

        return None

    def execute_adjustment(self, action: Dict, execution_price: float) -> None:
        """
        Execute the adjustment

        Parameters:
        -----------
        action : dict
            Action dictionary from check_adjustment()
        execution_price : float
            Execution price for futures
        """
        if action['action'] == 'HEDGE':
            # Open hedge position
            if action['hedge_side'] == 'BUY':
                self.futures_position = action['hedge_quantity']
            else:
                self.futures_position = -action['hedge_quantity']

            self.futures_entry_price = execution_price
            self.adjustments_count += 1

            self.adjustment_history.append({
                **action,
                'execution_price': execution_price,
                'futures_position': self.futures_position
            })

            logger.info(f"✅ Hedge executed @ ₹{execution_price:,.2f}")

        elif action['action'] == 'CLOSE_HEDGE':
            # Close hedge and realize P&L
            self.realized_pnl += action['hedge_pnl']

            self.adjustment_history.append({
                **action,
                'execution_price': execution_price,
                'realized_pnl': self.realized_pnl
            })

            # Reset futures position
            self.futures_position = 0
            self.futures_entry_price = 0

            logger.info(f"✅ Hedge closed @ ₹{execution_price:,.2f}")
            logger.info(f"   Total Realized P&L: ₹{self.realized_pnl:,.2f}")

    def exit_position(self, call_exit_price: float, put_exit_price: float) -> Dict:
        """
        Exit entire position (end of day)

        Parameters:
        -----------
        call_exit_price : float
            Exit price for call
        put_exit_price : float
            Exit price for put

        Returns:
        --------
        dict : Exit summary
        """
        # Calculate options P&L
        options_exit_value = (call_exit_price + put_exit_price) * self.lot_size
        options_pnl = options_exit_value - self.entry_cost

        # Close any open futures hedge
        hedge_pnl = 0
        if self.futures_position != 0:
            logger.warning("⚠️  Closing open hedge at exit")
            # Assume closed at current spot
            # hedge_pnl calculated separately

        # Total P&L
        total_pnl = options_pnl + self.realized_pnl + hedge_pnl

        exit_summary = {
            'timestamp': datetime.now(),
            'action': 'EXIT',
            'entry_cost': self.entry_cost,
            'exit_value': options_exit_value,
            'options_pnl': options_pnl,
            'realized_hedge_pnl': self.realized_pnl,
            'total_pnl': total_pnl,
            'total_adjustments': self.adjustments_count,
            'roi_pct': (total_pnl / self.entry_cost) * 100 if self.entry_cost > 0 else 0
        }

        self.position_active = False

        logger.info("=" * 60)
        logger.info("GAMMA SCALPING - EXIT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Entry Cost:       ₹{self.entry_cost:,.2f}")
        logger.info(f"Exit Value:       ₹{options_exit_value:,.2f}")
        logger.info(f"Options P&L:      ₹{options_pnl:,.2f}")
        logger.info(f"Hedge P&L:        ₹{self.realized_pnl:,.2f}")
        logger.info(f"Total P&L:        ₹{total_pnl:,.2f}")
        logger.info(f"ROI:              {exit_summary['roi_pct']:.2f}%")
        logger.info(f"Adjustments:      {self.adjustments_count}")
        logger.info("=" * 60)

        return exit_summary

    def get_summary(self) -> Dict:
        """Get current position summary"""
        return {
            'position_active': self.position_active,
            'entry_cost': self.entry_cost,
            'current_delta': self.current_delta,
            'futures_position': self.futures_position,
            'realized_pnl': self.realized_pnl,
            'adjustments_count': self.adjustments_count,
            'max_adjustments': self.max_adjustments
        }


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("GAMMA SCALPING STRATEGY - EXAMPLE")
    print("=" * 80)
    print()

    # Initialize strategy
    strategy = GammaScalpingStrategy(
        spot_price=19500,
        atm_strike=19500,
        atm_call_price=150,
        atm_put_price=140,
        call_delta=0.50,
        put_delta=-0.50,
        call_gamma=0.01,
        put_gamma=0.01,
        lot_size=50,
        delta_threshold=0.15,  # Hedge when |delta| > 0.15
        profit_target_pct=0.5  # Take profit at 0.5%
    )

    # Enter position
    entry = strategy.enter_position()

    print("\n--- Market moves to 19600 (up 100 points) ---\n")

    # Update Greeks (spot moved up)
    strategy.update_greeks(
        spot=19600,
        call_delta=0.65,  # Increased
        put_delta=-0.35,  # Decreased (less negative)
        call_gamma=0.009,
        put_gamma=0.009
    )

    # Check for adjustment
    action = strategy.check_adjustment(19600)

    if action:
        print(f"Action needed: {action}")
        # Execute hedge
        strategy.execute_adjustment(action, execution_price=19600)

    print("\n--- Market reverts to 19550 ---\n")

    # Update Greeks
    strategy.update_greeks(
        spot=19550,
        call_delta=0.55,
        put_delta=-0.45,
        call_gamma=0.01,
        put_gamma=0.01
    )

    # Check if hedge can be closed
    action = strategy.check_adjustment(19550)

    if action:
        print(f"Action needed: {action}")
        strategy.execute_adjustment(action, execution_price=19550)

    print("\n--- End of Day: Exit Position ---\n")

    # Exit
    exit_summary = strategy.exit_position(
        call_exit_price=160,
        put_exit_price=130
    )

    print("\n" + "=" * 80)
