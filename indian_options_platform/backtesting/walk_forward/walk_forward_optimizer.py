"""
Walk-Forward Optimization
Realistic strategy optimization with out-of-sample testing

Walk-Forward Analysis:
- Train on in-sample data
- Test on out-of-sample data
- Rolling window approach
- Prevents overfitting

Example:
--------
Total data: 2 years
Window: 6 months train, 2 months test

Train Jan-Jun → Test Jul-Aug
Train Feb-Jul → Test Aug-Sep
Train Mar-Aug → Test Sep-Oct
...
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardWindow:
    """Single walk-forward window"""
    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_data: pd.DataFrame = None
    test_data: pd.DataFrame = None
    best_params: Dict = None
    train_performance: Dict = None
    test_performance: Dict = None


@dataclass
class WalkForwardResults:
    """Walk-forward optimization results"""
    windows: List[WalkForwardWindow]
    total_train_performance: Dict
    total_test_performance: Dict
    parameter_stability: Dict
    efficiency_ratio: float  # Test / Train performance


class WalkForwardOptimizer:
    """
    Walk-Forward Optimization Engine

    Features:
    ---------
    1. Rolling window optimization
    2. Anchored window optimization
    3. Parameter stability analysis
    4. Out-of-sample performance
    5. Overfitting detection

    Example:
    --------
    >>> optimizer = WalkForwardOptimizer(
    ...     train_period_days=180,  # 6 months
    ...     test_period_days=60,    # 2 months
    ...     step_days=30            # 1 month step
    ... )
    >>>
    >>> results = optimizer.optimize(
    ...     data=historical_data,
    ...     strategy_func=backtest_strategy,
    ...     param_grid={'lookback': [10, 20, 30], 'threshold': [0.1, 0.2]}
    ... )
    """

    def __init__(self,
                 train_period_days: int = 180,
                 test_period_days: int = 60,
                 step_days: int = 30,
                 anchored: bool = False,
                 min_train_size: int = 100,
                 parallel: bool = True,
                 max_workers: int = 4):
        """
        Initialize Walk-Forward Optimizer

        Parameters:
        -----------
        train_period_days : int
            Training window size (days)
        test_period_days : int
            Testing window size (days)
        step_days : int
            Step size for rolling window (days)
        anchored : bool
            If True, anchor training start date (expanding window)
        min_train_size : int
            Minimum training data points required
        parallel : bool
            Use parallel processing
        max_workers : int
            Max parallel workers
        """
        self.train_period_days = train_period_days
        self.test_period_days = test_period_days
        self.step_days = step_days
        self.anchored = anchored
        self.min_train_size = min_train_size
        self.parallel = parallel
        self.max_workers = max_workers

        logger.info(f"WalkForwardOptimizer initialized: "
                   f"Train={train_period_days}d, Test={test_period_days}d, "
                   f"Step={step_days}d, Anchored={anchored}")

    def create_windows(self, data: pd.DataFrame) -> List[WalkForwardWindow]:
        """
        Create walk-forward windows

        Parameters:
        -----------
        data : pd.DataFrame
            Time-indexed data

        Returns:
        --------
        List[WalkForwardWindow] : List of windows
        """
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data must have DatetimeIndex")

        windows = []
        window_id = 0

        start_date = data.index[0]
        end_date = data.index[-1]

        current_train_start = start_date

        while True:
            # Calculate window dates
            if self.anchored:
                train_start = start_date  # Anchored - always start from beginning
            else:
                train_start = current_train_start

            train_end = train_start + timedelta(days=self.train_period_days)
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=self.test_period_days)

            # Check if we have enough data
            if test_end > end_date:
                break

            # Extract data for this window
            train_mask = (data.index >= train_start) & (data.index < test_start)
            test_mask = (data.index >= test_start) & (data.index <= test_end)

            train_data = data[train_mask]
            test_data = data[test_mask]

            # Validate minimum size
            if len(train_data) < self.min_train_size:
                logger.warning(f"Window {window_id}: Insufficient training data ({len(train_data)} < {self.min_train_size})")
                break

            # Create window
            window = WalkForwardWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                train_data=train_data,
                test_data=test_data
            )

            windows.append(window)

            logger.info(f"Window {window_id}: Train={train_start.date()} to {train_end.date()}, "
                       f"Test={test_start.date()} to {test_end.date()}")

            window_id += 1

            # Move to next window
            current_train_start += timedelta(days=self.step_days)

        logger.info(f"Created {len(windows)} walk-forward windows")

        return windows

    def optimize(self,
                data: pd.DataFrame,
                strategy_func: Callable,
                param_grid: Dict[str, List],
                metric: str = 'sharpe_ratio') -> WalkForwardResults:
        """
        Perform walk-forward optimization

        Parameters:
        -----------
        data : pd.DataFrame
            Historical data with DatetimeIndex
        strategy_func : Callable
            Strategy backtest function
            Signature: func(data, **params) -> Dict[metrics]
        param_grid : Dict[str, List]
            Parameter grid for optimization
            Example: {'lookback': [10, 20, 30], 'threshold': [0.1, 0.2]}
        metric : str
            Optimization metric (default: 'sharpe_ratio')

        Returns:
        --------
        WalkForwardResults : Optimization results
        """
        # Create windows
        windows = self.create_windows(data)

        if not windows:
            raise ValueError("No windows created - insufficient data")

        # Optimize each window
        if self.parallel:
            windows = self._optimize_parallel(windows, strategy_func, param_grid, metric)
        else:
            windows = self._optimize_sequential(windows, strategy_func, param_grid, metric)

        # Analyze results
        results = self._analyze_results(windows, metric)

        return results

    def _optimize_window(self,
                        window: WalkForwardWindow,
                        strategy_func: Callable,
                        param_grid: Dict[str, List],
                        metric: str) -> WalkForwardWindow:
        """Optimize single window"""
        # Generate parameter combinations
        param_combinations = self._generate_param_combinations(param_grid)

        best_score = -np.inf
        best_params = None
        best_train_perf = None

        # Test each parameter combination on training data
        for params in param_combinations:
            try:
                train_results = strategy_func(window.train_data, **params)

                if metric in train_results:
                    score = train_results[metric]

                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                        best_train_perf = train_results.copy()

            except Exception as e:
                logger.warning(f"Window {window.window_id}, params {params}: {e}")
                continue

        # Test best parameters on out-of-sample data
        if best_params:
            try:
                test_results = strategy_func(window.test_data, **best_params)
            except Exception as e:
                logger.error(f"Window {window.window_id} test failed: {e}")
                test_results = {}
        else:
            logger.warning(f"Window {window.window_id}: No valid parameters found")
            test_results = {}

        # Update window
        window.best_params = best_params
        window.train_performance = best_train_perf
        window.test_performance = test_results

        logger.info(f"Window {window.window_id}: Best params={best_params}, "
                   f"Train {metric}={best_train_perf.get(metric, 0):.4f}, "
                   f"Test {metric}={test_results.get(metric, 0):.4f}")

        return window

    def _optimize_sequential(self,
                            windows: List[WalkForwardWindow],
                            strategy_func: Callable,
                            param_grid: Dict[str, List],
                            metric: str) -> List[WalkForwardWindow]:
        """Optimize windows sequentially"""
        optimized_windows = []

        for window in windows:
            optimized = self._optimize_window(window, strategy_func, param_grid, metric)
            optimized_windows.append(optimized)

        return optimized_windows

    def _optimize_parallel(self,
                          windows: List[WalkForwardWindow],
                          strategy_func: Callable,
                          param_grid: Dict[str, List],
                          metric: str) -> List[WalkForwardWindow]:
        """Optimize windows in parallel"""
        optimized_windows = [None] * len(windows)

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self._optimize_window, window, strategy_func, param_grid, metric): idx
                for idx, window in enumerate(windows)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    optimized_windows[idx] = future.result()
                except Exception as e:
                    logger.error(f"Window {idx} failed: {e}")
                    optimized_windows[idx] = windows[idx]

        return optimized_windows

    def _generate_param_combinations(self, param_grid: Dict[str, List]) -> List[Dict]:
        """Generate all parameter combinations"""
        import itertools

        keys = list(param_grid.keys())
        values = list(param_grid.values())

        combinations = []
        for combo in itertools.product(*values):
            param_dict = dict(zip(keys, combo))
            combinations.append(param_dict)

        return combinations

    def _analyze_results(self, windows: List[WalkForwardWindow], metric: str) -> WalkForwardResults:
        """Analyze walk-forward results"""
        # Aggregate train performance
        train_metrics = []
        test_metrics = []
        params_list = []

        for window in windows:
            if window.train_performance and metric in window.train_performance:
                train_metrics.append(window.train_performance[metric])

            if window.test_performance and metric in window.test_performance:
                test_metrics.append(window.test_performance[metric])

            if window.best_params:
                params_list.append(window.best_params)

        # Calculate aggregate performance
        total_train_perf = {
            metric: np.mean(train_metrics) if train_metrics else 0,
            f'{metric}_std': np.std(train_metrics) if train_metrics else 0,
            'num_windows': len(train_metrics)
        }

        total_test_perf = {
            metric: np.mean(test_metrics) if test_metrics else 0,
            f'{metric}_std': np.std(test_metrics) if test_metrics else 0,
            'num_windows': len(test_metrics)
        }

        # Parameter stability analysis
        param_stability = self._analyze_parameter_stability(params_list)

        # Efficiency ratio (out-of-sample / in-sample)
        if total_train_perf[metric] != 0:
            efficiency_ratio = total_test_perf[metric] / total_train_perf[metric]
        else:
            efficiency_ratio = 0

        results = WalkForwardResults(
            windows=windows,
            total_train_performance=total_train_perf,
            total_test_performance=total_test_perf,
            parameter_stability=param_stability,
            efficiency_ratio=efficiency_ratio
        )

        return results

    def _analyze_parameter_stability(self, params_list: List[Dict]) -> Dict:
        """Analyze parameter stability across windows"""
        if not params_list:
            return {}

        stability = {}

        # Get all parameter names
        param_names = set()
        for params in params_list:
            param_names.update(params.keys())

        # Analyze each parameter
        for param_name in param_names:
            values = [p[param_name] for p in params_list if param_name in p]

            if values:
                stability[param_name] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'stability_score': 1 - (np.std(values) / np.mean(values)) if np.mean(values) != 0 else 0
                }

        return stability

    def print_results(self, results: WalkForwardResults, metric: str = 'sharpe_ratio') -> None:
        """Print walk-forward results"""
        print("=" * 80)
        print("WALK-FORWARD OPTIMIZATION RESULTS")
        print("=" * 80)
        print()

        print("OVERALL PERFORMANCE:")
        print("-" * 80)
        print(f"{'Metric':<30}: {metric}")
        print(f"{'Number of Windows':<30}: {len(results.windows)}")
        print()

        print(f"IN-SAMPLE (Training):")
        print(f"  {metric:<28}: {results.total_train_performance[metric]:>10.4f}")
        print(f"  Std Dev:<30}: {results.total_train_performance.get(f'{metric}_std', 0):>10.4f}")
        print()

        print(f"OUT-OF-SAMPLE (Testing):")
        print(f"  {metric:<28}: {results.total_test_performance[metric]:>10.4f}")
        print(f"  Std Dev:<30}: {results.total_test_performance.get(f'{metric}_std', 0):>10.4f}")
        print()

        print(f"{'Efficiency Ratio (OOS/IS)':<30}: {results.efficiency_ratio:>10.2%}")
        print()

        if results.efficiency_ratio > 0.7:
            print("✓ Good efficiency - Low overfitting")
        elif results.efficiency_ratio > 0.4:
            print("⚠ Moderate efficiency - Some overfitting")
        else:
            print("✗ Low efficiency - High overfitting risk")

        print()
        print("PARAMETER STABILITY:")
        print("-" * 80)

        for param_name, stats in results.parameter_stability.items():
            print(f"{param_name}:")
            print(f"  Mean: {stats['mean']:.4f}, Std: {stats['std']:.4f}")
            print(f"  Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
            print(f"  Stability Score: {stats['stability_score']:.2%}")
            print()

        print("=" * 80)


if __name__ == "__main__":
    # Example usage with dummy data
    print("WALK-FORWARD OPTIMIZATION - EXAMPLE")
    print()

    # Create dummy price data
    dates = pd.date_range('2023-01-01', '2024-12-31', freq='D')
    prices = 19000 + np.cumsum(np.random.randn(len(dates)) * 50)
    data = pd.DataFrame({'close': prices}, index=dates)

    # Simple moving average strategy
    def backtest_sma_strategy(data, lookback=20, threshold=0.02):
        """Simple SMA crossover strategy"""
        data = data.copy()
        data['sma'] = data['close'].rolling(lookback).mean()
        data['signal'] = ((data['close'] - data['sma']) / data['sma']) > threshold

        # Calculate returns
        data['returns'] = data['close'].pct_change()
        data['strategy_returns'] = data['signal'].shift(1) * data['returns']

        # Metrics
        total_return = (1 + data['strategy_returns'].dropna()).prod() - 1
        sharpe_ratio = data['strategy_returns'].mean() / data['strategy_returns'].std() * np.sqrt(252)

        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'num_trades': data['signal'].diff().abs().sum() / 2
        }

    # Run walk-forward optimization
    optimizer = WalkForwardOptimizer(
        train_period_days=180,
        test_period_days=60,
        step_days=30,
        parallel=False  # Sequential for example
    )

    param_grid = {
        'lookback': [10, 20, 30, 50],
        'threshold': [0.01, 0.02, 0.03]
    }

    results = optimizer.optimize(
        data=data,
        strategy_func=backtest_sma_strategy,
        param_grid=param_grid,
        metric='sharpe_ratio'
    )

    # Print results
    optimizer.print_results(results, metric='sharpe_ratio')
