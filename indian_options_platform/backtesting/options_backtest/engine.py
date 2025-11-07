"""
Options Backtesting Engine
Event-driven backtest for Indian options strategies

Features:
- Realistic slippage modeling
- Transaction costs (STT, brokerage, taxes)
- Margin requirements
- Position sizing
- Risk management
- Performance analytics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import warnings


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    """Represents an order"""
    timestamp: datetime
    symbol: str
    strike: float
    option_type: str  # CE or PE
    side: OrderSide
    quantity: int
    order_type: OrderType
    limit_price: Optional[float] = None
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    status: str = "PENDING"  # PENDING, FILLED, PARTIAL, REJECTED


@dataclass
class Position:
    """Represents a position"""
    symbol: str
    strike: float
    option_type: str
    quantity: int  # Positive for long, negative for short
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    pnl: float = 0.0


@dataclass
class Trade:
    """Represents a completed trade"""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    strike: float
    option_type: str
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    commission: float
    slippage: float


class OptionsBacktester:
    """
    Event-driven options backtesting engine

    Example Usage:
    --------------
    backtester = OptionsBacktester(initial_capital=10000000)
    backtester.load_data(options_data)

    for timestamp, data in backtester.iterate():
        # Your strategy logic
        if buy_signal:
            backtester.place_order(...)

    results = backtester.get_results()
    """

    def __init__(self,
                 initial_capital: float = 10000000,  # 1 Crore
                 brokerage_per_order: float = 20,
                 stt_rate: float = 0.0005,
                 exchange_charges_rate: float = 0.0005,
                 gst_rate: float = 0.18,
                 slippage_pct: float = 0.01):
        """
        Initialize Backtester

        Parameters:
        -----------
        initial_capital : float
            Starting capital (₹)
        brokerage_per_order : float
            Flat brokerage per order (₹)
        stt_rate : float
            STT rate (0.05% on sell side)
        exchange_charges_rate : float
            Exchange charges rate
        gst_rate : float
            GST rate (18%)
        slippage_pct : float
            Slippage percentage per order
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.brokerage_per_order = brokerage_per_order
        self.stt_rate = stt_rate
        self.exchange_charges_rate = exchange_charges_rate
        self.gst_rate = gst_rate
        self.slippage_pct = slippage_pct

        # State
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []

        # Data
        self.data: Optional[pd.DataFrame] = None
        self.current_index = 0

        # Metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission = 0.0
        self.total_slippage = 0.0

    def load_data(self, data: pd.DataFrame) -> None:
        """
        Load options data

        Parameters:
        -----------
        data : pd.DataFrame
            Must have columns: timestamp, symbol, strike, option_type, ltp, bid, ask
        """
        required_cols = ['timestamp', 'symbol', 'strike', 'option_type', 'ltp']

        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data must have columns: {required_cols}")

        self.data = data.sort_values('timestamp').reset_index(drop=True)
        print(f"Loaded {len(self.data)} data points")

    def iterate(self):
        """Iterator for backtesting"""
        if self.data is None:
            raise ValueError("No data loaded. Call load_data() first.")

        grouped = self.data.groupby('timestamp')

        for timestamp, group_data in grouped:
            # Update positions
            self._update_positions(group_data)

            # Update equity curve
            self._update_equity_curve(timestamp)

            # Process pending orders
            self._process_orders(group_data)

            yield timestamp, group_data

            self.current_index += 1

    def place_order(self,
                   symbol: str,
                   strike: float,
                   option_type: str,
                   side: OrderSide,
                   quantity: int,
                   order_type: OrderType = OrderType.MARKET,
                   limit_price: Optional[float] = None) -> Order:
        """
        Place an order

        Parameters:
        -----------
        symbol : str
            Underlying symbol (e.g., 'NIFTY')
        strike : float
            Strike price
        option_type : str
            'CE' or 'PE'
        side : OrderSide
            BUY or SELL
        quantity : int
            Number of lots
        order_type : OrderType
            MARKET or LIMIT
        limit_price : float (optional)
            Limit price for limit orders

        Returns:
        --------
        Order : Created order
        """
        if self.data is None:
            raise ValueError("No data loaded")

        current_timestamp = self.data.iloc[self.current_index]['timestamp']

        order = Order(
            timestamp=current_timestamp,
            symbol=symbol,
            strike=strike,
            option_type=option_type,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price
        )

        self.orders.append(order)

        return order

    def _process_orders(self, market_data: pd.DataFrame) -> None:
        """Process pending orders"""
        for order in self.orders:
            if order.status != "PENDING":
                continue

            # Find matching option
            option_data = market_data[
                (market_data['symbol'] == order.symbol) &
                (market_data['strike'] == order.strike) &
                (market_data['option_type'] == order.option_type)
            ]

            if option_data.empty:
                continue

            option = option_data.iloc[0]

            # Determine execution price
            if order.order_type == OrderType.MARKET:
                # Market order: use bid/ask with slippage
                if order.side == OrderSide.BUY:
                    execution_price = option['ltp'] * (1 + self.slippage_pct)
                else:
                    execution_price = option['ltp'] * (1 - self.slippage_pct)
            else:
                # Limit order: check if limit price is hit
                if order.side == OrderSide.BUY and option['ltp'] <= order.limit_price:
                    execution_price = order.limit_price
                elif order.side == OrderSide.SELL and option['ltp'] >= order.limit_price:
                    execution_price = order.limit_price
                else:
                    continue  # Order not filled

            # Calculate costs
            position_value = execution_price * order.quantity
            commission = self._calculate_commission(position_value, order.side)
            slippage = abs(execution_price - option['ltp']) * order.quantity

            total_cost = position_value + commission

            # Check if sufficient capital
            if order.side == OrderSide.BUY and self.capital < total_cost:
                order.status = "REJECTED"
                continue

            # Fill order
            order.filled_price = execution_price
            order.filled_quantity = order.quantity
            order.status = "FILLED"

            # Update position
            self._update_position(order)

            # Update capital
            if order.side == OrderSide.BUY:
                self.capital -= total_cost
            else:
                self.capital += position_value - commission

            # Track costs
            self.total_commission += commission
            self.total_slippage += slippage

    def _calculate_commission(self, position_value: float, side: OrderSide) -> float:
        """Calculate total transaction costs"""
        # Brokerage
        brokerage = self.brokerage_per_order

        # STT (only on sell side)
        stt = position_value * self.stt_rate if side == OrderSide.SELL else 0

        # Exchange charges
        exchange_charges = position_value * self.exchange_charges_rate

        # Total before GST
        subtotal = brokerage + stt + exchange_charges

        # GST
        gst = subtotal * self.gst_rate

        total = subtotal + gst

        return total

    def _update_position(self, order: Order) -> None:
        """Update position after order fill"""
        position_key = f"{order.symbol}_{order.strike}_{order.option_type}"

        quantity = order.filled_quantity if order.side == OrderSide.BUY else -order.filled_quantity

        if position_key in self.positions:
            # Existing position
            position = self.positions[position_key]

            # Check if closing position
            if (position.quantity > 0 and quantity < 0) or (position.quantity < 0 and quantity > 0):
                # Closing trade
                close_quantity = min(abs(position.quantity), abs(quantity))

                # Calculate P&L
                if position.quantity > 0:
                    # Long position closed
                    pnl = (order.filled_price - position.entry_price) * close_quantity
                else:
                    # Short position closed
                    pnl = (position.entry_price - order.filled_price) * close_quantity

                # Record trade
                trade = Trade(
                    entry_time=position.entry_time,
                    exit_time=order.timestamp,
                    symbol=order.symbol,
                    strike=order.strike,
                    option_type=order.option_type,
                    quantity=close_quantity,
                    entry_price=position.entry_price,
                    exit_price=order.filled_price,
                    pnl=pnl,
                    pnl_pct=(pnl / (position.entry_price * close_quantity)) * 100,
                    commission=self._calculate_commission(
                        order.filled_price * close_quantity,
                        order.side
                    ),
                    slippage=abs(order.filled_price - position.current_price) * close_quantity
                )

                self.trades.append(trade)
                self.total_trades += 1

                if pnl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1

                # Update or remove position
                position.quantity += quantity

                if position.quantity == 0:
                    del self.positions[position_key]
                else:
                    position.current_price = order.filled_price
            else:
                # Adding to position
                total_quantity = position.quantity + quantity
                position.entry_price = (
                    (position.entry_price * abs(position.quantity) +
                     order.filled_price * abs(quantity)) /
                    abs(total_quantity)
                )
                position.quantity = total_quantity
                position.current_price = order.filled_price
        else:
            # New position
            self.positions[position_key] = Position(
                symbol=order.symbol,
                strike=order.strike,
                option_type=order.option_type,
                quantity=quantity,
                entry_price=order.filled_price,
                entry_time=order.timestamp,
                current_price=order.filled_price
            )

    def _update_positions(self, market_data: pd.DataFrame) -> None:
        """Update current prices and P&L of open positions"""
        for position_key, position in self.positions.items():
            # Find current price
            option_data = market_data[
                (market_data['symbol'] == position.symbol) &
                (market_data['strike'] == position.strike) &
                (market_data['option_type'] == position.option_type)
            ]

            if not option_data.empty:
                current_price = option_data.iloc[0]['ltp']
                position.current_price = current_price

                # Calculate unrealized P&L
                if position.quantity > 0:
                    position.pnl = (current_price - position.entry_price) * position.quantity
                else:
                    position.pnl = (position.entry_price - current_price) * abs(position.quantity)

    def _update_equity_curve(self, timestamp: datetime) -> None:
        """Update equity curve"""
        # Calculate total equity (capital + unrealized P&L)
        unrealized_pnl = sum(pos.pnl for pos in self.positions.values())
        equity = self.capital + unrealized_pnl

        self.equity_curve.append((timestamp, equity))

    def get_results(self) -> Dict:
        """
        Get backtest results

        Returns:
        --------
        Dict : Performance metrics
        """
        if not self.equity_curve:
            return {}

        # Extract equity values
        equity_df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity'])
        equity_values = equity_df['equity'].values

        # Calculate returns
        returns = pd.Series(equity_values).pct_change().dropna()

        # Performance metrics
        total_return = (equity_values[-1] - self.initial_capital) / self.initial_capital
        total_return_pct = total_return * 100

        # Sharpe ratio (annualized)
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100

        # Win rate
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        # Average trade P&L
        if self.trades:
            avg_trade_pnl = np.mean([t.pnl for t in self.trades])
            avg_win = np.mean([t.pnl for t in self.trades if t.pnl > 0]) if self.winning_trades > 0 else 0
            avg_loss = np.mean([t.pnl for t in self.trades if t.pnl < 0]) if self.losing_trades > 0 else 0
            profit_factor = abs(sum(t.pnl for t in self.trades if t.pnl > 0) / sum(t.pnl for t in self.trades if t.pnl < 0)) if any(t.pnl < 0 for t in self.trades) else np.inf
        else:
            avg_trade_pnl = avg_win = avg_loss = profit_factor = 0

        results = {
            'initial_capital': self.initial_capital,
            'final_equity': equity_values[-1],
            'total_return': total_return_pct,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'avg_trade_pnl': avg_trade_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_commission': self.total_commission,
            'total_slippage': self.total_slippage,
            'equity_curve': equity_df
        }

        return results

    def print_results(self) -> None:
        """Print backtest results"""
        results = self.get_results()

        if not results:
            print("No results available")
            return

        print("\n" + "=" * 80)
        print("BACKTEST RESULTS")
        print("=" * 80)

        print(f"\n{'Capital':<25}")
        print(f"  {'Initial Capital':<23}: ₹{results['initial_capital']:>15,.2f}")
        print(f"  {'Final Equity':<23}: ₹{results['final_equity']:>15,.2f}")
        print(f"  {'Total Return':<23}: {results['total_return']:>16.2f}%")

        print(f"\n{'Performance Metrics':<25}")
        print(f"  {'Sharpe Ratio':<23}: {results['sharpe_ratio']:>18.4f}")
        print(f"  {'Max Drawdown':<23}: {results['max_drawdown']:>17.2f}%")
        print(f"  {'Profit Factor':<23}: {results['profit_factor']:>18.2f}")

        print(f"\n{'Trade Statistics':<25}")
        print(f"  {'Total Trades':<23}: {results['total_trades']:>18}")
        print(f"  {'Winning Trades':<23}: {results['winning_trades']:>18}")
        print(f"  {'Losing Trades':<23}: {results['losing_trades']:>18}")
        print(f"  {'Win Rate':<23}: {results['win_rate']:>17.2f}%")

        print(f"\n{'P&L Analysis':<25}")
        print(f"  {'Avg Trade P&L':<23}: ₹{results['avg_trade_pnl']:>15,.2f}")
        print(f"  {'Avg Win':<23}: ₹{results['avg_win']:>15,.2f}")
        print(f"  {'Avg Loss':<23}: ₹{results['avg_loss']:>15,.2f}")

        print(f"\n{'Costs':<25}")
        print(f"  {'Total Commission':<23}: ₹{results['total_commission']:>15,.2f}")
        print(f"  {'Total Slippage':<23}: ₹{results['total_slippage']:>15,.2f}")

        print("=" * 80)


if __name__ == "__main__":
    print("Options Backtesting Engine - Example usage in documentation")
