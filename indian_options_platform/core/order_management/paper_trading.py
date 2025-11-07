"""
Paper Trading System
Virtual trading with real-time market data

Features:
- Real-time position tracking
- Realistic order execution
- P&L calculation
- Risk management
- Performance analytics
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


@dataclass
class PaperOrder:
    """Paper trading order"""
    order_id: str
    timestamp: datetime
    symbol: str
    strike: float
    option_type: str  # CE or PE
    side: str  # BUY or SELL
    quantity: int
    order_type: str  # MARKET or LIMIT
    limit_price: Optional[float] = None
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.PENDING
    commission: float = 0.0


@dataclass
class PaperPosition:
    """Paper trading position"""
    symbol: str
    strike: float
    option_type: str
    quantity: int  # Positive = Long, Negative = Short
    avg_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


class PaperTradingAccount:
    """
    Paper Trading Account

    Example Usage:
    --------------
    account = PaperTradingAccount(initial_capital=100000)

    # Place order
    order = account.place_order(
        symbol='NIFTY',
        strike=19500,
        option_type='CE',
        side='BUY',
        quantity=1
    )

    # Update prices
    account.update_price('NIFTY', 19500, 'CE', 155)

    # Get P&L
    pnl = account.get_total_pnl()
    """

    def __init__(self,
                 initial_capital: float = 100000,
                 name: str = "Paper Account",
                 brokerage_per_order: float = 20,
                 enable_margin: bool = False,
                 margin_multiplier: float = 5):
        """
        Initialize paper trading account

        Parameters:
        -----------
        initial_capital : float
            Starting capital (₹)
        name : str
            Account name
        brokerage_per_order : float
            Brokerage per order
        enable_margin : bool
            Enable margin trading
        margin_multiplier : float
            Margin multiplier (if enabled)
        """
        self.name = name
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.brokerage_per_order = brokerage_per_order
        self.enable_margin = enable_margin
        self.margin_multiplier = margin_multiplier

        # State
        self.positions: Dict[str, PaperPosition] = {}
        self.orders: List[PaperOrder] = []
        self.order_counter = 0

        # Metrics
        self.total_commission_paid = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        # History
        self.equity_history: List[Dict] = []

        print(f"Paper Trading Account '{name}' initialized with ₹{initial_capital:,.2f}")

    def place_order(self,
                   symbol: str,
                   strike: float,
                   option_type: str,
                   side: str,
                   quantity: int,
                   order_type: str = 'MARKET',
                   limit_price: Optional[float] = None,
                   current_price: Optional[float] = None) -> PaperOrder:
        """
        Place a paper trading order

        Parameters:
        -----------
        symbol : str
            Underlying symbol
        strike : float
            Strike price
        option_type : str
            'CE' or 'PE'
        side : str
            'BUY' or 'SELL'
        quantity : int
            Number of lots
        order_type : str
            'MARKET' or 'LIMIT'
        limit_price : float (optional)
            Limit price for limit orders
        current_price : float (optional)
            Current market price (for immediate fill)

        Returns:
        --------
        PaperOrder : Created order
        """
        # Generate order ID
        self.order_counter += 1
        order_id = f"PAPER{self.order_counter:06d}"

        # Create order
        order = PaperOrder(
            order_id=order_id,
            timestamp=datetime.now(),
            symbol=symbol,
            strike=strike,
            option_type=option_type,
            side=side.upper(),
            quantity=quantity,
            order_type=order_type.upper(),
            limit_price=limit_price
        )

        # If market price provided, try to fill immediately
        if current_price is not None and order_type.upper() == 'MARKET':
            self._execute_order(order, current_price)

        self.orders.append(order)

        print(f"Order placed: {order_id} - {side} {quantity} {symbol} {strike}{option_type}")

        return order

    def _execute_order(self, order: PaperOrder, execution_price: float) -> bool:
        """Execute an order"""
        # Calculate required capital
        position_value = execution_price * order.quantity

        # Calculate commission
        commission = self.brokerage_per_order

        # Check for limit order price condition
        if order.order_type == 'LIMIT':
            if order.limit_price is None:
                order.status = OrderStatus.REJECTED
                return False

            if order.side == 'BUY' and execution_price > order.limit_price:
                return False  # Price too high
            elif order.side == 'SELL' and execution_price < order.limit_price:
                return False  # Price too low

        # Check capital availability
        if order.side == 'BUY':
            required_capital = position_value + commission

            available_capital = self.cash
            if self.enable_margin:
                available_capital *= self.margin_multiplier

            if required_capital > available_capital:
                order.status = OrderStatus.REJECTED
                print(f"Order {order.order_id} REJECTED - Insufficient capital")
                return False

        # Execute order
        order.filled_price = execution_price
        order.filled_quantity = order.quantity
        order.commission = commission
        order.status = OrderStatus.FILLED

        # Update position
        self._update_position(order)

        # Update cash
        if order.side == 'BUY':
            self.cash -= (position_value + commission)
        else:
            self.cash += (position_value - commission)

        self.total_commission_paid += commission

        print(f"Order {order.order_id} FILLED @ ₹{execution_price:.2f}")

        return True

    def _update_position(self, order: PaperOrder) -> None:
        """Update position after order fill"""
        position_key = f"{order.symbol}_{order.strike}_{order.option_type}"

        qty_change = order.filled_quantity if order.side == 'BUY' else -order.filled_quantity

        if position_key in self.positions:
            position = self.positions[position_key]

            # Check if closing/reducing position
            if (position.quantity > 0 and qty_change < 0) or (position.quantity < 0 and qty_change > 0):
                # Closing trade
                close_qty = min(abs(position.quantity), abs(qty_change))

                # Calculate realized P&L
                if position.quantity > 0:
                    pnl = (order.filled_price - position.avg_price) * close_qty
                else:
                    pnl = (position.avg_price - order.filled_price) * close_qty

                position.realized_pnl += pnl

                self.total_trades += 1
                if pnl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1

                # Update quantity
                new_qty = position.quantity + qty_change

                if new_qty == 0:
                    # Position closed
                    del self.positions[position_key]
                    print(f"Position closed - P&L: ₹{pnl:,.2f}")
                else:
                    position.quantity = new_qty
            else:
                # Adding to position
                total_value = (position.avg_price * abs(position.quantity) +
                              order.filled_price * abs(qty_change))
                new_qty = position.quantity + qty_change
                position.avg_price = total_value / abs(new_qty)
                position.quantity = new_qty
        else:
            # New position
            self.positions[position_key] = PaperPosition(
                symbol=order.symbol,
                strike=order.strike,
                option_type=order.option_type,
                quantity=qty_change,
                avg_price=order.filled_price,
                current_price=order.filled_price
            )

            print(f"New position opened: {position_key}")

    def update_price(self, symbol: str, strike: float, option_type: str, price: float) -> None:
        """
        Update current price for a position

        Parameters:
        -----------
        symbol : str
            Underlying symbol
        strike : float
            Strike price
        option_type : str
            'CE' or 'PE'
        price : float
            Current market price
        """
        position_key = f"{symbol}_{strike}_{option_type}"

        if position_key in self.positions:
            position = self.positions[position_key]
            position.current_price = price

            # Calculate unrealized P&L
            if position.quantity > 0:
                position.unrealized_pnl = (price - position.avg_price) * position.quantity
            else:
                position.unrealized_pnl = (position.avg_price - price) * abs(position.quantity)

    def get_total_pnl(self) -> float:
        """Get total P&L (realized + unrealized)"""
        realized = sum(pos.realized_pnl for pos in self.positions.values())
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return realized + unrealized

    def get_equity(self) -> float:
        """Get total equity (cash + position value)"""
        return self.cash + self.get_total_pnl()

    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        total_pnl = self.get_total_pnl()
        equity = self.get_equity()
        returns_pct = ((equity - self.initial_capital) / self.initial_capital) * 100

        summary = {
            'account_name': self.name,
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'equity': equity,
            'total_pnl': total_pnl,
            'returns_pct': returns_pct,
            'open_positions': len(self.positions),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'total_commission': self.total_commission_paid
        }

        return summary

    def print_portfolio(self) -> None:
        """Print portfolio summary"""
        summary = self.get_portfolio_summary()

        print("\n" + "=" * 80)
        print(f"PAPER TRADING ACCOUNT: {summary['account_name']}")
        print("=" * 80)

        print(f"\n{'Account Value':<25}")
        print(f"  {'Initial Capital':<23}: ₹{summary['initial_capital']:>15,.2f}")
        print(f"  {'Cash':<23}: ₹{summary['cash']:>15,.2f}")
        print(f"  {'Equity':<23}: ₹{summary['equity']:>15,.2f}")
        print(f"  {'Total P&L':<23}: ₹{summary['total_pnl']:>15,.2f}")
        print(f"  {'Returns':<23}: {summary['returns_pct']:>16.2f}%")

        print(f"\n{'Trading Statistics':<25}")
        print(f"  {'Open Positions':<23}: {summary['open_positions']:>18}")
        print(f"  {'Total Trades':<23}: {summary['total_trades']:>18}")
        print(f"  {'Winning Trades':<23}: {summary['winning_trades']:>18}")
        print(f"  {'Losing Trades':<23}: {summary['losing_trades']:>18}")
        print(f"  {'Win Rate':<23}: {summary['win_rate']:>17.2f}%")
        print(f"  {'Total Commission':<23}: ₹{summary['total_commission']:>15,.2f}")

        if self.positions:
            print(f"\n{'Open Positions':<25}")
            print("-" * 80)
            print(f"{'Symbol':<15} {'Strike':<10} {'Type':<8} {'Qty':<8} {'Avg Price':<12} {'Current':<12} {'P&L':<12}")
            print("-" * 80)

            for pos_key, pos in self.positions.items():
                print(f"{pos.symbol:<15} {pos.strike:<10.0f} {pos.option_type:<8} "
                      f"{pos.quantity:<8} ₹{pos.avg_price:<11.2f} ₹{pos.current_price:<11.2f} "
                      f"₹{pos.unrealized_pnl:<11,.2f}")

        print("=" * 80)

    def save_state(self, filepath: str) -> None:
        """Save account state to JSON"""
        state = {
            'account_name': self.name,
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'positions': [
                {
                    'symbol': pos.symbol,
                    'strike': pos.strike,
                    'option_type': pos.option_type,
                    'quantity': pos.quantity,
                    'avg_price': pos.avg_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'realized_pnl': pos.realized_pnl
                }
                for pos in self.positions.values()
            ],
            'metrics': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'total_commission': self.total_commission_paid
            },
            'timestamp': datetime.now().isoformat()
        }

        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"Account state saved to {filepath}")


if __name__ == "__main__":
    print("=" * 80)
    print("PAPER TRADING SYSTEM - EXAMPLE")
    print("=" * 80)

    # Create paper trading account
    account = PaperTradingAccount(initial_capital=100000, name="My Paper Account")

    print("\n--- Scenario: Iron Condor Trade ---\n")

    # Place Iron Condor orders
    # Buy 19300 PE @ ₹30
    account.place_order('NIFTY', 19300, 'PE', 'BUY', 1, current_price=30)

    # Sell 19400 PE @ ₹60
    account.place_order('NIFTY', 19400, 'PE', 'SELL', 1, current_price=60)

    # Sell 19600 CE @ ₹55
    account.place_order('NIFTY', 19600, 'CE', 'SELL', 1, current_price=55)

    # Buy 19700 CE @ ₹25
    account.place_order('NIFTY', 19700, 'CE', 'BUY', 1, current_price=25)

    # Show portfolio
    account.print_portfolio()

    print("\n--- Price Update: Market moves to 19550 ---\n")

    # Update prices (market moved to 19550)
    account.update_price('NIFTY', 19300, 'PE', 15)  # OTM, decreased
    account.update_price('NIFTY', 19400, 'PE', 25)  # OTM, decreased
    account.update_price('NIFTY', 19600, 'CE', 35)  # Slightly ITM, increased
    account.update_price('NIFTY', 19700, 'CE', 20)  # OTM, decreased

    # Show updated portfolio
    account.print_portfolio()

    print("\n--- Closing all positions ---\n")

    # Close all positions
    account.place_order('NIFTY', 19300, 'PE', 'SELL', 1, current_price=15)
    account.place_order('NIFTY', 19400, 'PE', 'BUY', 1, current_price=25)
    account.place_order('NIFTY', 19600, 'CE', 'BUY', 1, current_price=35)
    account.place_order('NIFTY', 19700, 'CE', 'SELL', 1, current_price=20)

    # Final portfolio
    account.print_portfolio()

    print("\n" + "=" * 80)
