#!/usr/bin/env python3
"""
Unit Tests - Test Individual Components
Tests: Pricing, Greeks, Strategies, Risk Manager, Expiry Engine
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd

# Import components to test
from core.options_pricing.black_scholes import BlackScholes
from core.options_pricing.greeks import Greeks
try:
    from core.options_pricing.implied_volatility import ImpliedVolatilityCalculator
except ImportError:
    ImpliedVolatilityCalculator = None
from core.market_data.nse_expiry_engine import NSEExpiryEngine, NSEHolidayCalendar
from core.risk_engine.risk_manager import RiskManager
from strategies.base_strategy import OptionType, PositionType, Position
from strategies.non_directional.iron_condor import IronCondor
from strategies.non_directional.straddle import LongStraddle, ShortStraddle
from strategies.hft_scalping.gamma_scalping import GammaScalpingStrategy
from strategies.hft_scalping.zero_dte_strategy import ZeroDTEStrategy


class TestBlackScholesPricing(unittest.TestCase):
    """Test Black-Scholes pricing engine"""

    def setUp(self):
        self.bs = BlackScholes()

    def test_call_option_pricing(self):
        """Test call option pricing"""
        price = self.bs.price(
            S=18000,      # Nifty spot
            K=18000,      # ATM strike
            T=0.0192,     # 1 week (7/365)
            r=0.07,       # 7% risk-free rate
            sigma=0.15,   # 15% IV
            option_type='call'
        )
        self.assertGreater(price, 0, "Call price should be positive")
        self.assertLess(price, 18000, "Call price should be less than spot")
        print(f"✓ ATM Call (18000): ₹{price:.2f}")

    def test_put_option_pricing(self):
        """Test put option pricing"""
        price = self.bs.price(
            S=18000,
            K=18000,
            T=0.0192,
            r=0.07,
            sigma=0.15,
            option_type='put'
        )
        self.assertGreater(price, 0, "Put price should be positive")
        print(f"✓ ATM Put (18000): ₹{price:.2f}")

    def test_put_call_parity(self):
        """Test put-call parity"""
        S, K, T, r, sigma = 18000, 18000, 0.0192, 0.07, 0.15
        call = self.bs.price(S, K, T, r, sigma, 'call')
        put = self.bs.price(S, K, T, r, sigma, 'put')

        # C - P = S - K*e^(-rT)
        lhs = call - put
        rhs = S - K * np.exp(-r * T)

        self.assertAlmostEqual(lhs, rhs, places=2, msg="Put-call parity violated")
        print(f"✓ Put-Call Parity: {lhs:.2f} ≈ {rhs:.2f}")


class TestGreeksCalculation(unittest.TestCase):
    """Test Greeks calculator"""

    def setUp(self):
        self.greeks_calc = Greeks()

    def test_delta_call(self):
        """Test call delta (should be between 0 and 1)"""
        delta = self.greeks_calc.delta(
            S=18000, K=18000, T=0.0192, r=0.07, sigma=0.15, option_type='call'
        )
        self.assertGreater(delta, 0, "Call delta should be positive")
        self.assertLess(delta, 1, "Call delta should be less than 1")
        print(f"✓ ATM Call Delta: {delta:.4f}")

    def test_delta_put(self):
        """Test put delta (should be between -1 and 0)"""
        delta = self.greeks_calc.delta(
            S=18000, K=18000, T=0.0192, r=0.07, sigma=0.15, option_type='put'
        )
        self.assertLess(delta, 0, "Put delta should be negative")
        self.assertGreater(delta, -1, "Put delta should be greater than -1")
        print(f"✓ ATM Put Delta: {delta:.4f}")

    def test_gamma_positive(self):
        """Test gamma (always positive)"""
        gamma = self.greeks_calc.gamma(
            S=18000, K=18000, T=0.0192, r=0.07, sigma=0.15
        )
        self.assertGreater(gamma, 0, "Gamma should always be positive")
        print(f"✓ Gamma: {gamma:.6f}")

    def test_vega_positive(self):
        """Test vega (always positive)"""
        vega = self.greeks_calc.vega(
            S=18000, K=18000, T=0.0192, r=0.07, sigma=0.15
        )
        self.assertGreater(vega, 0, "Vega should always be positive")
        print(f"✓ Vega: {vega:.2f}")

    def test_theta_call(self):
        """Test call theta (usually negative)"""
        theta = self.greeks_calc.theta(
            S=18000, K=18000, T=0.0192, r=0.07, sigma=0.15, option_type='call'
        )
        self.assertLess(theta, 0, "ATM call theta should be negative (time decay)")
        print(f"✓ Call Theta: {theta:.2f}")


class TestNSEExpiryEngine(unittest.TestCase):
    """Test NSE expiry calculation engine"""

    def setUp(self):
        self.expiry_engine = NSEExpiryEngine()
        self.holiday_cal = NSEHolidayCalendar()

    def test_nifty_expiry_thursday(self):
        """Test Nifty expiry is Thursday"""
        expiry = self.expiry_engine.get_next_expiry('NIFTY', from_date=date(2025, 1, 6))
        self.assertEqual(expiry.weekday(), 3, "Nifty expiry should be Thursday (3)")
        print(f"✓ Nifty expiry: {expiry} ({expiry.strftime('%A')})")

    def test_banknifty_expiry_wednesday(self):
        """Test Bank Nifty expiry is Wednesday"""
        expiry = self.expiry_engine.get_next_expiry('BANKNIFTY', from_date=date(2025, 1, 6))
        self.assertEqual(expiry.weekday(), 2, "Bank Nifty expiry should be Wednesday (2)")
        print(f"✓ Bank Nifty expiry: {expiry} ({expiry.strftime('%A')})")

    def test_expiry_not_holiday(self):
        """Test expiry is not a holiday"""
        expiry = self.expiry_engine.get_next_expiry('NIFTY')
        is_trading_day = self.holiday_cal.is_trading_day(expiry)
        self.assertTrue(is_trading_day, "Expiry should be a trading day")
        print(f"✓ Expiry {expiry} is trading day: {is_trading_day}")

    def test_time_to_expiry(self):
        """Test time to expiry calculation"""
        tte = self.expiry_engine.time_to_expiry('NIFTY', from_date=date(2025, 1, 6))
        self.assertGreater(tte, 0, "Time to expiry should be positive")
        self.assertLess(tte, 1, "Weekly expiry should be less than 1 year")
        print(f"✓ Time to expiry: {tte:.4f} years ({tte*365:.1f} days)")

    def test_is_expiry_day(self):
        """Test expiry day detection"""
        # Get next expiry
        expiry = self.expiry_engine.get_next_expiry('NIFTY', from_date=date(2025, 1, 6))
        is_expiry = self.expiry_engine.is_expiry_day(expiry, 'NIFTY')
        self.assertTrue(is_expiry, f"{expiry} should be expiry day")
        print(f"✓ {expiry} is Nifty expiry: {is_expiry}")

    def test_holiday_calendar_2025(self):
        """Test holiday calendar"""
        # Republic Day 2025
        is_holiday = not self.holiday_cal.is_trading_day(date(2025, 1, 26))
        self.assertTrue(is_holiday, "Jan 26, 2025 should be a holiday")
        print(f"✓ Jan 26, 2025 (Republic Day) is holiday: {is_holiday}")


class TestRiskManager(unittest.TestCase):
    """Test Risk Management System"""

    def setUp(self):
        self.risk_mgr = RiskManager(
            total_capital=10000000,  # 1 crore
            max_daily_loss_pct=5.0,
            max_daily_profit_pct=10.0,
            max_position_size_pct=10.0
        )

    def test_kelly_criterion(self):
        """Test Kelly Criterion position sizing"""
        # Win rate 60%, Win/Loss ratio 2:1
        position_size = self.risk_mgr.calculate_position_size_kelly(
            win_rate=0.60,
            win_loss_ratio=2.0
        )
        self.assertGreater(position_size, 0, "Position size should be positive")
        self.assertLess(position_size, 10000000, "Position size should not exceed capital")
        print(f"✓ Kelly position size: ₹{position_size:,.0f}")

    def test_fixed_fractional(self):
        """Test Fixed Fractional position sizing"""
        position_size = self.risk_mgr.calculate_position_size_fixed_fractional(
            risk_per_trade_pct=2.0
        )
        expected = 10000000 * 0.02
        self.assertEqual(position_size, expected, "Fixed fractional calculation error")
        print(f"✓ Fixed fractional (2%): ₹{position_size:,.0f}")

    def test_daily_loss_limit(self):
        """Test daily loss limit"""
        # Simulate loss
        self.risk_mgr.update_pnl(-600000)  # -6 lakh loss

        can_trade, reason = self.risk_mgr.can_place_trade(100000, 50000)
        self.assertFalse(can_trade, "Should block trade after exceeding daily loss limit")
        self.assertIn("daily loss limit", reason.lower())
        print(f"✓ Daily loss limit triggered: {reason}")

    def test_position_size_limit(self):
        """Test position size limit"""
        # Try to place trade > 10% of capital
        can_trade, reason = self.risk_mgr.can_place_trade(
            capital_required=1500000,  # 15 lakh (15% of 1 cr)
            strategy_risk=500000
        )
        self.assertFalse(can_trade, "Should block oversized position")
        self.assertIn("position size", reason.lower())
        print(f"✓ Position size limit triggered: {reason}")

    def test_var_calculation(self):
        """Test VaR calculation"""
        # Add some PnL history
        for pnl in [10000, -5000, 15000, -8000, 20000, -3000, 12000]:
            self.risk_mgr.update_pnl(pnl)

        var = self.risk_mgr.calculate_var(confidence=0.95)
        self.assertLess(var, 0, "VaR should be negative (potential loss)")
        print(f"✓ VaR (95%): ₹{var:,.0f}")


class TestStrategies(unittest.TestCase):
    """Test Options Strategies"""

    def test_iron_condor_structure(self):
        """Test Iron Condor strategy structure"""
        ic = IronCondor(
            lower_long_put_strike=17500,
            lower_short_put_strike=17700,
            upper_short_call_strike=18300,
            upper_long_call_strike=18500,
            lower_long_put_premium=20,
            lower_short_put_premium=50,
            upper_short_call_premium=45,
            upper_long_call_premium=15,
            quantity=1,
            lot_size=75
        )

        # Check 4 legs
        self.assertEqual(len(ic.positions), 4, "Iron Condor should have 4 legs")

        # Check max profit
        max_profit = ic.max_profit()
        expected_credit = (50 + 45 - 20 - 15) * 75
        self.assertEqual(max_profit, expected_credit, "Max profit should be net credit")
        print(f"✓ Iron Condor max profit: ₹{max_profit:,.0f}")

        # Check max loss
        max_loss = ic.max_loss()
        self.assertLess(max_loss, 0, "Max loss should be negative")
        print(f"✓ Iron Condor max loss: ₹{max_loss:,.0f}")

    def test_long_straddle(self):
        """Test Long Straddle strategy"""
        straddle = LongStraddle(
            strike=18000,
            call_premium=150,
            put_premium=145,
            quantity=1,
            lot_size=75
        )

        # Check 2 legs
        self.assertEqual(len(straddle.positions), 2, "Straddle should have 2 legs")

        # Check max profit (unlimited)
        max_profit = straddle.max_profit()
        self.assertIsNone(max_profit, "Long straddle has unlimited profit")

        # Check max loss
        max_loss = straddle.max_loss()
        expected_debit = -(150 + 145) * 75
        self.assertEqual(max_loss, expected_debit, "Max loss should be total premium paid")
        print(f"✓ Long Straddle max loss: ₹{max_loss:,.0f}")

    def test_short_straddle(self):
        """Test Short Straddle strategy"""
        straddle = ShortStraddle(
            strike=18000,
            call_premium=150,
            put_premium=145,
            quantity=1,
            lot_size=75
        )

        # Check max profit
        max_profit = straddle.max_profit()
        expected_credit = (150 + 145) * 75
        self.assertEqual(max_profit, expected_credit, "Max profit should be total premium collected")
        print(f"✓ Short Straddle max profit: ₹{max_profit:,.0f}")

        # Check max loss (unlimited)
        max_loss = straddle.max_loss()
        self.assertIsNone(max_loss, "Short straddle has unlimited loss")

    def test_gamma_scalping_strategy(self):
        """Test Gamma Scalping strategy"""
        gs = GammaScalpingStrategy(
            spot_price=18000,
            atm_strike=18000,
            atm_call_price=150,
            atm_put_price=145,
            call_delta=0.5,
            put_delta=-0.5,
            call_gamma=0.01,
            put_gamma=0.01,
            lot_size=75,
            delta_threshold=0.15
        )

        self.assertEqual(gs.lot_size, 75, "Lot size should be 75")
        self.assertEqual(gs.atm_strike, 18000, "ATM strike should be 18000")
        print(f"✓ Gamma Scalping initialized: Spot={gs.spot_price}, Strike={gs.atm_strike}")

    def test_zero_dte_strategy(self):
        """Test Zero DTE strategy"""
        zdte = ZeroDTEStrategy(
            spot_price=18000,
            strategy_type='credit_spread',
            risk_per_trade=5000,
            profit_target_pct=50,
            stop_loss_pct=100,
            max_trades=5,
            lot_size=75
        )

        self.assertEqual(zdte.lot_size, 75, "Lot size should be 75")
        self.assertEqual(zdte.risk_per_trade, 5000, "Risk per trade should be 5000")
        print(f"✓ Zero DTE initialized: Risk=₹{zdte.risk_per_trade:,}, Target={zdte.profit_target_pct}%")


def run_unit_tests():
    """Run all unit tests"""
    print("\n" + "="*80)
    print("UNIT TESTS - Testing Individual Components")
    print("="*80 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestBlackScholesPricing))
    suite.addTests(loader.loadTestsFromTestCase(TestGreeksCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestNSEExpiryEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestRiskManager))
    suite.addTests(loader.loadTestsFromTestCase(TestStrategies))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print("UNIT TEST SUMMARY")
    print("="*80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print("="*80 + "\n")

    return result


if __name__ == '__main__':
    result = run_unit_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
