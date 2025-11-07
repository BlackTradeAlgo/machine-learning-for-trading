"""
Risk Management Engine
Real-time risk monitoring and position management

Features:
- Daily loss/profit limits
- Position sizing (Kelly Criterion, Fixed Fractional)
- Portfolio heat monitoring
- Greeks-based exposure limits
- Margin requirement tracking
- Correlation-based risk assessment
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass
class Position:
    """Trading position"""
    symbol: str
    strike: float
    option_type: str  # CE or PE
    quantity: int
    entry_price: float
    current_price: float
    pnl: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0


@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    total_capital: float
    deployed_capital: float
    available_capital: float
    daily_pnl: float
    total_pnl: float
    portfolio_delta: float
    portfolio_gamma: float
    portfolio_vega: float
    portfolio_theta: float
    var_95: float  # Value at Risk (95%)
    max_drawdown: float
    current_drawdown: float
    num_positions: int
    risk_level: RiskLevel


class RiskManager:
    """
    Comprehensive Risk Management System

    Features:
    ---------
    1. Position Sizing (Kelly, Fixed Fractional)
    2. Daily Loss/Profit Limits
    3. Portfolio Greeks Monitoring
    4. VaR (Value at Risk) Calculation
    5. Drawdown Tracking
    6. Exposure Limits

    Example:
    --------
    >>> risk_mgr = RiskManager(
    ...     total_capital=10000000,  # 1 crore
    ...     max_daily_loss_pct=5,
    ...     max_daily_profit_pct=10,
    ...     max_position_size_pct=10
    ... )
    >>>
    >>> # Check if trade is allowed
    >>> can_trade = risk_mgr.can_place_trade(
    ...     capital_required=50000,
    ...     strategy_risk=25000
    ... )
    """

    def __init__(self,
                 total_capital: float = 10000000,  # 1 crore
                 max_daily_loss_pct: float = 5.0,
                 max_daily_profit_pct: float = 10.0,
                 max_position_size_pct: float = 10.0,
                 max_portfolio_delta: float = 100.0,
                 max_portfolio_gamma: float = 10.0,
                 max_portfolio_vega: float = 50.0,
                 max_drawdown_pct: float = 15.0):
        """
        Initialize Risk Manager

        Parameters:
        -----------
        total_capital : float
            Total trading capital (₹)
        max_daily_loss_pct : float
            Max daily loss % (e.g., 5 = 5%)
        max_daily_profit_pct : float
            Max daily profit % to book (e.g., 10 = 10%)
        max_position_size_pct : float
            Max capital per position % (e.g., 10 = 10%)
        max_portfolio_delta : float
            Maximum portfolio delta exposure
        max_portfolio_gamma : float
            Maximum portfolio gamma exposure
        max_portfolio_vega : float
            Maximum portfolio vega exposure
        max_drawdown_pct : float
            Maximum allowed drawdown %
        """
        self.total_capital = total_capital
        self.initial_capital = total_capital
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_daily_profit_pct = max_daily_profit_pct
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_delta = max_portfolio_delta
        self.max_portfolio_gamma = max_portfolio_gamma
        self.max_portfolio_vega = max_portfolio_vega
        self.max_drawdown_pct = max_drawdown_pct

        # Calculate absolute limits
        self.max_daily_loss = total_capital * (max_daily_loss_pct / 100)
        self.max_daily_profit = total_capital * (max_daily_profit_pct / 100)
        self.max_position_size = total_capital * (max_position_size_pct / 100)
        self.max_drawdown = total_capital * (max_drawdown_pct / 100)

        # State tracking
        self.positions: Dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.peak_capital = total_capital
        self.current_drawdown = 0.0
        self.max_drawdown_seen = 0.0
        self.trades_today = 0
        self.current_date = date.today()

        # Risk history
        self.daily_pnl_history: List[float] = []
        self.capital_history: List[float] = [total_capital]

        logger.info(f"RiskManager initialized: Capital=₹{total_capital:,.0f}, "
                   f"MaxDailyLoss={max_daily_loss_pct}%, MaxDailyProfit={max_daily_profit_pct}%")

    # ==================== POSITION SIZING ====================

    def calculate_position_size_kelly(self, win_rate: float, win_loss_ratio: float,
                                     capital_to_risk: float = None) -> float:
        """
        Calculate position size using Kelly Criterion

        Parameters:
        -----------
        win_rate : float
            Probability of winning (0-1)
        win_loss_ratio : float
            Average win / Average loss ratio
        capital_to_risk : float
            Capital to use for calculation (default: total_capital)

        Returns:
        --------
        float : Recommended position size (₹)

        Formula: Kelly% = W - [(1-W) / R]
        Where W = win rate, R = win/loss ratio
        """
        if capital_to_risk is None:
            capital_to_risk = self.total_capital

        # Kelly formula
        kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)

        # Use fractional Kelly (0.25 to 0.5 for safety)
        safe_kelly_pct = kelly_pct * 0.25  # Quarter Kelly

        # Ensure non-negative and cap at max position size
        safe_kelly_pct = max(0, min(safe_kelly_pct, self.max_position_size_pct / 100))

        position_size = capital_to_risk * safe_kelly_pct

        logger.debug(f"Kelly Position Size: ₹{position_size:,.0f} ({safe_kelly_pct*100:.2f}%)")

        return position_size

    def calculate_position_size_fixed_fractional(self, risk_pct: float = 2.0) -> float:
        """
        Calculate position size using Fixed Fractional method

        Parameters:
        -----------
        risk_pct : float
            Risk per trade % (default: 2%)

        Returns:
        --------
        float : Position size (₹)
        """
        position_size = self.total_capital * (risk_pct / 100)

        # Cap at max position size
        position_size = min(position_size, self.max_position_size)

        return position_size

    # ==================== TRADE VALIDATION ====================

    def can_place_trade(self, capital_required: float, strategy_risk: float,
                       position_delta: float = 0, position_gamma: float = 0,
                       position_vega: float = 0) -> Tuple[bool, str]:
        """
        Check if trade can be placed based on risk limits

        Parameters:
        -----------
        capital_required : float
            Capital needed for trade
        strategy_risk : float
            Maximum loss potential
        position_delta : float
            Delta of new position
        position_gamma : float
            Gamma of new position
        position_vega : float
            Vega of new position

        Returns:
        --------
        Tuple[bool, str] : (can_trade, reason)
        """
        # Reset daily counters if new day
        self._check_new_day()

        # Check 1: Daily loss limit
        if abs(self.daily_pnl) >= self.max_daily_loss:
            return False, f"Daily loss limit hit: ₹{abs(self.daily_pnl):,.0f} / ₹{self.max_daily_loss:,.0f}"

        # Check 2: Daily profit limit (book profits)
        if self.daily_pnl >= self.max_daily_profit:
            return False, f"Daily profit target hit: ₹{self.daily_pnl:,.0f}. Book profits!"

        # Check 3: Max drawdown
        if self.current_drawdown >= self.max_drawdown:
            return False, f"Max drawdown hit: ₹{self.current_drawdown:,.0f} / ₹{self.max_drawdown:,.0f}"

        # Check 4: Position size limit
        if capital_required > self.max_position_size:
            return False, f"Position size too large: ₹{capital_required:,.0f} > ₹{self.max_position_size:,.0f}"

        # Check 5: Available capital
        deployed = sum(pos.entry_price * abs(pos.quantity) for pos in self.positions.values())
        available = self.total_capital - deployed

        if capital_required > available:
            return False, f"Insufficient capital: Need ₹{capital_required:,.0f}, Available ₹{available:,.0f}"

        # Check 6: Portfolio Greeks limits
        current_greeks = self.get_portfolio_greeks()

        new_delta = current_greeks['delta'] + position_delta
        if abs(new_delta) > self.max_portfolio_delta:
            return False, f"Portfolio delta limit: {abs(new_delta):.2f} > {self.max_portfolio_delta:.2f}"

        new_gamma = current_greeks['gamma'] + position_gamma
        if abs(new_gamma) > self.max_portfolio_gamma:
            return False, f"Portfolio gamma limit: {abs(new_gamma):.2f} > {self.max_portfolio_gamma:.2f}"

        new_vega = current_greeks['vega'] + position_vega
        if abs(new_vega) > self.max_portfolio_vega:
            return False, f"Portfolio vega limit: {abs(new_vega):.2f} > {self.max_portfolio_vega:.2f}"

        # All checks passed
        return True, "Trade allowed"

    # ==================== POSITION MANAGEMENT ====================

    def add_position(self, position: Position) -> None:
        """Add new position to portfolio"""
        position_key = f"{position.symbol}_{position.strike}_{position.option_type}"
        self.positions[position_key] = position
        self.trades_today += 1

        logger.info(f"Position added: {position_key}, Qty={position.quantity}")

    def update_position_price(self, symbol: str, strike: float, option_type: str,
                             current_price: float) -> None:
        """Update position with current price"""
        position_key = f"{symbol}_{strike}_{option_type}"

        if position_key in self.positions:
            pos = self.positions[position_key]
            pos.current_price = current_price
            pos.pnl = (current_price - pos.entry_price) * pos.quantity

    def close_position(self, symbol: str, strike: float, option_type: str,
                      exit_price: float) -> float:
        """Close position and return P&L"""
        position_key = f"{symbol}_{strike}_{option_type}"

        if position_key in self.positions:
            pos = self.positions[position_key]
            pnl = (exit_price - pos.entry_price) * pos.quantity

            # Update P&L
            self.daily_pnl += pnl
            self.total_pnl += pnl
            self.total_capital += pnl

            # Update drawdown
            self._update_drawdown()

            # Remove position
            del self.positions[position_key]

            logger.info(f"Position closed: {position_key}, P&L=₹{pnl:,.2f}")

            return pnl

        return 0.0

    def get_portfolio_greeks(self) -> Dict[str, float]:
        """Calculate total portfolio Greeks"""
        total_delta = sum(pos.delta * pos.quantity for pos in self.positions.values())
        total_gamma = sum(pos.gamma * pos.quantity for pos in self.positions.values())
        total_vega = sum(pos.vega * pos.quantity for pos in self.positions.values())
        total_theta = sum(pos.theta * pos.quantity for pos in self.positions.values())

        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'vega': total_vega,
            'theta': total_theta
        }

    # ==================== RISK METRICS ====================

    def calculate_var(self, confidence: float = 0.95, days: int = 1) -> float:
        """
        Calculate Value at Risk (VaR)

        Parameters:
        -----------
        confidence : float
            Confidence level (e.g., 0.95 for 95%)
        days : int
            Number of days

        Returns:
        --------
        float : VaR amount (₹)
        """
        if len(self.daily_pnl_history) < 30:
            # Not enough history, use simple estimate
            deployed_capital = sum(pos.entry_price * abs(pos.quantity)
                                  for pos in self.positions.values())
            var = deployed_capital * 0.02 * np.sqrt(days)  # 2% daily volatility
        else:
            # Use historical method
            returns = np.array(self.daily_pnl_history) / self.total_capital
            std_dev = np.std(returns)
            z_score = 1.65 if confidence == 0.95 else 2.33  # 95% or 99%
            var = self.total_capital * z_score * std_dev * np.sqrt(days)

        return var

    def get_risk_metrics(self) -> RiskMetrics:
        """Get comprehensive risk metrics"""
        deployed = sum(pos.entry_price * abs(pos.quantity) for pos in self.positions.values())
        available = self.total_capital - deployed

        greeks = self.get_portfolio_greeks()
        var_95 = self.calculate_var(confidence=0.95)

        # Determine risk level
        risk_score = 0
        if abs(self.daily_pnl) / self.max_daily_loss > 0.7:
            risk_score += 3
        elif abs(self.daily_pnl) / self.max_daily_loss > 0.5:
            risk_score += 2
        elif abs(self.daily_pnl) / self.max_daily_loss > 0.3:
            risk_score += 1

        if abs(greeks['delta']) / self.max_portfolio_delta > 0.8:
            risk_score += 2

        if self.current_drawdown / self.max_drawdown > 0.8:
            risk_score += 3

        if risk_score >= 6:
            risk_level = RiskLevel.EXTREME
        elif risk_score >= 4:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 2:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.LOW

        return RiskMetrics(
            total_capital=self.total_capital,
            deployed_capital=deployed,
            available_capital=available,
            daily_pnl=self.daily_pnl,
            total_pnl=self.total_pnl,
            portfolio_delta=greeks['delta'],
            portfolio_gamma=greeks['gamma'],
            portfolio_vega=greeks['vega'],
            portfolio_theta=greeks['theta'],
            var_95=var_95,
            max_drawdown=self.max_drawdown_seen,
            current_drawdown=self.current_drawdown,
            num_positions=len(self.positions),
            risk_level=risk_level
        )

    def print_risk_report(self) -> None:
        """Print comprehensive risk report"""
        metrics = self.get_risk_metrics()

        print("=" * 80)
        print("RISK MANAGEMENT REPORT")
        print("=" * 80)
        print(f"Date: {date.today().strftime('%d-%b-%Y')}")
        print()

        print("CAPITAL:")
        print("-" * 80)
        print(f"{'Total Capital':<30}: ₹{metrics.total_capital:>15,.2f}")
        print(f"{'Deployed Capital':<30}: ₹{metrics.deployed_capital:>15,.2f}")
        print(f"{'Available Capital':<30}: ₹{metrics.available_capital:>15,.2f}")
        print()

        print("P&L:")
        print("-" * 80)
        print(f"{'Daily P&L':<30}: ₹{metrics.daily_pnl:>15,.2f}")
        print(f"{'Total P&L':<30}: ₹{metrics.total_pnl:>15,.2f}")
        print(f"{'Return on Capital':<30}: {(metrics.total_pnl/self.initial_capital)*100:>16.2f}%")
        print()

        print("LIMITS:")
        print("-" * 80)
        daily_loss_used = (abs(self.daily_pnl) / self.max_daily_loss) * 100
        print(f"{'Daily Loss Used':<30}: {daily_loss_used:>17.2f}%")
        print(f"{'Max Daily Loss':<30}: ₹{self.max_daily_loss:>15,.2f}")
        print(f"{'Drawdown':<30}: ₹{metrics.current_drawdown:>15,.2f}")
        print(f"{'Max Drawdown Allowed':<30}: ₹{self.max_drawdown:>15,.2f}")
        print()

        print("PORTFOLIO GREEKS:")
        print("-" * 80)
        print(f"{'Delta':<30}: {metrics.portfolio_delta:>18.2f} (Max: {self.max_portfolio_delta:.0f})")
        print(f"{'Gamma':<30}: {metrics.portfolio_gamma:>18.2f} (Max: {self.max_portfolio_gamma:.0f})")
        print(f"{'Vega':<30}: {metrics.portfolio_vega:>18.2f} (Max: {self.max_portfolio_vega:.0f})")
        print(f"{'Theta':<30}: {metrics.portfolio_theta:>18.2f}")
        print()

        print("RISK METRICS:")
        print("-" * 80)
        print(f"{'Value at Risk (95%)':<30}: ₹{metrics.var_95:>15,.2f}")
        print(f"{'Number of Positions':<30}: {metrics.num_positions:>18}")
        print(f"{'Trades Today':<30}: {self.trades_today:>18}")
        print(f"{'Risk Level':<30}: {metrics.risk_level.value:>18}")
        print("=" * 80)

    # ==================== PRIVATE METHODS ====================

    def _check_new_day(self) -> None:
        """Check if it's a new trading day and reset counters"""
        today = date.today()
        if today != self.current_date:
            # New day - reset daily counters
            self.daily_pnl_history.append(self.daily_pnl)
            self.capital_history.append(self.total_capital)

            self.daily_pnl = 0.0
            self.trades_today = 0
            self.current_date = today

            logger.info(f"New trading day: {today}")

    def _update_drawdown(self) -> None:
        """Update drawdown metrics"""
        # Update peak
        if self.total_capital > self.peak_capital:
            self.peak_capital = self.total_capital

        # Calculate current drawdown
        self.current_drawdown = self.peak_capital - self.total_capital

        # Update max drawdown seen
        if self.current_drawdown > self.max_drawdown_seen:
            self.max_drawdown_seen = self.current_drawdown

    def __repr__(self) -> str:
        metrics = self.get_risk_metrics()
        return (f"<RiskManager: Capital=₹{metrics.total_capital:,.0f}, "
                f"P&L=₹{metrics.daily_pnl:,.0f}, "
                f"Risk={metrics.risk_level.value}>")


