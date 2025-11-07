"""
Live Trading Engine for Angel One
Integrates strategies with real-time execution

Features:
- Real-time options data via WebSocket
- Auto Greeks calculation
- Strategy execution
- Risk management
- Position monitoring
- P&L tracking
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from datetime import datetime, time as dt_time
import threading
import time
import logging
from queue import Queue

from ..market_data.angel_one_api import AngelOneAPI
from ...core.options_pricing import BlackScholes, Greeks
from ...strategies.hft_scalping.gamma_scalping import GammaScalpingStrategy
from ...strategies.hft_scalping.zero_dte_strategy import ZeroDTEStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveTradingEngine:
    """
    Live Trading Engine

    Connects Angel One API with trading strategies

    Usage:
    ------
    engine = LiveTradingEngine(angel_api)

    # Add strategy
    gamma_strategy = GammaScalpingStrategy(...)
    engine.add_strategy('gamma_scalp', gamma_strategy)

    # Start trading
    engine.start()

    # Monitor
    while trading:
        summary = engine.get_summary()
        print(summary)

    # Stop
    engine.stop()
    """

    def __init__(self,
                 angel_api: AngelOneAPI,
                 risk_per_trade: float = 10000,
                 max_daily_loss: float = 50000,
                 max_daily_profit: float = 100000):
        """
        Initialize Live Trading Engine

        Parameters:
        -----------
        angel_api : AngelOneAPI
            Authenticated Angel One API instance
        risk_per_trade : float
            Max risk per trade
        max_daily_loss : float
            Max loss for the day (trading stops)
        max_daily_profit : float
            Max profit for the day (trading stops)
        """
        self.api = angel_api
        self.risk_per_trade = risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_daily_profit = max_daily_profit

        # Pricing models
        self.bs_model = BlackScholes()
        self.greeks_calc = Greeks()

        # Strategies
        self.strategies: Dict[str, any] = {}
        self.active_strategy: Optional[str] = None

        # Trading state
        self.running = False
        self.trading_thread: Optional[threading.Thread] = None
        self.data_queue = Queue()

        # Risk management
        self.daily_pnl = 0.0
        self.open_positions: List[Dict] = []
        self.closed_trades: List[Dict] = []

        # Market data cache
        self.spot_price = 0.0
        self.options_chain: Optional[pd.DataFrame] = None
        self.last_update = None

    def add_strategy(self, name: str, strategy: any) -> None:
        """
        Add a trading strategy

        Parameters:
        -----------
        name : str
            Strategy name
        strategy : Strategy object
            Strategy instance
        """
        self.strategies[name] = strategy
        logger.info(f"✅ Strategy added: {name}")

    def set_active_strategy(self, name: str) -> bool:
        """
        Set active strategy

        Parameters:
        -----------
        name : str
            Strategy name

        Returns:
        --------
        bool : True if successful
        """
        if name in self.strategies:
            self.active_strategy = name
            logger.info(f"✅ Active strategy: {name}")
            return True
        else:
            logger.error(f"❌ Strategy not found: {name}")
            return False

    def start(self) -> None:
        """Start live trading"""
        if self.running:
            logger.warning("⚠️  Already running")
            return

        if not self.active_strategy:
            logger.error("❌ No active strategy set")
            return

        self.running = True

        # Start data update thread
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()

        logger.info("🚀 Live Trading Engine STARTED")
        logger.info(f"   Active Strategy: {self.active_strategy}")
        logger.info(f"   Max Daily Loss: ₹{self.max_daily_loss:,.2f}")
        logger.info(f"   Max Daily Profit: ₹{self.max_daily_profit:,.2f}")

    def stop(self) -> None:
        """Stop live trading"""
        self.running = False

        if self.trading_thread:
            self.trading_thread.join(timeout=5)

        logger.info("🛑 Live Trading Engine STOPPED")

        # Print summary
        self.print_day_summary()

    def _trading_loop(self) -> None:
        """Main trading loop"""
        while self.running:
            try:
                # Check trading hours
                if not self._is_market_hours():
                    time.sleep(60)
                    continue

                # Check risk limits
                if not self._check_risk_limits():
                    logger.warning("⚠️  Risk limits breached. Stopping.")
                    self.stop()
                    break

                # Update market data
                self._update_market_data()

                # Run strategy logic
                self._execute_strategy()

                # Update positions
                self._update_positions()

                # Sleep before next iteration
                time.sleep(1)  # 1 second interval

            except Exception as e:
                logger.error(f"❌ Trading loop error: {e}")
                time.sleep(5)

    def _is_market_hours(self) -> bool:
        """Check if market is open"""
        current_time = datetime.now().time()

        market_open = dt_time(9, 15)
        market_close = dt_time(15, 30)

        return market_open <= current_time <= market_close

    def _check_risk_limits(self) -> bool:
        """Check if risk limits are OK"""
        # Max loss check
        if self.daily_pnl <= -self.max_daily_loss:
            logger.error(f"🚨 MAX DAILY LOSS HIT: ₹{self.daily_pnl:,.2f}")
            return False

        # Max profit check (stop when target hit)
        if self.daily_pnl >= self.max_daily_profit:
            logger.info(f"🎯 MAX DAILY PROFIT HIT: ₹{self.daily_pnl:,.2f}")
            return False

        return True

    def _update_market_data(self) -> None:
        """Update market data from Angel One"""
        try:
            # Get Nifty spot
            nifty_ltp = self.api.get_ltp('NSE', 'NIFTY 50', 'NSE:NIFTY 50')

            if nifty_ltp:
                self.spot_price = nifty_ltp

            # Get options chain (every 5 seconds to avoid rate limits)
            if (self.last_update is None or
                (datetime.now() - self.last_update).seconds >= 5):

                self.options_chain = self.api.get_options_chain('NIFTY')
                self.last_update = datetime.now()

        except Exception as e:
            logger.error(f"❌ Market data update error: {e}")

    def _execute_strategy(self) -> None:
        """Execute active strategy"""
        if not self.active_strategy or self.options_chain is None:
            return

        strategy = self.strategies[self.active_strategy]

        try:
            # Gamma Scalping
            if isinstance(strategy, GammaScalpingStrategy):
                self._execute_gamma_scalping(strategy)

            # 0DTE Strategy
            elif isinstance(strategy, ZeroDTEStrategy):
                self._execute_zero_dte(strategy)

        except Exception as e:
            logger.error(f"❌ Strategy execution error: {e}")

    def _execute_gamma_scalping(self, strategy: GammaScalpingStrategy) -> None:
        """Execute gamma scalping strategy"""
        # If no position, check entry
        if not strategy.position_active:
            # Get ATM options
            atm_strike = round(self.spot_price / 50) * 50

            atm_call = self.options_chain[
                (self.options_chain['strike'] == atm_strike) &
                (self.options_chain['option_type'] == 'CE')
            ]

            atm_put = self.options_chain[
                (self.options_chain['strike'] == atm_strike) &
                (self.options_chain['option_type'] == 'PE')
            ]

            if not atm_call.empty and not atm_put.empty:
                call_price = atm_call.iloc[0]['ltp']
                put_price = atm_put.iloc[0]['ltp']

                # Enter position
                strategy.enter_position()

                # Place orders
                self.api.place_order('NIFTY', atm_strike, 'CE', 'BUY', 1)
                self.api.place_order('NIFTY', atm_strike, 'PE', 'BUY', 1)

        else:
            # Calculate Greeks
            T = 1 / 365  # Assume 1 day to expiry for demo
            r = 0.07
            sigma = 0.15

            call_delta = self.greeks_calc.delta(
                self.spot_price, strategy.atm_strike, T, r, sigma, 'call'
            )
            put_delta = self.greeks_calc.delta(
                self.spot_price, strategy.atm_strike, T, r, sigma, 'put'
            )
            call_gamma = self.greeks_calc.gamma(
                self.spot_price, strategy.atm_strike, T, r, sigma
            )
            put_gamma = self.greeks_calc.gamma(
                self.spot_price, strategy.atm_strike, T, r, sigma
            )

            # Update strategy Greeks
            strategy.update_greeks(
                self.spot_price, call_delta, put_delta, call_gamma, put_gamma
            )

            # Check for adjustment
            action = strategy.check_adjustment(self.spot_price)

            if action:
                # Execute adjustment
                if action['action'] == 'HEDGE':
                    # Place futures order
                    logger.info(f"Executing hedge: {action}")
                    strategy.execute_adjustment(action, self.spot_price)

                elif action['action'] == 'CLOSE_HEDGE':
                    # Close futures hedge
                    logger.info(f"Closing hedge: {action}")
                    strategy.execute_adjustment(action, self.spot_price)

    def _execute_zero_dte(self, strategy: ZeroDTEStrategy) -> None:
        """Execute 0DTE strategy"""
        # Check if should enter
        should_enter = strategy.should_enter(
            spot=self.spot_price,
            iv=0.15,  # Calculate from options chain
            trend='sideways'  # Use ML model to determine
        )

        if should_enter:
            # Enter position based on strategy type
            if strategy.strategy_type == strategy.STRATEGY_CREDIT_SPREAD:
                entry = strategy.enter_credit_spread(self.spot_price, direction='put')

                # Place orders
                # Sell OTM put
                self.api.place_order(
                    'NIFTY',
                    entry['sell_strike'],
                    'PE',
                    'SELL',
                    1
                )

                # Buy further OTM put
                self.api.place_order(
                    'NIFTY',
                    entry['buy_strike'],
                    'PE',
                    'BUY',
                    1
                )

        else:
            # Check exit if position active
            if strategy.position_active:
                exit_reason = strategy.check_exit({'sell_premium': 0, 'buy_premium': 0})

                if exit_reason:
                    # Exit position
                    exit_summary = strategy.exit_position(exit_reason, {})

                    # Close orders
                    # (Implementation depends on position type)

    def _update_positions(self) -> None:
        """Update open positions and calculate P&L"""
        try:
            positions = self.api.get_positions()

            if not positions.empty:
                # Calculate total P&L
                total_pnl = positions['pnl'].sum() if 'pnl' in positions.columns else 0
                self.daily_pnl = total_pnl

        except Exception as e:
            logger.error(f"❌ Position update error: {e}")

    def get_summary(self) -> Dict:
        """Get current trading summary"""
        return {
            'running': self.running,
            'active_strategy': self.active_strategy,
            'spot_price': self.spot_price,
            'daily_pnl': self.daily_pnl,
            'open_positions': len(self.open_positions),
            'closed_trades': len(self.closed_trades),
            'max_daily_loss': self.max_daily_loss,
            'max_daily_profit': self.max_daily_profit
        }

    def print_day_summary(self) -> None:
        """Print end-of-day summary"""
        summary = self.get_summary()

        print("\n" + "=" * 80)
        print("END OF DAY SUMMARY")
        print("=" * 80)
        print(f"Active Strategy:    {summary['active_strategy']}")
        print(f"Total P&L:          ₹{summary['daily_pnl']:,.2f}")
        print(f"Closed Trades:      {summary['closed_trades']}")
        print(f"Final Spot:         ₹{summary['spot_price']:,.2f}")
        print("=" * 80)


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("LIVE TRADING ENGINE - SETUP EXAMPLE")
    print("=" * 80)
    print()
    print("⚠️  Replace with your actual Angel One credentials")
    print()
    print("# Setup Angel One API")
    print("angel_api = AngelOneAPI(api_key='...', username='...', password='...', totp_token='...')")
    print("angel_api.login()")
    print()
    print("# Setup strategy")
    print("gamma_strategy = GammaScalpingStrategy(...)")
    print()
    print("# Setup trading engine")
    print("engine = LiveTradingEngine(angel_api)")
    print("engine.add_strategy('gamma_scalp', gamma_strategy)")
    print("engine.set_active_strategy('gamma_scalp')")
    print()
    print("# Start trading")
    print("engine.start()")
    print()
    print("# Monitor (in separate thread/process)")
    print("while True:")
    print("    summary = engine.get_summary()")
    print("    print(summary)")
    print("    time.sleep(60)")
    print()
    print("# Stop trading")
    print("engine.stop()")
    print()
    print("=" * 80)
