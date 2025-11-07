# 📊 Unified Intraday Options Strategy Guide

> **Complete guide for intraday options trading with Indian markets**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Strategy Library Structure](#strategy-library-structure)
3. [Intraday Strategies Deep Dive](#intraday-strategies-deep-dive)
4. [Strategy Selection](#strategy-selection)
5. [Quick Reference](#quick-reference)
6. [Usage Examples](#usage-examples)
7. [Risk Management](#risk-management)

---

## 🎯 Overview

This unified strategy library consolidates **ALL options trading strategies** with a primary focus on **INTRADAY execution** for Indian markets (NSE).

### What's New (v2.0.0):

✅ **Unified Interface**: Single import point for all strategies
✅ **Intraday-Focused**: All strategies optimized for intraday trading
✅ **Smart Selection**: Auto-recommend best strategy based on market conditions
✅ **Angel One Integration**: Direct live trading capability
✅ **No Redundancy**: Removed duplicate/overlapping strategies

### Strategies Included:

| Strategy | Type | Intraday Use | Risk Level |
|----------|------|--------------|------------|
| **GammaScalpingStrategy** | HFT/Scalping | ⭐⭐⭐⭐⭐ PRIMARY | MODERATE |
| **ZeroDTEStrategy** | HFT/Scalping | ⭐⭐⭐⭐⭐ PRIMARY | HIGH |
| **IronCondor** | Range-Bound | ⭐⭐⭐ GOOD | LOW-MODERATE |
| **LongStraddle** | Volatility | ⭐⭐⭐⭐ VERY GOOD | MODERATE |
| **ShortStraddle** | Volatility | ⭐⭐ RISKY | VERY HIGH |

---

## 📚 Strategy Library Structure

```
strategies/
├── __init__.py                    # Unified entry point (v2.0.0)
├── base_strategy.py               # Core base class
│
├── non_directional/               # Range-bound strategies
│   ├── __init__.py
│   ├── iron_condor.py            # 4-leg neutral strategy
│   └── straddle.py               # Long/Short straddle
│
└── hft_scalping/                  # Pure intraday strategies
    ├── __init__.py
    ├── gamma_scalping.py         # Delta-neutral intraday
    └── zero_dte_strategy.py      # Expiry day trading
```

### Import Pattern:

```python
# Method 1: Import from main module
from strategies import GammaScalpingStrategy, ZeroDTEStrategy, IronCondor

# Method 2: Import specific categories
from strategies.hft_scalping import GammaScalpingStrategy
from strategies.non_directional import IronCondor

# Method 3: Use smart selector
from strategies import select_strategy
```

---

## 🔥 Intraday Strategies Deep Dive

### 1. Gamma Scalping Strategy ⭐⭐⭐⭐⭐

**Best for:** High volatility, trending markets

**Concept:**
- Buy ATM straddle (long gamma position)
- When spot moves → delta changes → hedge with futures
- Capture profits from hedge adjustments
- Repeat throughout the day

**Time Frame:** Full day (9:30 AM - 3:15 PM)
**Capital Required:** ₹15,000 - ₹30,000
**Expected Return:** 1-3% per day
**Risk Level:** MODERATE (limited to straddle cost)

**When to Use:**
- ✅ High volatility days (VIX > 15, IV > 15%)
- ✅ Trending markets (up or down)
- ✅ Frequent price oscillations
- ✅ Comfortable with frequent adjustments

**Setup:**
```python
from strategies import GammaScalpingStrategy

strategy = GammaScalpingStrategy(
    spot_price=19500,
    atm_strike=19500,
    atm_call_price=150,
    atm_put_price=140,
    delta_threshold=0.15,      # Hedge when |delta| > 0.15
    profit_target_pct=0.5,     # Take profit at 0.5%
    max_adjustments=10         # Max 10 hedges per day
)

# Initialize position
strategy.enter_position()

# Throughout the day
while trading:
    # Update Greeks
    strategy.update_greeks(current_spot, call_delta, put_delta, call_gamma, put_gamma)

    # Check if adjustment needed
    action = strategy.check_adjustment(current_spot)

    if action:
        # Execute hedge via Angel One API
        execute_hedge(action)
```

**Key Metrics:**
- **Delta Threshold:** Trigger for hedging (typically 0.10-0.20)
- **Profit Target:** Take profit on hedges (typically 0.5-1%)
- **Max Adjustments:** Limit total hedges (typically 8-12 per day)

---

### 2. Zero DTE Strategy ⭐⭐⭐⭐⭐

**Best for:** Expiry day trading (Thursday)

**Concept:**
- Trade options on expiry day only
- Maximum theta decay on last day
- Quick scalps based on spot movement
- Exit by 3:20 PM to avoid assignment

**Time Frame:** Expiry day only (9:30 AM - 3:20 PM)
**Capital Required:** ₹5,000 - ₹10,000 per trade
**Expected Return:** 20-50% per trade (or -100% loss)
**Risk Level:** HIGH (can lose 100% quickly)

**Sub-Strategies:**

#### a) Credit Spread (Bull Put / Bear Call)
- Sell OTM option, buy further OTM for protection
- Best when expecting range-bound
- Limited risk, limited reward

#### b) ATM Scalp
- Buy ATM straddle when IV low
- Sell when spot moves or IV increases
- Quick in/out (10-30 minutes)

#### c) Iron Condor (Expiry Day)
- Sell OTM call + put, buy further OTM
- Best if expecting no movement
- Exit at 50% profit or if breached

**Setup:**
```python
from strategies import ZeroDTEStrategy

strategy = ZeroDTEStrategy(
    spot_price=19500,
    strategy_type='credit_spread',  # or 'atm_scalp', 'iron_condor'
    risk_per_trade=5000,
    profit_target_pct=50,           # 50% of max profit
    stop_loss_pct=100,              # 100% of risk
    max_trades=5                    # Max 5 trades on expiry day
)

# Check entry
should_enter = strategy.should_enter(
    spot=19500,
    iv=0.18,
    trend='sideways'
)

if should_enter:
    # Enter position
    entry = strategy.enter_credit_spread(spot=19500, direction='put')

    # Place orders via Angel One
    api.place_order(...)

# Monitor exit
exit_reason = strategy.check_exit(current_prices)
if exit_reason:
    strategy.exit_position(exit_reason, exit_prices)
```

**⚠️ WARNING:**
- Extremely high risk on expiry day
- Can lose 100% in minutes
- Always use stop loss
- Exit by 3:20 PM mandatory

---

### 3. Iron Condor ⭐⭐⭐

**Best for:** Range-bound, low volatility markets

**Concept:**
- Sell OTM put + call (collect premium)
- Buy further OTM put + call (protection)
- Profit if spot stays within range

**Time Frame:** Can hold to expiry OR exit intraday
**Capital Required:** ₹20,000 - ₹40,000
**Expected Return:** 2-5% per day (if hit intraday target)
**Risk Level:** LOW-MODERATE (limited risk)

**Intraday Usage:**
- Enter in morning (9:30-10:30 AM)
- Target 50-75% of max profit
- Exit if spot breaches short strike
- Can hold to expiry if conditions remain favorable

**Setup:**
```python
from strategies import IronCondor

# Manual construction
ic = IronCondor(
    lower_long_put_strike=19300,
    lower_short_put_strike=19400,
    upper_short_call_strike=19600,
    upper_long_call_strike=19700,
    lower_long_put_premium=30,
    lower_short_put_premium=60,
    upper_short_call_premium=55,
    upper_long_call_premium=25,
    quantity=1,
    lot_size=50
)

# Auto-balanced construction
ic = IronCondor.create_balanced(
    spot=19500,
    put_width=100,
    call_width=100,
    distance_from_spot=150
)

# Get metrics
metrics = ic.risk_metrics()
print(f"Max Profit: ₹{metrics['max_profit']:,.2f}")
print(f"Profit Zone: {metrics['profit_zone']}")
```

**Intraday Optimization:**
- Exit at 50% of max profit (don't be greedy)
- If one side breaches, consider exiting or adjusting
- Best in morning, exit by 2:30 PM if target hit

---

### 4. Long Straddle ⭐⭐⭐⭐

**Best for:** Expecting big move, low IV

**Concept:**
- Buy ATM call + ATM put
- Profit from large move in either direction
- Best before major events

**Time Frame:** 10-60 minutes (quick scalps)
**Capital Required:** ₹15,000 - ₹25,000
**Expected Return:** 5-15% per trade
**Risk Level:** MODERATE (limited to premium paid)

**Intraday Usage:**
- Enter when IV is low (< 15%)
- Before expected volatility (news, RBI policy, etc.)
- Exit IMMEDIATELY when profit target hit
- Don't hold if no move within 1 hour

**Setup:**
```python
from strategies import LongStraddle

straddle = LongStraddle(
    strike=19500,           # ATM strike
    call_premium=150,
    put_premium=140,
    quantity=1,
    lot_size=50
)

# Check if IV is favorable
iv_analysis = straddle.iv_analysis(
    current_iv=0.12,        # 12% current
    historical_iv_avg=0.15  # 15% average
)

if iv_analysis['favorable']:
    # Enter position
    # Set profit target: 10-15%
    # Set stop loss: 50% of premium
    pass
```

**Quick Exit Rules:**
- ✅ Exit at 10-15% profit
- ✅ Exit if no move within 1 hour
- ✅ Exit after event (before IV crush)
- ❌ Never hold overnight for intraday

---

### 5. Short Straddle ⭐⭐ (RISKY)

**Best for:** Range-bound, high IV (aggressive traders only)

**Concept:**
- Sell ATM call + ATM put
- Profit from theta decay
- **UNLIMITED RISK**

**Time Frame:** Full day (close monitoring)
**Capital Required:** ₹20,000 - ₹35,000
**Expected Return:** 3-8% per day
**Risk Level:** VERY HIGH (unlimited loss)

**⚠️ USE WITH EXTREME CAUTION:**
- Only for aggressive traders
- Mandatory stop loss at 2x premium
- Exit immediately if spot moves against you
- Consider Iron Condor instead for defined risk

---

## 🎯 Strategy Selection

### Automatic Selection

Use the `select_strategy()` function to auto-recommend:

```python
from strategies import select_strategy

# Get recommendation
rec = select_strategy(
    spot=19500,
    iv=0.18,                    # 18% implied volatility
    trend='sideways',           # 'up', 'down', 'sideways', 'volatile'
    time_of_day='10:00',        # HH:MM format
    risk_appetite='moderate'    # 'conservative', 'moderate', 'aggressive'
)

print(f"Strategy: {rec['strategy_name']}")
print(f"Reason: {rec['reason']}")
print(f"Setup: {rec['setup']}")
print(f"Capital: {rec['capital_required']}")
print(f"Expected: {rec['expected_return']}")
```

### Selection Flowchart

```
START
  │
  ├─ Is it Thursday (Expiry Day)?
  │  └─ YES → ZeroDTEStrategy ✓
  │
  └─ NO → Check Market Conditions:
      │
      ├─ High Volatility (IV > 15%) + Trending?
      │  └─ YES → GammaScalpingStrategy ✓
      │
      ├─ Range-Bound + Low/Normal Vol (IV < 20%)?
      │  └─ YES → IronCondor ✓
      │
      ├─ Expecting Big Move + Low IV (< 15%)?
      │  └─ YES → LongStraddle ✓
      │
      └─ High IV (> 18%) + Range-Bound + Aggressive?
         └─ YES → ShortStraddle ⚠️ (Use strict SL)
```

---

## 📖 Quick Reference

### Strategy Comparison Table

| Strategy | Market | Capital | Risk | Time | Expected Return |
|----------|--------|---------|------|------|-----------------|
| **Gamma Scalping** | High Vol, Trending | ₹15K-30K | MODERATE | Full Day | 1-3%/day |
| **Zero DTE** | Expiry Day | ₹5K-10K | HIGH | 9:30-3:20 | 20-50%/trade |
| **Iron Condor** | Range-Bound | ₹20K-40K | LOW-MOD | Full Day | 2-5%/day |
| **Long Straddle** | Before Event | ₹15K-25K | MODERATE | 10-60 min | 5-15%/trade |
| **Short Straddle** | High IV Range | ₹20K-35K | VERY HIGH | Full Day | 3-8%/day |

### When to Use Each Strategy

**Market Conditions:**

| Condition | Best Strategy |
|-----------|---------------|
| Expiry Day (Thursday) | Zero DTE |
| High Volatility + Trending | Gamma Scalping |
| Range-Bound + Low Vol | Iron Condor |
| Before Major Event + Low IV | Long Straddle |
| High IV + Range-Bound | Short Straddle (⚠️) |
| Sideways Market | Iron Condor OR Zero DTE (expiry) |
| Volatile but No Trend | Gamma Scalping |

**Time of Day:**

| Time | Recommended Strategy |
|------|----------------------|
| 9:30-10:30 AM | Enter Iron Condor OR Gamma Scalping |
| 10:30-2:00 PM | Gamma Scalping OR Long Straddle (quick) |
| 2:00-3:00 PM | Zero DTE (if expiry) OR Close positions |
| After 3:00 PM | CLOSE ALL POSITIONS |

---

## 💻 Usage Examples

### Example 1: Using Smart Selector

```python
from strategies import select_strategy, print_strategy_guide

# Print comparison table
print_strategy_guide()

# Get recommendation
rec = select_strategy(
    spot=19500,
    iv=0.20,
    trend='volatile',
    time_of_day='10:30',
    risk_appetite='moderate'
)

# Create strategy instance
StrategyClass = rec['class']
strategy = StrategyClass(**rec['setup'])
```

### Example 2: Manual Strategy Selection

```python
from strategies import GammaScalpingStrategy, ZeroDTEStrategy, IronCondor
from core.market_data.angel_one_api import AngelOneAPI

# Initialize API
api = AngelOneAPI(API_KEY, USERNAME, PASSWORD, TOTP_TOKEN)
api.login()

# Get current market data
spot = api.get_ltp('NSE', 'NIFTY 50', 'NSE:NIFTY 50')
options_chain = api.get_options_chain('NIFTY')

# Select strategy based on day
from datetime import datetime

if datetime.now().weekday() == 3:  # Thursday
    # Expiry day - use Zero DTE
    strategy = ZeroDTEStrategy(
        spot_price=spot,
        strategy_type='credit_spread',
        risk_per_trade=5000
    )

else:
    # Regular day - use Gamma Scalping
    atm_strike = round(spot / 50) * 50

    strategy = GammaScalpingStrategy(
        spot_price=spot,
        atm_strike=atm_strike,
        atm_call_price=150,  # Fetch from options_chain
        atm_put_price=140,
        delta_threshold=0.15,
        profit_target_pct=0.5
    )
```

### Example 3: Live Trading with Engine

```python
from core.order_management.live_trading_engine import LiveTradingEngine
from strategies import GammaScalpingStrategy

# Setup strategy
strategy = GammaScalpingStrategy(
    spot_price=19500,
    atm_strike=19500,
    atm_call_price=150,
    atm_put_price=140
)

# Setup engine
engine = LiveTradingEngine(
    angel_api=api,
    risk_per_trade=10000,
    max_daily_loss=50000,
    max_daily_profit=100000
)

# Add and activate strategy
engine.add_strategy('gamma_scalp', strategy)
engine.set_active_strategy('gamma_scalp')

# Start automated trading
engine.start()

# Monitor
import time
while True:
    summary = engine.get_summary()
    print(f"P&L: ₹{summary['daily_pnl']:,.2f}")
    time.sleep(60)

    if summary['daily_pnl'] >= 50000:  # Hit profit target
        engine.stop()
        break
```

---

## ⚠️ Risk Management

### Position Sizing

```python
account_size = 500000  # ₹5 lakh
risk_per_trade = account_size * 0.02  # 2% = ₹10,000

# Don't risk more than 2% per trade
# Max 3-5 simultaneous positions
```

### Stop Losses

**Strategy-Specific Stop Loss:**

| Strategy | Stop Loss |
|----------|-----------|
| Gamma Scalping | Entry cost (straddle premium) |
| Zero DTE | 100% of risk (max loss) |
| Iron Condor | 1.5x credit received |
| Long Straddle | 50% of premium paid |
| Short Straddle | 2x premium received |

### Daily Limits

```python
# Set daily limits
MAX_DAILY_LOSS = account_size * 0.05      # 5% = ₹25,000
MAX_DAILY_PROFIT = account_size * 0.10    # 10% = ₹50,000

# Stop trading when hit
if daily_pnl <= -MAX_DAILY_LOSS:
    STOP_TRADING()

if daily_pnl >= MAX_DAILY_PROFIT:
    STOP_TRADING()  # Take profits!
```

### Time-Based Rules

**⏰ Trading Hours:**
- ✅ Trade: 9:30 AM - 3:00 PM
- ❌ Don't Trade: 9:15-9:30 AM (market opening)
- ❌ Don't Trade: 3:00-3:30 PM (closing)
- 🚨 Exit ALL: By 3:15 PM mandatory

**📅 Don't Trade On:**
- Budget day (without preparation)
- RBI policy announcement (unless trading straddle)
- Major global events (Fed meeting, war, etc.)
- Holidays eve (low liquidity)

---

## 🎓 Best Practices

### 1. Always Paper Trade First
- Test strategies for 1-2 weeks
- Verify execution logic
- Check risk management

### 2. Start Small
- Begin with 1 lot
- Increase after consistent profits
- Never risk more than 2% per trade

### 3. Keep Trading Journal
- Log all trades
- Note market conditions
- Review weekly

### 4. Respect Risk Limits
- Set daily loss limits
- Stop when limit hit
- No revenge trading

### 5. Continuous Learning
- Analyze losing trades
- Study market behavior
- Adapt strategies

---

## 📞 Support & Resources

**Documentation:**
- [Angel One Setup Guide](ANGEL_ONE_SETUP.md)
- [ML Models Guide](docs/ML_MODELS_GUIDE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

**Live Trading:**
- Angel One API Integration: ✅ Complete
- WebSocket Streaming: ✅ Available
- Paper Trading: ✅ Available
- Backtesting: ✅ Available

**Contact:**
- GitHub Issues: For bugs and feature requests
- Angel One Support: 1800 123 4567

---

## ⚠️ DISCLAIMER

**This software is for educational purposes only.**

- ❌ NOT financial advice
- ❌ NO guarantees of profit
- ❌ Can lose 100% of capital
- ✅ Trade at your own risk
- ✅ Test thoroughly before live trading
- ✅ Consult a financial advisor

**Options trading is extremely risky. Only trade with money you can afford to lose.**

---

**Happy Trading! 🚀**

*Built with ❤️ for Indian retail traders*

**Version:** 2.0.0 (Unified Intraday-Focused Library)
**Last Updated:** 2025-11-07