if __name__ == "__main__":
    # Example usage
    print("=" * 80)
    print("RISK MANAGER - EXAMPLE")
    print("=" * 80)
    print()

    # Initialize risk manager with 1 crore capital
    risk_mgr = RiskManager(
        total_capital=10000000,  # 1 crore
        max_daily_loss_pct=5,
        max_daily_profit_pct=10,
        max_position_size_pct=10
    )

    # Example 1: Calculate position size using Kelly
    print("1. Position Sizing (Kelly Criterion):")
    kelly_size = risk_mgr.calculate_position_size_kelly(
        win_rate=0.55,  # 55% win rate
        win_loss_ratio=1.5  # Win/Loss = 1.5
    )
    print(f"   Recommended Size: ₹{kelly_size:,.0f}")
    print()

    # Example 2: Check if trade is allowed
    print("2. Trade Validation:")
    can_trade, reason = risk_mgr.can_place_trade(
        capital_required=500000,  # 5 lakh
        strategy_risk=250000,  # 2.5 lakh max loss
        position_delta=15.0
    )
    print(f"   Can Trade: {can_trade}")
    print(f"   Reason: {reason}")
    print()

    # Example 3: Add position
    print("3. Adding Position:")
    pos = Position(
        symbol='NIFTY',
        strike=19500,
        option_type='CE',
        quantity=75,
        entry_price=150,
        current_price=160,
        delta=0.5,
        gamma=0.01,
        vega=0.3,
        theta=-5.0
    )
    risk_mgr.add_position(pos)
    print(f"   Position added: NIFTY 19500 CE")
    print()

    # Example 4: Update position
    print("4. Updating Position Price:")
    risk_mgr.update_position_price('NIFTY', 19500, 'CE', 165)
    print(f"   Price updated: 150 → 165")
    print()

    # Example 5: Print risk report
    print("5. Risk Report:")
    print()
    risk_mgr.print_risk_report()
