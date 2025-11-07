"""
0DTE (Zero Days to Expiry) Options Strategy
Ultra-short-term intraday strategy for expiry day

Concept:
- Trade options on expiry day (Thursday for weekly Nifty)
- Maximum theta decay on expiry day
- Quick scalps based on spot movement
- Exit before 3:20 PM to avoid assignment risk

Strategies:
1. Sell OTM options (credit collection)
2. Buy ATM, sell OTM (vertical spreads)
3. Iron Condor on expiry day
4. Scalp ATM straddle based on IV changes

Risk: High (can go to zero or max loss quickly)
Reward: High (can double/triple in minutes)
Time: 9:30 AM - 3:20 PM (expiry day only)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime, time as dt_time
import logging

logger = logging.getLogger(__name__)


class ZeroDTEStrategy:
    """
    0DTE Options Trading Strategy

    Multiple sub-strategies for expiry day:
    1. Credit Spreads (sell OTM, buy further OTM)
    2. Debit Spreads (buy ATM, sell OTM)
    3. ATM Straddle Scalp
    4. Iron Condor on expiry

    Parameters:
    -----------
    spot_price : float
        Current spot price
    strategy_type : str
        'credit_spread', 'debit_spread', 'atm_scalp', 'iron_condor'
    risk_per_trade : float
        Max risk per trade (₹)
    profit_target_pct : float
        Profit target (% of max profit)
    stop_loss_pct : float
        Stop loss (% of entry)
    max_trades : int
        Maximum trades for the day
    """

    STRATEGY_CREDIT_SPREAD = 'credit_spread'
    STRATEGY_DEBIT_SPREAD = 'debit_spread'
    STRATEGY_ATM_SCALP = 'atm_scalp'
    STRATEGY_IRON_CONDOR = 'iron_condor'

    def __init__(self,
                 spot_price: float,
                 strategy_type: str = STRATEGY_CREDIT_SPREAD,
                 risk_per_trade: float = 5000,
                 profit_target_pct: float = 50,
                 stop_loss_pct: float = 100,
                 max_trades: int = 5,
                 lot_size: int = 50):
        """Initialize 0DTE Strategy"""

        self.spot_price = spot_price
        self.strategy_type = strategy_type
        self.risk_per_trade = risk_per_trade
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_trades = max_trades
        self.lot_size = lot_size

        # Trading state
        self.trades_taken = 0
        self.position_active = False
        self.entry_details: Optional[Dict] = None
        self.current_pnl = 0
        self.total_pnl = 0

        # Trade history
        self.trade_history: List[Dict] = []

        # Exit time (3:20 PM to avoid assignment)
        self.exit_time = dt_time(15, 20)

    def check_time_filter(self) -> bool:
        """
        Check if current time is valid for trading

        Returns:
        --------
        bool : True if can trade
        """
        current_time = datetime.now().time()

        # Don't trade after 3:20 PM
        if current_time >= self.exit_time:
            logger.warning("⚠️  Market closing soon. No new trades.")
            return False

        # Don't trade in first 15 minutes (let market settle)
        if current_time < dt_time(9, 30):
            return False

        return True

    def should_enter(self, spot: float, iv: float, trend: str) -> bool:
        """
        Check if entry conditions are met

        Parameters:
        -----------
        spot : float
            Current spot price
        iv : float
            Current IV
        trend : str
            'up', 'down', 'sideways'

        Returns:
        --------
        bool : True if should enter
        """
        # Check filters
        if not self.check_time_filter():
            return False

        if self.position_active:
            return False

        if self.trades_taken >= self.max_trades:
            logger.info("ℹ️  Max trades reached for the day")
            return False

        # Strategy-specific conditions
        if self.strategy_type == self.STRATEGY_CREDIT_SPREAD:
            # Sell OTM when expecting range-bound
            return trend == 'sideways' and iv > 0.15

        elif self.strategy_type == self.STRATEGY_DEBIT_SPREAD:
            # Buy ATM when expecting strong move
            return trend in ['up', 'down'] and iv < 0.20

        elif self.strategy_type == self.STRATEGY_ATM_SCALP:
            # Scalp ATM when IV is high
            return iv > 0.18

        elif self.strategy_type == self.STRATEGY_IRON_CONDOR:
            # Iron Condor when expecting range
            return trend == 'sideways' and iv > 0.16

        return False

    def enter_credit_spread(self, spot: float, direction: str = 'put') -> Dict:
        """
        Enter credit spread (sell OTM, buy further OTM)

        Parameters:
        -----------
        spot : float
            Current spot
        direction : str
            'call' for bearish, 'put' for bullish

        Returns:
        --------
        dict : Entry details
        """
        strike_interval = 50  # Nifty strike interval

        if direction == 'put':
            # Bull put spread (bullish)
            # Sell OTM put, buy further OTM put
            sell_strike = spot - 100  # 100 points OTM
            buy_strike = spot - 200   # 200 points OTM

            # Assume premiums (in reality, fetch from market)
            sell_premium = 40
            buy_premium = 15

            net_credit = (sell_premium - buy_premium) * self.lot_size
            max_loss = (sell_strike - buy_strike - (sell_premium - buy_premium)) * self.lot_size

        else:
            # Bear call spread (bearish)
            # Sell OTM call, buy further OTM call
            sell_strike = spot + 100
            buy_strike = spot + 200

            sell_premium = 38
            buy_premium = 12

            net_credit = (sell_premium - buy_premium) * self.lot_size
            max_loss = (buy_strike - sell_strike - (sell_premium - buy_premium)) * self.lot_size

        self.entry_details = {
            'timestamp': datetime.now(),
            'strategy': 'credit_spread',
            'direction': direction,
            'spot': spot,
            'sell_strike': sell_strike,
            'buy_strike': buy_strike,
            'sell_premium': sell_premium,
            'buy_premium': buy_premium,
            'net_credit': net_credit,
            'max_loss': max_loss,
            'profit_target': net_credit * (self.profit_target_pct / 100),
            'stop_loss': max_loss * (self.stop_loss_pct / 100)
        }

        self.position_active = True
        self.trades_taken += 1

        logger.info("✅ Credit Spread Entered")
        logger.info(f"   Direction: {direction.upper()}")
        logger.info(f"   Sell: {sell_strike} @ ₹{sell_premium}")
        logger.info(f"   Buy: {buy_strike} @ ₹{buy_premium}")
        logger.info(f"   Net Credit: ₹{net_credit:,.2f}")
        logger.info(f"   Max Loss: ₹{max_loss:,.2f}")

        return self.entry_details

    def enter_atm_scalp(self, spot: float, call_price: float, put_price: float) -> Dict:
        """
        Enter ATM straddle for scalping

        Parameters:
        -----------
        spot : float
            Current spot
        call_price : float
            ATM call price
        put_price : float
            ATM put price

        Returns:
        --------
        dict : Entry details
        """
        atm_strike = round(spot / 50) * 50  # Round to nearest strike

        total_cost = (call_price + put_price) * self.lot_size

        self.entry_details = {
            'timestamp': datetime.now(),
            'strategy': 'atm_scalp',
            'spot': spot,
            'strike': atm_strike,
            'call_price': call_price,
            'put_price': put_price,
            'total_cost': total_cost,
            'profit_target': total_cost * (self.profit_target_pct / 100),
            'stop_loss': total_cost * (self.stop_loss_pct / 100)
        }

        self.position_active = True
        self.trades_taken += 1

        logger.info("✅ ATM Straddle Scalp Entered")
        logger.info(f"   Strike: {atm_strike}")
        logger.info(f"   Call: ₹{call_price}, Put: ₹{put_price}")
        logger.info(f"   Total Cost: ₹{total_cost:,.2f}")

        return self.entry_details

    def check_exit(self, current_prices: Dict) -> Optional[str]:
        """
        Check if exit conditions are met

        Parameters:
        -----------
        current_prices : dict
            Current market prices

        Returns:
        --------
        str or None : Exit reason if should exit
        """
        if not self.position_active or not self.entry_details:
            return None

        # Time-based exit (3:20 PM)
        if datetime.now().time() >= self.exit_time:
            return "time_exit"

        # Calculate current P&L
        if self.entry_details['strategy'] == 'credit_spread':
            # For credit spread, profit when premium decreases
            sell_current = current_prices.get('sell_premium', self.entry_details['sell_premium'])
            buy_current = current_prices.get('buy_premium', self.entry_details['buy_premium'])

            current_value = (sell_current - buy_current) * self.lot_size
            self.current_pnl = self.entry_details['net_credit'] - current_value

        elif self.entry_details['strategy'] == 'atm_scalp':
            # For straddle, profit when value increases
            call_current = current_prices.get('call_price', self.entry_details['call_price'])
            put_current = current_prices.get('put_price', self.entry_details['put_price'])

            current_value = (call_current + put_current) * self.lot_size
            self.current_pnl = current_value - self.entry_details['total_cost']

        # Profit target
        if self.current_pnl >= self.entry_details['profit_target']:
            return "profit_target"

        # Stop loss
        if self.current_pnl <= -self.entry_details['stop_loss']:
            return "stop_loss"

        return None

    def exit_position(self, exit_reason: str, exit_prices: Dict) -> Dict:
        """
        Exit the position

        Parameters:
        -----------
        exit_reason : str
            Reason for exit
        exit_prices : dict
            Exit prices

        Returns:
        --------
        dict : Exit summary
        """
        if not self.position_active:
            return {}

        exit_summary = {
            'timestamp': datetime.now(),
            'entry': self.entry_details,
            'exit_reason': exit_reason,
            'exit_prices': exit_prices,
            'pnl': self.current_pnl,
            'pnl_pct': (self.current_pnl / self.entry_details.get('net_credit', self.entry_details.get('total_cost', 1))) * 100
        }

        self.total_pnl += self.current_pnl
        self.trade_history.append(exit_summary)
        self.position_active = False
        self.entry_details = None

        logger.info("=" * 60)
        logger.info("POSITION EXITED")
        logger.info("=" * 60)
        logger.info(f"Reason: {exit_reason}")
        logger.info(f"P&L: ₹{self.current_pnl:,.2f} ({exit_summary['pnl_pct']:.2f}%)")
        logger.info(f"Total P&L: ₹{self.total_pnl:,.2f}")
        logger.info("=" * 60)

        return exit_summary

    def get_day_summary(self) -> Dict:
        """Get end-of-day summary"""
        winning_trades = sum(1 for trade in self.trade_history if trade['pnl'] > 0)
        losing_trades = len(self.trade_history) - winning_trades

        win_rate = (winning_trades / len(self.trade_history) * 100) if self.trade_history else 0

        return {
            'total_trades': len(self.trade_history),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'max_trades_allowed': self.max_trades,
            'trade_history': self.trade_history
        }


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("0DTE (ZERO DAYS TO EXPIRY) STRATEGY - EXAMPLE")
    print("=" * 80)
    print()
    print("⚠️  HIGH RISK - Trade only with proper risk management")
    print()

    # Initialize strategy
    strategy = ZeroDTEStrategy(
        spot_price=19500,
        strategy_type='credit_spread',
        risk_per_trade=5000,
        profit_target_pct=50,  # Take profit at 50% of max
        stop_loss_pct=100,     # Stop at 100% loss
        max_trades=5
    )

    print("--- Scenario: Bullish Credit Spread (Bull Put Spread) ---\n")

    # Check if should enter
    should_enter = strategy.should_enter(
        spot=19500,
        iv=0.18,
        trend='sideways'
    )

    if should_enter:
        # Enter position
        entry = strategy.enter_credit_spread(spot=19500, direction='put')

        print("\n--- Market stays range-bound ---\n")

        # Check exit
        exit_reason = strategy.check_exit({
            'sell_premium': 20,  # Decreased from 40
            'buy_premium': 8     # Decreased from 15
        })

        if exit_reason:
            exit_summary = strategy.exit_position(
                exit_reason=exit_reason,
                exit_prices={'sell_premium': 20, 'buy_premium': 8}
            )

    print("\n--- End of Day Summary ---\n")
    summary = strategy.get_day_summary()

    print(f"Total Trades: {summary['total_trades']}")
    print(f"Win Rate: {summary['win_rate']:.2f}%")
    print(f"Total P&L: ₹{summary['total_pnl']:,.2f}")

    print("\n" + "=" * 80)
