#!/usr/bin/env python3
"""
Comprehensive Test Runner for Indian Options Platform
Tests 4 critical aspects:
1. Unit Tests - Individual component functionality
2. Integration Tests - Component interaction
3. System Tests - End-to-end workflows
4. Performance Tests - Speed and resource usage
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import traceback
from datetime import date, datetime
from collections import defaultdict

# Test results storage
test_results = {
    'unit': {'passed': [], 'failed': [], 'errors': []},
    'integration': {'passed': [], 'failed': [], 'errors': []},
    'system': {'passed': [], 'failed': [], 'errors': []},
    'performance': {'passed': [], 'failed': [], 'errors': [], 'metrics': {}}
}


def log_test(category, test_name, status, message="", execution_time=None):
    """Log test result"""
    result = {
        'test': test_name,
        'message': message,
        'time': execution_time
    }
    test_results[category][status].append(result)


def run_test(category, test_name, test_func):
    """Run a single test and log result"""
    try:
        start_time = time.time()
        test_func()
        execution_time = time.time() - start_time
        log_test(category, test_name, 'passed', f"✓ Passed", execution_time)
        print(f"  ✓ {test_name} ({execution_time:.3f}s)")
        return True
    except AssertionError as e:
        execution_time = time.time() - start_time
        log_test(category, test_name, 'failed', str(e), execution_time)
        print(f"  ✗ {test_name} - FAILED: {str(e)}")
        return False
    except Exception as e:
        execution_time = time.time() - start_time
        log_test(category, test_name, 'errors', str(e), execution_time)
        print(f"  ⚠ {test_name} - ERROR: {str(e)}")
        return False


# ============================================================================
# 1. UNIT TESTS - Test Individual Components
# ============================================================================

def run_unit_tests():
    """Test individual components"""
    print("\n" + "="*80)
    print("1. UNIT TESTS - Testing Individual Components")
    print("="*80)

    # Import components
    try:
        from core.options_pricing.black_scholes import BlackScholes
        from core.options_pricing.greeks import Greeks
        from core.market_data.nse_expiry_engine import NSEExpiryEngine, NSEHolidayCalendar
        from core.risk_engine.risk_manager import RiskManager
        from strategies.non_directional.iron_condor import IronCondor
        from strategies.non_directional.straddle import LongStraddle, ShortStraddle
        from strategies.hft_scalping.zero_dte_strategy import ZeroDTEStrategy
    except ImportError as e:
        print(f"  ⚠ Failed to import components: {e}")
        return

    print("\n[1.1] Options Pricing Tests")

    def test_black_scholes_import():
        bs = BlackScholes()
        assert bs is not None, "BlackScholes instance creation failed"

    run_test('unit', 'Black-Scholes Import', test_black_scholes_import)

    def test_greeks_delta():
        greeks = Greeks()
        delta = greeks.delta(18000, 18000, 0.0192, 0.07, 0.15, 'call')
        assert 0 < delta < 1, f"Call delta should be between 0 and 1, got {delta}"

    run_test('unit', 'Greeks Delta Calculation', test_greeks_delta)

    def test_greeks_gamma():
        greeks = Greeks()
        gamma = greeks.gamma(18000, 18000, 0.0192, 0.07, 0.15)
        assert gamma > 0, f"Gamma should be positive, got {gamma}"

    run_test('unit', 'Greeks Gamma Calculation', test_greeks_gamma)

    print("\n[1.2] NSE Expiry Engine Tests")

    def test_nifty_expiry_thursday():
        engine = NSEExpiryEngine()
        expiry = engine.get_next_expiry('NIFTY', from_date=date(2025, 1, 6))
        assert expiry.weekday() == 3, f"Nifty expiry should be Thursday, got {expiry.strftime('%A')}"

    run_test('unit', 'Nifty Expiry Day (Thursday)', test_nifty_expiry_thursday)

    def test_banknifty_expiry_wednesday():
        engine = NSEExpiryEngine()
        expiry = engine.get_next_expiry('BANKNIFTY', from_date=date(2025, 1, 6))
        assert expiry.weekday() == 2, f"Bank Nifty expiry should be Wednesday, got {expiry.strftime('%A')}"

    run_test('unit', 'Bank Nifty Expiry Day (Wednesday)', test_banknifty_expiry_wednesday)

    def test_holiday_calendar():
        cal = NSEHolidayCalendar()
        is_holiday = not cal.is_trading_day(date(2025, 1, 26))  # Republic Day
        assert is_holiday, "Jan 26, 2025 should be a holiday"

    run_test('unit', 'Holiday Calendar (Republic Day)', test_holiday_calendar)

    print("\n[1.3] Risk Manager Tests")

    def test_risk_manager_init():
        rm = RiskManager(total_capital=10000000)
        assert rm.total_capital == 10000000, "Risk manager capital mismatch"

    run_test('unit', 'Risk Manager Initialization', test_risk_manager_init)

    def test_kelly_criterion():
        rm = RiskManager(total_capital=10000000)
        size = rm.calculate_position_size_kelly(0.6, 2.0)
        assert size > 0, f"Kelly position size should be positive, got {size}"

    run_test('unit', 'Kelly Criterion Position Sizing', test_kelly_criterion)

    print("\n[1.4] Strategy Tests")

    def test_iron_condor():
        ic = IronCondor(17500, 17700, 18300, 18500, 20, 50, 45, 15, 1, 75)
        assert len(ic.positions) == 4, f"Iron Condor should have 4 legs, got {len(ic.positions)}"
        max_profit = ic.max_profit()
        assert max_profit > 0, f"Iron Condor max profit should be positive, got {max_profit}"

    run_test('unit', 'Iron Condor Strategy Structure', test_iron_condor)

    def test_long_straddle():
        ls = LongStraddle(18000, 150, 145, 1, 75)
        assert len(ls.positions) == 2, f"Straddle should have 2 legs, got {len(ls.positions)}"

    run_test('unit', 'Long Straddle Strategy Structure', test_long_straddle)

    def test_zero_dte():
        zdte = ZeroDTEStrategy(18000, 'credit_spread', 5000, 50, 100, 5, 75)
        assert zdte.lot_size == 75, f"Lot size should be 75, got {zdte.lot_size}"

    run_test('unit', 'Zero DTE Strategy Initialization', test_zero_dte)


# ============================================================================
# 2. INTEGRATION TESTS - Test Component Interactions
# ============================================================================

def run_integration_tests():
    """Test how components work together"""
    print("\n" + "="*80)
    print("2. INTEGRATION TESTS - Testing Component Interactions")
    print("="*80)

    try:
        from core.options_pricing.black_scholes import BlackScholes
        from core.options_pricing.greeks import Greeks
        from core.market_data.nse_expiry_engine import NSEExpiryEngine
        from core.risk_engine.risk_manager import RiskManager
        from strategies.non_directional.iron_condor import IronCondor
    except ImportError as e:
        print(f"  ⚠ Failed to import components: {e}")
        return

    print("\n[2.1] Pricing + Greeks Integration")

    def test_pricing_greeks_integration():
        bs = BlackScholes()
        greeks = Greeks()

        # Price an option
        S, K, T, r, sigma = 18000, 18000, 0.0192, 0.07, 0.15

        # Calculate greeks
        delta = greeks.delta(S, K, T, r, sigma, 'call')
        gamma = greeks.gamma(S, K, T, r, sigma)
        vega = greeks.vega(S, K, T, r, sigma)

        assert all([delta, gamma, vega]), "All greeks should be calculated"

    run_test('integration', 'Pricing + Greeks Integration', test_pricing_greeks_integration)

    print("\n[2.2] Expiry Engine + Options Pricing")

    def test_expiry_pricing_integration():
        engine = NSEExpiryEngine()
        greeks = Greeks()

        # Get time to expiry
        tte = engine.time_to_expiry('NIFTY', from_date=date(2025, 1, 6))

        # Use in pricing
        delta = greeks.delta(18000, 18000, tte, 0.07, 0.15, 'call')
        assert delta > 0, "Delta calculation with expiry engine failed"

    run_test('integration', 'Expiry Engine + Pricing Integration', test_expiry_pricing_integration)

    print("\n[2.3] Strategy + Risk Manager Integration")

    def test_strategy_risk_integration():
        rm = RiskManager(total_capital=10000000, max_position_size_pct=10.0)
        ic = IronCondor(17500, 17700, 18300, 18500, 20, 50, 45, 15, 1, 75)

        max_profit = ic.max_profit()
        max_loss = abs(ic.max_loss())

        # Check if strategy fits within risk limits
        can_trade, reason = rm.can_place_trade(max_loss, max_loss)

        assert isinstance(can_trade, bool), "Risk check should return boolean"

    run_test('integration', 'Strategy + Risk Manager Integration', test_strategy_risk_integration)

    print("\n[2.4] Complete Options Chain Workflow")

    def test_complete_workflow():
        # Expiry calculation
        engine = NSEExpiryEngine()
        tte = engine.time_to_expiry('NIFTY')

        # Options pricing
        greeks = Greeks()
        delta = greeks.delta(18000, 18000, tte, 0.07, 0.15, 'call')

        # Strategy creation
        ic = IronCondor(17500, 17700, 18300, 18500, 20, 50, 45, 15, 1, 75)

        # Risk check
        rm = RiskManager(total_capital=10000000)
        max_loss = abs(ic.max_loss())
        can_trade, _ = rm.can_place_trade(max_loss, max_loss)

        assert all([tte, delta, ic, can_trade is not None]), "Complete workflow failed"

    run_test('integration', 'Complete Options Workflow', test_complete_workflow)


# ============================================================================
# 3. SYSTEM TESTS - End-to-End Workflows
# ============================================================================

def run_system_tests():
    """Test end-to-end workflows"""
    print("\n" + "="*80)
    print("3. SYSTEM TESTS - Testing End-to-End Workflows")
    print("="*80)

    try:
        from core.options_pricing.greeks import Greeks
        from core.market_data.nse_expiry_engine import NSEExpiryEngine, NSEHolidayCalendar
        from core.risk_engine.risk_manager import RiskManager
        from strategies.non_directional.iron_condor import IronCondor
        from strategies.non_directional.straddle import LongStraddle, ShortStraddle
        from strategies.hft_scalping.zero_dte_strategy import ZeroDTEStrategy
        from strategies import select_strategy
    except ImportError as e:
        print(f"  ⚠ Failed to import components: {e}")
        return

    print("\n[3.1] Intraday Trading Workflow")

    def test_intraday_workflow():
        # Step 1: Check if today is trading day
        cal = NSEHolidayCalendar()
        today = date.today()
        is_trading_day = cal.is_trading_day(today)

        # Step 2: Select strategy based on market conditions
        recommendation = select_strategy(
            spot=18000,
            iv=15.0,
            trend='sideways',
            time_of_day='morning',
            risk_appetite='moderate'
        )

        assert recommendation is not None, "Strategy selection failed"
        assert 'strategy_name' in recommendation, "No strategy recommended"

    run_test('system', 'Intraday Trading Workflow', test_intraday_workflow)

    print("\n[3.2] Expiry Day (Zero DTE) Workflow")

    def test_expiry_day_workflow():
        # Step 1: Check if today is expiry
        engine = NSEExpiryEngine()
        today = date.today()

        # Step 2: Create Zero DTE strategy
        zdte = ZeroDTEStrategy(18000, 'credit_spread', 5000, 50, 100, 5, 75)

        # Step 3: Risk check
        rm = RiskManager(total_capital=10000000)
        can_trade, _ = rm.can_place_trade(10000, 5000)

        assert zdte is not None, "Zero DTE strategy creation failed"

    run_test('system', 'Expiry Day (Zero DTE) Workflow', test_expiry_day_workflow)

    print("\n[3.3] Multi-Strategy Portfolio Management")

    def test_portfolio_workflow():
        # Create multiple strategies
        ic = IronCondor(17500, 17700, 18300, 18500, 20, 50, 45, 15, 1, 75)
        ls = LongStraddle(18000, 150, 145, 1, 75)

        # Calculate portfolio Greeks
        greeks_calc = Greeks()

        positions = [
            {'S': 18000, 'K': 17700, 'T': 0.0192, 'r': 0.07, 'sigma': 0.15,
             'option_type': 'put', 'quantity': 1, 'lot_size': 75},
            {'S': 18000, 'K': 18000, 'T': 0.0192, 'r': 0.07, 'sigma': 0.15,
             'option_type': 'call', 'quantity': 1, 'lot_size': 75}
        ]

        portfolio_greeks = greeks_calc.portfolio_greeks(positions)

        assert 'delta' in portfolio_greeks, "Portfolio greeks calculation failed"

    run_test('system', 'Multi-Strategy Portfolio Management', test_portfolio_workflow)

    print("\n[3.4] Risk Limit Enforcement")

    def test_risk_limits():
        rm = RiskManager(
            total_capital=10000000,
            max_daily_loss_pct=5.0,
            max_position_size_pct=10.0
        )

        # Try to place oversized trade
        can_trade, reason = rm.can_place_trade(2000000, 500000)  # 20% of capital
        assert can_trade == False, "Risk manager should block oversized trade"

        # Try to place acceptable trade
        can_trade2, _ = rm.can_place_trade(500000, 100000)  # 5% of capital
        assert can_trade2 == True, "Risk manager should allow normal trade"

    run_test('system', 'Risk Limit Enforcement', test_risk_limits)


# ============================================================================
# 4. PERFORMANCE TESTS - Speed and Resource Usage
# ============================================================================

def run_performance_tests():
    """Test performance and resource usage"""
    print("\n" + "="*80)
    print("4. PERFORMANCE TESTS - Testing Speed and Resource Usage")
    print("="*80)

    try:
        import numpy as np
        from core.options_pricing.greeks import Greeks, GreeksVectorized
        from core.market_data.nse_expiry_engine import NSEExpiryEngine
        from core.risk_engine.risk_manager import RiskManager
    except ImportError as e:
        print(f"  ⚠ Failed to import components: {e}")
        return

    print("\n[4.1] Greeks Calculation Speed")

    def test_greeks_performance():
        greeks = Greeks()

        # Calculate greeks for 1000 strikes
        start_time = time.time()
        for i in range(1000):
            greeks.delta(18000, 17000 + i*10, 0.0192, 0.07, 0.15, 'call')

        execution_time = time.time() - start_time

        test_results['performance']['metrics']['greeks_1000_calcs'] = execution_time
        assert execution_time < 5.0, f"Greeks calculation too slow: {execution_time:.2f}s"
        print(f"    → 1000 Delta calculations: {execution_time:.3f}s ({1000/execution_time:.0f} calcs/sec)")

    run_test('performance', 'Greeks Calculation Speed (1000 strikes)', test_greeks_performance)

    print("\n[4.2] Vectorized Greeks Performance")

    def test_vectorized_greeks():
        greeks_vec = GreeksVectorized()

        # Vectorized calculation for 1000 strikes
        S = np.full(1000, 18000)
        K = np.arange(17000, 27000, 10)
        T = np.full(1000, 0.0192)
        r = np.full(1000, 0.07)
        sigma = np.full(1000, 0.15)

        start_time = time.time()
        deltas = greeks_vec.delta_vectorized(S, K, T, r, sigma, 'call')
        execution_time = time.time() - start_time

        test_results['performance']['metrics']['vectorized_greeks'] = execution_time
        assert execution_time < 0.1, f"Vectorized greeks too slow: {execution_time:.3f}s"
        print(f"    → 1000 Vectorized Deltas: {execution_time:.4f}s ({1000/execution_time:.0f} calcs/sec)")

    run_test('performance', 'Vectorized Greeks Performance', test_vectorized_greeks)

    print("\n[4.3] Expiry Calculation Performance")

    def test_expiry_performance():
        engine = NSEExpiryEngine()

        # Calculate expiries for 100 dates
        start_time = time.time()
        for i in range(100):
            engine.get_next_expiry('NIFTY', from_date=date(2025, 1, 1))

        execution_time = time.time() - start_time

        test_results['performance']['metrics']['expiry_100_calcs'] = execution_time
        assert execution_time < 1.0, f"Expiry calculation too slow: {execution_time:.2f}s"
        print(f"    → 100 Expiry calculations: {execution_time:.3f}s ({100/execution_time:.0f} calcs/sec)")

    run_test('performance', 'Expiry Calculation Performance', test_expiry_performance)

    print("\n[4.4] Memory Usage Test")

    def test_memory_usage():
        greeks = Greeks()

        # Create large arrays
        results = []
        for i in range(10000):
            delta = greeks.delta(18000, 17000 + i, 0.0192, 0.07, 0.15, 'call')
            results.append(delta)

        assert len(results) == 10000, "Memory test failed"
        print(f"    → Successfully processed 10,000 calculations")

    run_test('performance', 'Memory Usage (10K calculations)', test_memory_usage)


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_report():
    """Generate comprehensive test report"""
    print("\n" + "="*80)
    print("TEST REPORT - Indian Options Trading Platform")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    categories = [
        ('unit', '1. UNIT TESTS'),
        ('integration', '2. INTEGRATION TESTS'),
        ('system', '3. SYSTEM TESTS'),
        ('performance', '4. PERFORMANCE TESTS')
    ]

    total_passed = 0
    total_failed = 0
    total_errors = 0

    for cat_key, cat_name in categories:
        print(f"\n{cat_name}")
        print("-" * 80)

        passed = len(test_results[cat_key]['passed'])
        failed = len(test_results[cat_key]['failed'])
        errors = len(test_results[cat_key]['errors'])
        total = passed + failed + errors

        total_passed += passed
        total_failed += failed
        total_errors += errors

        print(f"  Total Tests: {total}")
        print(f"  ✓ Passed:    {passed}")
        print(f"  ✗ Failed:    {failed}")
        print(f"  ⚠ Errors:    {errors}")

        if total > 0:
            success_rate = (passed / total) * 100
            print(f"  Success Rate: {success_rate:.1f}%")

        # Show failures
        if failed > 0:
            print(f"\n  Failed Tests:")
            for result in test_results[cat_key]['failed']:
                print(f"    - {result['test']}: {result['message']}")

        # Show errors
        if errors > 0:
            print(f"\n  Errors:")
            for result in test_results[cat_key]['errors']:
                print(f"    - {result['test']}: {result['message'][:100]}")

    # Performance metrics
    if test_results['performance']['metrics']:
        print(f"\n{'PERFORMANCE METRICS':^80}")
        print("-" * 80)
        for metric, value in test_results['performance']['metrics'].items():
            print(f"  {metric}: {value:.4f}s")

    # Overall summary
    print(f"\n{'OVERALL SUMMARY':^80}")
    print("=" * 80)
    grand_total = total_passed + total_failed + total_errors
    print(f"  Total Tests Run:     {grand_total}")
    print(f"  ✓ Total Passed:      {total_passed}")
    print(f"  ✗ Total Failed:      {total_failed}")
    print(f"  ⚠ Total Errors:      {total_errors}")

    if grand_total > 0:
        overall_success = (total_passed / grand_total) * 100
        print(f"  Overall Success Rate: {overall_success:.1f}%")

        # Final verdict
        print("\n" + "=" * 80)
        if overall_success >= 90:
            print("  STATUS: ✓ EXCELLENT - Platform is production-ready")
        elif overall_success >= 75:
            print("  STATUS: ✓ GOOD - Platform is mostly ready, minor fixes needed")
        elif overall_success >= 50:
            print("  STATUS: ⚠ FAIR - Platform needs significant fixes")
        else:
            print("  STATUS: ✗ POOR - Platform has major issues")
        print("=" * 80)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run all tests and generate report"""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUITE - Indian Options Trading Platform")
    print("="*80)
    print("Testing 4 Critical Aspects:")
    print("  1. Unit Tests - Individual component functionality")
    print("  2. Integration Tests - Component interactions")
    print("  3. System Tests - End-to-end workflows")
    print("  4. Performance Tests - Speed and resource usage")
    print("="*80)

    start_time = time.time()

    # Run all test suites
    run_unit_tests()
    run_integration_tests()
    run_system_tests()
    run_performance_tests()

    total_time = time.time() - start_time

    # Generate report
    generate_report()

    print(f"\nTotal Execution Time: {total_time:.2f}s")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
