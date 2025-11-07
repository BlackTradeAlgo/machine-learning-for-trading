# 🔥 Angel One API Integration Guide

> **Complete guide for live intraday options trading with Angel One SmartAPI**

---

## 📋 **Table of Contents**

1. [Angel One Account Setup](#angel-one-account-setup)
2. [API Credentials](#api-credentials)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Intraday Strategies](#intraday-strategies)
6. [Live Trading Engine](#live-trading-engine)
7. [Risk Management](#risk-management)
8. [Common Issues](#common-issues)

---

## 🏦 **Angel One Account Setup**

###Step 1: Open Angel One Account**

1. Visit: https://www.angelone.in/
2. Complete KYC process
3. Fund your account

### **Step 2: Get API Access**

1. Login to Angel One web platform
2. Go to: **My Profile** → **My API**
3. Click "**Create API**"
4. Note down:
   - API Key
   - Client Code (Username)
   - Password (Your trading password)

### **Step 3: Enable TOTP (2FA)**

1. Install **Google Authenticator** app
2. In Angel One: **My Profile** → **Security** → **2FA**
3. Scan QR code
4. **IMPORTANT**: Save the **TOTP secret key** (shown as text)
   - Example: `JBSWY3DPEHPK3PXP`

---

## 🔑 **API Credentials**

Create a file: `config/angel_one_credentials.py`

```python
# Angel One API Credentials
API_KEY = "your_api_key_here"
USERNAME = "your_client_code"  # e.g., "A12345"
PASSWORD = "your_password"
TOTP_TOKEN = "your_totp_secret_key"  # NOT the 6-digit code!

# Example (DUMMY DATA - replace with yours):
# API_KEY = "aBcD1234"
# USERNAME = "A123456"
# PASSWORD = "MyPass@123"
# TOTP_TOKEN = "JBSWY3DPEHPK3PXP"
```

⚠️ **Security:**
- Never commit credentials to git
- Add `config/angel_one_credentials.py` to `.gitignore`
- Use environment variables in production

---

## 📦 **Installation**

### **1. Install Dependencies**

```bash
pip install smartapi-python pyotp pandas numpy
```

### **2. Verify Installation**

```python
from smartapi import SmartConnect
import pyotp

print("✅ SmartAPI installed successfully")
```

---

## 🚀 **Quick Start**

### **1. Basic Connection Test**

```python
from core.market_data.angel_one_api import AngelOneAPI
from config.angel_one_credentials import *

# Initialize
api = AngelOneAPI(
    api_key=API_KEY,
    username=USERNAME,
    password=PASSWORD,
    totp_token=TOTP_TOKEN
)

# Login
if api.login():
    print("✅ Logged in successfully!")

    # Get Nifty spot
    nifty_ltp = api.get_ltp('NSE', 'NIFTY 50', 'NSE:NIFTY 50')
    print(f"Nifty: ₹{nifty_ltp:,.2f}")

    # Logout
    api.logout()
else:
    print("❌ Login failed")
```

### **2. Get Options Chain**

```python
# Get options chain
chain = api.get_options_chain('NIFTY')

print(f"Found {len(chain)} options")
print(chain.head())

# Get specific strike
atm_strike = 19500

call_option = chain[
    (chain['strike'] == atm_strike) &
    (chain['option_type'] == 'CE')
].iloc[0]

print(f"19500 CE: ₹{call_option['ltp']:.2f}")
```

### **3. Place Order (Paper Trading First!)**

```python
# ⚠️ TEST IN PAPER TRADING MODE FIRST!

# Place order
order_id = api.place_order(
    symbol='NIFTY',
    strike=19500,
    option_type='CE',
    transaction_type='BUY',
    quantity=1,  # 1 lot
    order_type='MARKET'
)

if order_id:
    print(f"✅ Order placed: {order_id}")

    # Check order status
    orders = api.get_orders()
    print(orders[orders['orderid'] == order_id])
```

---

## 🎯 **Intraday Strategies**

### **1. Gamma Scalping (Delta Neutral)**

**Concept:**
- Buy ATM straddle (long gamma)
- When spot moves, delta changes
- Hedge with futures to capture profits
- Repeat throughout the day

**Setup:**

```python
from strategies.hft_scalping.gamma_scalping import GammaScalpingStrategy

# Initialize
strategy = GammaScalpingStrategy(
    spot_price=19500,
    atm_strike=19500,
    atm_call_price=150,
    atm_put_price=140,
    delta_threshold=0.15,  # Hedge when |delta| > 0.15
    profit_target_pct=0.5  # Take profit at 0.5%
)

# Enter position
strategy.enter_position()

# Throughout the day: update Greeks and check adjustments
strategy.update_greeks(spot, call_delta, put_delta, call_gamma, put_gamma)
action = strategy.check_adjustment(current_spot)

if action:
    # Execute hedge
    strategy.execute_adjustment(action, execution_price)
```

**Best For:**
- High volatility days
- Range-bound markets with frequent oscillations
- Traders comfortable with frequent adjustments

**Time Frame:** 9:30 AM - 3:15 PM
**Capital Required:** ₹15,000 - ₹30,000
**Expected Return:** 1-3% per day

---

### **2. 0DTE (Zero Days to Expiry)**

**Concept:**
- Trade options on expiry day (Thursday)
- Maximum theta decay
- Quick scalps based on spot movement
- Exit by 3:20 PM (avoid assignment)

**Setup:**

```python
from strategies.hft_scalping.zero_dte_strategy import ZeroDTEStrategy

# Initialize
strategy = ZeroDTEStrategy(
    spot_price=19500,
    strategy_type='credit_spread',  # or 'atm_scalp'
    risk_per_trade=5000,
    profit_target_pct=50,
    stop_loss_pct=100,
    max_trades=5
)

# Check entry
should_enter = strategy.should_enter(
    spot=19500,
    iv=0.18,
    trend='sideways'
)

if should_enter:
    # Enter credit spread
    entry = strategy.enter_credit_spread(spot=19500, direction='put')

    # Place orders via API
    api.place_order(...)
```

**Best For:**
- Expiry day trading (Thursday)
- Quick scalps (5-30 minutes)
- Range-bound expiry days

**Time Frame:** 9:30 AM - 3:20 PM (Thursday only)
**Capital Required:** ₹5,000 - ₹10,000 per trade
**Expected Return:** 20-50% per trade (or -100%)

⚠️ **HIGH RISK** - Can lose 100% in minutes

---

### **3. Iron Condor Intraday**

**Concept:**
- Sell OTM call + put
- Buy further OTM for protection
- Profit from range-bound movement
- Adjust if one side breaches

**Setup:**

```python
from strategies.non_directional import IronCondor

# Create Iron Condor
ic = IronCondor(
    lower_long_put_strike=19200,
    lower_short_put_strike=19300,
    upper_short_call_strike=19700,
    upper_long_call_strike=19800,
    # ... premiums ...
    quantity=1,
    lot_size=50
)

# Check breakeven
breakevens = ic.breakeven_points()
print(f"Profit if Nifty stays between {breakevens[0]:.0f} - {breakevens[1]:.0f}")
```

**Best For:**
- Low volatility days
- Sideways markets
- Morning entries (9:30-10:30 AM)

**Time Frame:** 9:30 AM - 3:15 PM
**Capital Required:** ₹20,000 - ₹40,000
**Expected Return:** 2-5% per day

---

### **4. ATM Straddle Scalp (Volatility)**

**Concept:**
- Buy ATM straddle when IV is low
- Sell when IV increases or spot moves
- Quick scalps (10-30 minutes)

**Setup:**

```python
# Buy ATM straddle
atm = round(spot / 50) * 50  # Nearest strike

# Entry
api.place_order('NIFTY', atm, 'CE', 'BUY', 1)
api.place_order('NIFTY', atm, 'PE', 'BUY', 1)

# Exit targets
profit_target = entry_cost * 1.10  # 10% profit
stop_loss = entry_cost * 0.90      # 10% loss
```

**Best For:**
- High volatility expected (news, events)
- Strong directional moves
- Quick entries/exits

**Time Frame:** 10-30 minutes per trade
**Capital Required:** ₹15,000 - ₹25,000
**Expected Return:** 5-15% per trade

---

## 🤖 **Live Trading Engine**

**Automated trading with Angel One:**

```python
from core.order_management.live_trading_engine import LiveTradingEngine
from strategies.hft_scalping.gamma_scalping import GammaScalpingStrategy

# Setup API
api = AngelOneAPI(API_KEY, USERNAME, PASSWORD, TOTP_TOKEN)
api.login()

# Setup strategy
gamma_strategy = GammaScalpingStrategy(
    spot_price=19500,
    atm_strike=19500,
    atm_call_price=150,
    atm_put_price=140,
    delta_threshold=0.15,
    profit_target_pct=0.5
)

# Setup trading engine
engine = LiveTradingEngine(
    angel_api=api,
    risk_per_trade=10000,
    max_daily_loss=50000,
    max_daily_profit=100000
)

# Add strategy
engine.add_strategy('gamma_scalp', gamma_strategy)
engine.set_active_strategy('gamma_scalp')

# Start trading
engine.start()

# Monitor in separate thread
import time
while True:
    summary = engine.get_summary()
    print(f"P&L: ₹{summary['daily_pnl']:,.2f}")
    time.sleep(60)

    # Stop if needed
    if some_condition:
        engine.stop()
        break

# Logout
api.logout()
```

**Features:**
- ✅ Auto position monitoring
- ✅ Real-time Greeks calculation
- ✅ Risk limit enforcement
- ✅ Auto exit at 3:20 PM
- ✅ Daily P&L tracking

---

## ⚠️ **Risk Management**

### **1. Position Sizing**

```python
# Risk per trade: 1-2% of capital
account_size = 500000  # ₹5 lakh
risk_per_trade = account_size * 0.02  # ₹10,000

# Max positions: 3-5 simultaneously
max_positions = 3
```

### **2. Stop Loss**

```python
# Always set stop loss
entry_price = 150
stop_loss = entry_price * 0.50  # 50% of premium

# Exit if loss exceeds threshold
if current_price <= stop_loss:
    exit_position()
```

### **3. Daily Limits**

```python
# Max daily loss: 5% of capital
max_daily_loss = account_size * 0.05  # ₹25,000

# Max daily profit: 10% of capital
max_daily_profit = account_size * 0.10  # ₹50,000

# Stop trading if hit
if daily_pnl <= -max_daily_loss:
    stop_trading()
```

### **4. Time-based Rules**

```python
# Don't trade:
# - First 15 minutes (9:15-9:30 AM)
# - Last 10 minutes (3:20-3:30 PM)
# - During RBI announcements
# - On budget day (without preparation)
```

---

## 🐛 **Common Issues**

### **1. Login Failed**

**Problem:** TOTP error or login rejected

**Solutions:**
- ✅ Use **TOTP secret key**, not the 6-digit code
- ✅ Check if credentials are correct
- ✅ Ensure 2FA is enabled in Angel One
- ✅ Check if API is active in Angel One portal

```python
# Correct TOTP generation
import pyotp
totp = pyotp.TOTP(TOTP_TOKEN)
code = totp.now()  # 6-digit code
```

### **2. Order Rejected**

**Problem:** Insufficient funds or invalid parameters

**Solutions:**
- ✅ Check margin requirements
- ✅ Verify strike price exists
- ✅ Check if market is open
- ✅ Ensure lot size is correct

```python
# Check funds before order
positions = api.get_positions()
# Calculate available margin
```

### **3. Rate Limiting**

**Problem:** Too many API calls

**Solutions:**
- ✅ Limit options chain fetches (once per 5 seconds)
- ✅ Use WebSocket for live data (when available)
- ✅ Cache frequently used data

```python
import time

last_fetch = None
if last_fetch is None or (time.time() - last_fetch) >= 5:
    chain = api.get_options_chain('NIFTY')
    last_fetch = time.time()
```

### **4. Position Not Updating**

**Problem:** Positions not reflecting

**Solutions:**
- ✅ Wait for order to fill (check order status)
- ✅ Refresh positions after 2-3 seconds
- ✅ Check if order was rejected

```python
# Wait for order fill
time.sleep(2)
orders = api.get_orders()
# Check order status
```

---

## 📊 **Performance Monitoring**

### **Key Metrics to Track:**

```python
# Daily metrics
total_trades = len(trades)
winning_trades = sum(1 for t in trades if t['pnl'] > 0)
win_rate = winning_trades / total_trades * 100

avg_win = np.mean([t['pnl'] for t in trades if t['pnl'] > 0])
avg_loss = np.mean([t['pnl'] for t in trades if t['pnl'] < 0])

profit_factor = abs(sum(t['pnl'] for t in trades if t['pnl'] > 0) /
                    sum(t['pnl'] for t in trades if t['pnl'] < 0))

print(f"Win Rate: {win_rate:.2f}%")
print(f"Profit Factor: {profit_factor:.2f}")
print(f"Avg Win: ₹{avg_win:,.2f}")
print(f"Avg Loss: ₹{avg_loss:,.2f}")
```

---

## 🎓 **Best Practices**

1. **Always Paper Trade First**
   - Test strategies for 1-2 weeks
   - Verify execution logic
   - Check risk management

2. **Start Small**
   - Begin with 1 lot
   - Increase after consistent profits
   - Never risk more than 2% per trade

3. **Keep a Trading Journal**
   - Log all trades
   - Note market conditions
   - Review weekly

4. **Respect Risk Limits**
   - Set daily loss limits
   - Stop when limit hit
   - No revenge trading

5. **Continuous Learning**
   - Analyze losing trades
   - Study market behavior
   - Adapt strategies

---

## 📞 **Support**

- **Angel One Support**: 1800 123 4567
- **API Docs**: https://smartapi.angelbroking.com/docs
- **GitHub Issues**: Open an issue for bugs

---

## ⚠️ **DISCLAIMER**

**This software is for educational purposes only.**

- ❌ NOT financial advice
- ❌ NO guarantees of profit
- ❌ Can lose 100% of capital
- ✅ Trade at your own risk
- ✅ Test thoroughly before live trading
- ✅ Consult a financial advisor

**Options trading is risky. Only trade with money you can afford to lose.**

---

**Happy Trading! 🚀**

*Built with ❤️ for Indian retail traders*
