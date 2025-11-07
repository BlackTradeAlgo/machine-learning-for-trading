"""
Base Strategy Class
All options strategies inherit from this class
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import matplotlib.pyplot as plt
from datetime import datetime


class OptionType(Enum):
    """Option type enumeration"""
    CALL = "CE"
    PUT = "PE"


class PositionType(Enum):
    """Position type enumeration"""
    LONG = 1
    SHORT = -1


@dataclass
class Position:
    """
    Represents a single option position

    Attributes:
    -----------
    strike : float
        Strike price
    option_type : OptionType
        CALL or PUT
    position_type : PositionType
        LONG or SHORT
    premium : float
        Option premium (price)
    quantity : int
        Number of contracts
    lot_size : int
        Lot size for the option
    """
    strike: float
    option_type: OptionType
    position_type: PositionType
    premium: float
    quantity: int = 1
    lot_size: int = 50  # Default: Nifty lot size

    @property
    def total_lots(self) -> int:
        """Total number of lots"""
        return self.quantity * self.lot_size

    @property
    def total_premium(self) -> float:
        """Total premium (paid/received)"""
        return self.premium * self.quantity * self.lot_size

    def payoff_at_expiry(self, spot: float) -> float:
        """Calculate payoff at expiry for given spot price"""
        intrinsic = 0

        if self.option_type == OptionType.CALL:
            intrinsic = max(0, spot - self.strike)
        else:  # PUT
            intrinsic = max(0, self.strike - spot)

        # Adjust for position type (long/short)
        payoff = intrinsic * self.position_type.value

        # Adjust for premium
        premium_effect = -self.premium if self.position_type == PositionType.LONG else self.premium

        return (payoff + premium_effect) * self.quantity * self.lot_size

    def __repr__(self) -> str:
        pos_str = "LONG" if self.position_type == PositionType.LONG else "SHORT"
        opt_str = "CE" if self.option_type == OptionType.CALL else "PE"
        return f"{pos_str} {self.quantity}x {self.strike}{opt_str} @₹{self.premium}"


class BaseStrategy:
    """
    Base class for all options strategies

    Provides common functionality:
    - Payoff calculation
    - Greeks aggregation
    - Risk metrics
    - Visualization
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.positions: List[Position] = []
        self.spot_price: Optional[float] = None

    def add_position(self, position: Position) -> None:
        """Add a position to the strategy"""
        self.positions.append(position)

    def clear_positions(self) -> None:
        """Clear all positions"""
        self.positions = []

    # ==================== PAYOFF CALCULATION ====================

    def calculate_payoff(self, spot_prices: np.ndarray) -> np.ndarray:
        """
        Calculate strategy payoff across spot prices

        Parameters:
        -----------
        spot_prices : np.ndarray
            Array of spot prices

        Returns:
        --------
        np.ndarray : Payoff values
        """
        if not self.positions:
            return np.zeros_like(spot_prices)

        total_payoff = np.zeros_like(spot_prices, dtype=float)

        for position in self.positions:
            for spot in spot_prices:
                idx = np.where(spot_prices == spot)[0][0]
                total_payoff[idx] += position.payoff_at_expiry(spot)

        return total_payoff

    def calculate_payoff_at_price(self, spot: float) -> float:
        """Calculate total payoff at specific spot price"""
        return sum(pos.payoff_at_expiry(spot) for pos in self.positions)

    # ==================== COST & P&L ====================

    def net_premium(self) -> float:
        """Calculate net premium (paid is negative, received is positive)"""
        net = 0
        for pos in self.positions:
            if pos.position_type == PositionType.LONG:
                net -= pos.total_premium
            else:
                net += pos.total_premium
        return net

    def max_profit(self, spot_range: Tuple[float, float] = None) -> float:
        """
        Calculate maximum profit

        Parameters:
        -----------
        spot_range : Tuple[float, float]
            Range of spot prices to consider (min, max)

        Returns:
        --------
        float : Maximum profit possible
        """
        if not self.positions:
            return 0

        if spot_range is None:
            # Default range: ±50% from average strike
            avg_strike = np.mean([p.strike for p in self.positions])
            spot_range = (avg_strike * 0.5, avg_strike * 1.5)

        spots = np.linspace(spot_range[0], spot_range[1], 1000)
        payoffs = self.calculate_payoff(spots)

        return np.max(payoffs)

    def max_loss(self, spot_range: Tuple[float, float] = None) -> float:
        """Calculate maximum loss"""
        if not self.positions:
            return 0

        if spot_range is None:
            avg_strike = np.mean([p.strike for p in self.positions])
            spot_range = (avg_strike * 0.5, avg_strike * 1.5)

        spots = np.linspace(spot_range[0], spot_range[1], 1000)
        payoffs = self.calculate_payoff(spots)

        return np.min(payoffs)

    # ==================== BREAKEVEN ====================

    def breakeven_points(self, spot_range: Tuple[float, float] = None,
                        tolerance: float = 1.0) -> List[float]:
        """
        Find breakeven points (where payoff = 0)

        Parameters:
        -----------
        tolerance : float
            Acceptable range around zero to consider breakeven

        Returns:
        --------
        List[float] : List of breakeven prices
        """
        if not self.positions:
            return []

        if spot_range is None:
            avg_strike = np.mean([p.strike for p in self.positions])
            spot_range = (avg_strike * 0.5, avg_strike * 1.5)

        spots = np.linspace(spot_range[0], spot_range[1], 10000)
        payoffs = self.calculate_payoff(spots)

        # Find zero crossings
        breakevens = []
        for i in range(len(payoffs) - 1):
            if abs(payoffs[i]) <= tolerance:
                breakevens.append(spots[i])
            elif payoffs[i] * payoffs[i + 1] < 0:  # Sign change
                # Linear interpolation for more accuracy
                be = spots[i] - payoffs[i] * (spots[i + 1] - spots[i]) / (payoffs[i + 1] - payoffs[i])
                breakevens.append(be)

        # Remove duplicates (within tolerance)
        breakevens = sorted(set(round(be, 2) for be in breakevens))

        return breakevens

    # ==================== RISK METRICS ====================

    def risk_reward_ratio(self) -> float:
        """Calculate risk-reward ratio"""
        max_loss = abs(self.max_loss())
        max_profit = self.max_profit()

        if max_profit == 0:
            return 0

        return max_loss / max_profit

    def return_on_capital(self) -> float:
        """
        Calculate return on capital (%)

        ROC = (Max Profit / Capital Required) * 100
        """
        capital = abs(self.net_premium())

        if capital == 0:
            return 0

        return (self.max_profit() / capital) * 100

    def probability_of_profit(self, current_spot: float, volatility: float,
                             days_to_expiry: int, num_simulations: int = 10000) -> float:
        """
        Estimate probability of profit using Monte Carlo simulation

        Parameters:
        -----------
        current_spot : float
            Current underlying price
        volatility : float
            Annual volatility (e.g., 0.15 for 15%)
        days_to_expiry : int
            Days until expiry
        num_simulations : int
            Number of Monte Carlo simulations

        Returns:
        --------
        float : Probability of profit (0-1)
        """
        T = days_to_expiry / 365
        dt = T

        # Generate random price paths
        z = np.random.standard_normal(num_simulations)
        final_prices = current_spot * np.exp((- 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * z)

        # Calculate payoffs
        payoffs = np.array([self.calculate_payoff_at_price(price) for price in final_prices])

        # Probability of profit
        prob = np.sum(payoffs > 0) / num_simulations

        return prob

    # ==================== GREEKS ====================

    def portfolio_greeks(self, greeks_per_position: List[Dict]) -> Dict[str, float]:
        """
        Calculate portfolio-level Greeks

        Parameters:
        -----------
        greeks_per_position : List[Dict]
            List of Greeks dicts for each position
            Each dict should have keys: delta, gamma, vega, theta, rho

        Returns:
        --------
        Dict[str, float] : Aggregated Greeks
        """
        portfolio = {
            'delta': 0.0,
            'gamma': 0.0,
            'vega': 0.0,
            'theta': 0.0,
            'rho': 0.0
        }

        for pos, greeks in zip(self.positions, greeks_per_position):
            multiplier = pos.position_type.value * pos.total_lots

            for greek_name in portfolio.keys():
                portfolio[greek_name] += greeks.get(greek_name, 0) * multiplier

        return portfolio

    # ==================== VISUALIZATION ====================

    def plot_payoff(self, spot_range: Tuple[float, float] = None,
                   current_spot: Optional[float] = None,
                   figsize: Tuple[int, int] = (12, 6)) -> None:
        """
        Plot payoff diagram

        Parameters:
        -----------
        spot_range : Tuple[float, float]
            Range of spot prices (min, max)
        current_spot : float
            Current spot price (mark on chart)
        """
        if not self.positions:
            print("No positions to plot")
            return

        # Determine spot range
        if spot_range is None:
            strikes = [p.strike for p in self.positions]
            min_strike, max_strike = min(strikes), max(strikes)
            range_width = max_strike - min_strike
            spot_range = (min_strike - range_width * 0.5, max_strike + range_width * 0.5)

        # Generate spot prices
        spots = np.linspace(spot_range[0], spot_range[1], 1000)
        payoffs = self.calculate_payoff(spots)

        # Create plot
        fig, ax = plt.subplots(figsize=figsize)

        # Plot payoff line
        ax.plot(spots, payoffs, linewidth=2, label='Payoff', color='blue')

        # Mark zero line
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)

        # Mark current spot
        if current_spot:
            current_payoff = self.calculate_payoff_at_price(current_spot)
            ax.axvline(x=current_spot, color='red', linestyle='--', linewidth=1,
                      label=f'Current Spot: ₹{current_spot:,.0f}')
            ax.plot(current_spot, current_payoff, 'ro', markersize=10)

        # Mark breakeven points
        breakevens = self.breakeven_points(spot_range)
        for be in breakevens:
            ax.axvline(x=be, color='green', linestyle=':', linewidth=1, alpha=0.7)
            ax.plot(be, 0, 'go', markersize=8)

        # Add profit/loss regions
        ax.fill_between(spots, 0, payoffs, where=(payoffs > 0),
                        alpha=0.3, color='green', label='Profit')
        ax.fill_between(spots, 0, payoffs, where=(payoffs < 0),
                        alpha=0.3, color='red', label='Loss')

        # Labels and title
        ax.set_xlabel('Spot Price (₹)', fontsize=12)
        ax.set_ylabel('Profit/Loss (₹)', fontsize=12)
        ax.set_title(f'{self.name} - Payoff Diagram', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')

        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))

        plt.tight_layout()
        plt.show()

    def summary(self) -> pd.DataFrame:
        """Get strategy summary as DataFrame"""
        data = {
            'Position': [str(pos) for pos in self.positions],
            'Strike': [pos.strike for pos in self.positions],
            'Type': [pos.option_type.value for pos in self.positions],
            'Position': [pos.position_type.name for pos in self.positions],
            'Premium': [pos.premium for pos in self.positions],
            'Quantity': [pos.quantity for pos in self.positions],
            'Lot Size': [pos.lot_size for pos in self.positions],
            'Total Premium': [pos.total_premium for pos in self.positions]
        }

        df = pd.DataFrame(data)

        return df

    def print_summary(self) -> None:
        """Print strategy summary"""
        print("=" * 80)
        print(f"STRATEGY: {self.name}")
        print("=" * 80)
        if self.description:
            print(f"Description: {self.description}")
            print()

        if not self.positions:
            print("No positions")
            return

        print("Positions:")
        print("-" * 80)
        for i, pos in enumerate(self.positions, 1):
            print(f"{i}. {pos}")

        print("\n" + "-" * 80)
        print("RISK METRICS:")
        print("-" * 80)
        print(f"{'Net Premium':<25}: ₹{self.net_premium():>15,.2f}")
        print(f"{'Max Profit':<25}: ₹{self.max_profit():>15,.2f}")
        print(f"{'Max Loss':<25}: ₹{self.max_loss():>15,.2f}")
        print(f"{'Risk/Reward Ratio':<25}: {self.risk_reward_ratio():>18.2f}")
        print(f"{'Return on Capital':<25}: {self.return_on_capital():>17.2f}%")

        breakevens = self.breakeven_points()
        if breakevens:
            be_str = ', '.join([f"₹{be:,.2f}" for be in breakevens])
            print(f"{'Breakeven Points':<25}: {be_str}")

        print("=" * 80)

    def __repr__(self) -> str:
        return f"<{self.name}: {len(self.positions)} positions>"


if __name__ == "__main__":
    # Example: Simple Bull Call Spread
    strategy = BaseStrategy("Bull Call Spread Example")

    # Long 19500 CE @ ₹150
    strategy.add_position(Position(
        strike=19500,
        option_type=OptionType.CALL,
        position_type=PositionType.LONG,
        premium=150,
        quantity=1,
        lot_size=50
    ))

    # Short 19600 CE @ ₹100
    strategy.add_position(Position(
        strike=19600,
        option_type=OptionType.CALL,
        position_type=PositionType.SHORT,
        premium=100,
        quantity=1,
        lot_size=50
    ))

    # Print summary
    strategy.print_summary()

    # Plot payoff
    # strategy.plot_payoff(current_spot=19500)
