# 🇮🇳 Indian Options Trading Platform

> **A comprehensive, AI-powered options trading platform designed specifically for the Indian market (NSE/BSE)**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-yellow)](https://github.com)

---

## 🎯 **Vision**

Democratizing institutional-grade options trading tools for retail traders in India. This platform brings advanced analytics, ML-powered predictions, and HFT-style capabilities to individual traders.

---

## ✨ **Key Features**

### **📊 Core Capabilities**

- ✅ **Options Pricing Engine**
  - Black-Scholes model for European options
  - Real-time Greeks calculation (Delta, Gamma, Vega, Theta, Rho)
  - Second-order Greeks (Vanna, Charm, Vomma, Vera)
  - Implied Volatility calculation (Newton-Raphson, Brent's method)
  - IV surface modeling and skew analysis

- ✅ **NSE/BSE Integration**
  - Real-time options chain data
  - Nifty, Bank Nifty, Fin Nifty support
  - India VIX tracking
  - FII/DII data integration
  - Put-Call Ratio (PCR) analysis
  - Max Pain calculation
  - Open Interest analysis

- ✅ **Unified Strategy Library (v2.0.0)** - Intraday Focused
  - **HFT/Scalping** (Pure Intraday):
    - Gamma Scalping (delta-neutral with futures hedging)
    - Zero DTE (0 Days To Expiry - expiry day only)
  - **Range-Bound**: Iron Condor (limited risk/reward)
  - **Volatility**: Long/Short Straddle (quick intraday scalps)
  - **Smart Strategy Selector**: Auto-recommend based on market conditions
  - **See [STRATEGY_GUIDE.md](STRATEGY_GUIDE.md) for complete guide**

### **🤖 AI/ML Features**

- ✅ **LSTM Price Predictor** - Multi-step price forecasting
- ✅ **Random Forest Direction Classifier** - Up/Down/Sideways prediction
- ✅ **30+ Technical Features** - Automated feature engineering
- 🔄 XGBoost for intraday signals (Coming Soon)
- 🔄 GARCH for volatility forecasting (Coming Soon)
- 🔄 Sentiment analysis (Twitter, Reddit, News) (Coming Soon)

### **📈 Analytics & Risk Management**

- Portfolio Greeks aggregation
- Real-time P&L tracking
- Risk-reward ratios
- Breakeven analysis
- Probability of profit (Monte Carlo)
- Max drawdown monitoring
- SPAN margin calculator

### **🔄 Backtesting & Paper Trading**

- ✅ **Event-Driven Backtest Engine** - Bar-by-bar simulation
- ✅ **Realistic Cost Modeling** - STT, brokerage, GST, slippage
- ✅ **Paper Trading Account** - Virtual trading with real prices
- ✅ **Performance Analytics** - Sharpe, Sortino, max drawdown
- 🔄 Walk-forward optimization (Coming Soon)

### **🔥 Live Trading Integration**

- ✅ **Angel One SmartAPI** - Complete integration with live trading
- ✅ **Live Trading Engine** - Automated strategy execution
- ✅ **Real-time Greeks** - Auto-calculated from live prices
- ✅ **Risk Management** - Daily loss/profit limits, position sizing
- ✅ **Auto Exit** - Mandatory 3:15 PM exit for intraday
- ✅ **WebSocket Support** - Real-time tick data streaming
- **See [ANGEL_ONE_SETUP.md](ANGEL_ONE_SETUP.md) for setup guide**

---

## 🏗️ **Architecture**

```
indian_options_platform/
├── core/
│   ├── options_pricing/       # ✅ Black-Scholes, Greeks, IV
│   ├── market_data/            # ✅ NSE data + Angel One API
│   ├── order_management/       # ✅ Live trading + Paper trading
│   │   ├── live_trading_engine.py
│   │   └── paper_trading.py
│   └── risk_engine/            # Risk management (coming soon)
│
├── strategies/                # ✅ Unified Strategy Library (v2.0.0)
│   ├── base_strategy.py      # Core base class
│   ├── non_directional/      # Iron Condor, Straddle
│   ├── hft_scalping/         # ✅ Gamma Scalping, Zero DTE
│   └── __init__.py           # ✅ Smart strategy selector
│
├── ml_models/                 # ✅ ML Models
│   ├── price_prediction/     # ✅ LSTM, Random Forest
│   │   ├── lstm_predictor.py
│   │   └── random_forest_predictor.py
│   └── (more coming soon)
│
├── backtesting/               # ✅ Backtesting Engine
│   ├── options_backtest/     # ✅ Event-driven engine
│   └── transaction_costs/    # ✅ STT, brokerage, slippage
│
├── dashboard/                 # Web dashboard (coming soon)
│   ├── live_monitoring/
│   ├── strategy_selector/
│   └── analytics/
│
├── data/                      # Data storage
│   ├── nse_options/
│   ├── bse_options/
│   ├── live_feeds/
│   └── historical/
│
├── utils/                     # Utilities
├── tests/                     # Unit tests
├── docs/                      # Documentation
└── config/                    # Configuration files
```

---

## 🚀 **Quick Start**

### **Installation**

```bash
# Clone the repository
git clone https://github.com/yourusername/indian-options-platform.git
cd indian-options-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **Basic Usage**

#### **1. Calculate Option Price & Greeks**

```python
from core.options_pricing import BlackScholes, Greeks

# Initialize
bs = BlackScholes()
greeks_calc = Greeks()

# Nifty option parameters
spot = 19500
strike = 19500  # ATM
T = 7 / 365  # 7 days to expiry
r = 0.07  # 7% risk-free rate
sigma = 0.15  # 15% volatility

# Calculate prices
call_price = bs.call_price(spot, strike, T, r, sigma)
put_price = bs.put_price(spot, strike, T, r, sigma)

print(f"Call Price: ₹{call_price:.2f}")
print(f"Put Price: ₹{put_price:.2f}")

# Calculate Greeks
greeks = greeks_calc.all_greeks(spot, strike, T, r, sigma, 'call')
for name, value in greeks.items():
    print(f"{name.capitalize()}: {value:.4f}")
```

#### **2. Fetch NSE Options Chain**

```python
from core.market_data import NSEData

# Initialize
nse = NSEData()

# Check if market is open
is_open = nse.is_market_open()
print(f"Market Status: {'OPEN' if is_open else 'CLOSED'}")

# Get Nifty options chain
chain = nse.get_options_chain('NIFTY')

if chain is not None:
    spot = chain.attrs['spot']
    print(f"Nifty Spot: ₹{spot:,.2f}")

    # Calculate PCR
    pcr = nse.calculate_pcr(chain)
    print(f"Put-Call Ratio: {pcr:.4f}")

    # Max Pain
    max_pain = nse.calculate_max_pain(chain)
    print(f"Max Pain Strike: {max_pain:.0f}")
```

#### **3. Create Iron Condor Strategy**

```python
from strategies.non_directional import IronCondor

# Create Iron Condor
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

# Print summary
ic.print_detailed_summary()

# Plot payoff diagram
ic.plot_payoff(current_spot=19500)
```

#### **4. Calculate Implied Volatility**

```python
from core.options_pricing import ImpliedVolatility

iv_calc = ImpliedVolatility()

# Market parameters
market_price = 150  # Current option price
spot = 19500
strike = 19500
T = 7 / 365
r = 0.07

# Calculate IV
iv = iv_calc.calculate(market_price, spot, strike, T, r, 'call')

if iv:
    print(f"Implied Volatility: {iv*100:.2f}%")
else:
    print("IV calculation failed")
```

---

## 📚 **Strategy Examples**

### **Iron Condor** (Range-Bound Market)

```python
from strategies.non_directional import IronCondor

# Auto-generate balanced Iron Condor
ic = IronCondor.create_balanced(
    spot=19500,
    put_width=100,
    call_width=100,
    distance_from_spot=150,
    quantity=2,
    lot_size=50
)

ic.print_detailed_summary()
```

**When to Use:**
- Low volatility environment (IV Rank < 50)
- Expecting range-bound movement
- High probability of profit (~70-80%)

**Risk:** Limited (width of spread - net credit)
**Reward:** Limited (net credit received)

---

### **Long Straddle** (Volatility Play)

```python
from strategies.non_directional import LongStraddle

# Before major event (e.g., Budget Day)
straddle = LongStraddle(
    strike=19500,  # ATM
    call_premium=150,
    put_premium=140,
    quantity=1,
    lot_size=50
)

straddle.print_detailed_summary(
    current_iv=0.12,  # Current IV: 12%
    historical_iv=0.15  # Historical avg: 15%
)
```

**When to Use:**
- Before major events (earnings, RBI policy, budget)
- Low IV environment (cheap options)
- Expecting large move but direction uncertain

**Risk:** Limited (total premium paid)
**Reward:** Unlimited

---

## 🛠️ **Configuration**

### **config/settings.py**

```python
# Market settings
NSE_LOT_SIZES = {
    'NIFTY': 50,
    'BANKNIFTY': 15,
    'FINNIFTY': 40,
    'MIDCPNIFTY': 75
}

# Risk settings
MAX_POSITION_SIZE = 100000  # ₹1 lakh
MAX_PORTFOLIO_RISK = 0.02  # 2% max risk per trade
RISK_FREE_RATE = 0.07  # 7% (Indian T-bill rate)

# Trading hours (IST)
MARKET_OPEN_TIME = "09:15"
MARKET_CLOSE_TIME = "15:30"

# Data settings
DATA_UPDATE_INTERVAL = 1  # seconds
CACHE_DURATION = 300  # 5 minutes
```

---

## 📊 **Performance Metrics**

The platform tracks comprehensive metrics:

- **Sharpe Ratio**: Risk-adjusted returns
- **Sortino Ratio**: Downside risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Return on Capital**: Total return / Capital deployed

---

## 🔐 **Risk Management**

Built-in risk controls:

- Position size limits
- Portfolio heat monitoring
- Greeks-based exposure limits
- Auto stop-loss triggers
- Margin requirement tracking
- Correlation-based risk assessment

---

## 🗺️ **Roadmap**

### **Phase 1: Core Infrastructure** ✅ (Current)
- [x] Options pricing engine
- [x] Greeks calculation
- [x] NSE data integration
- [x] Basic strategy library
- [x] Risk metrics

### **Phase 2: ML Integration** (In Progress)
- [ ] LSTM price prediction
- [ ] IV forecasting (GARCH)
- [ ] Sentiment analysis
- [ ] Smart money detection
- [ ] Strategy optimization (Genetic Algorithms)

### **Phase 3: Backtesting** (Next)
- [ ] Event-driven backtest engine
- [ ] Slippage & transaction cost models
- [ ] Walk-forward optimization
- [ ] Multi-strategy backtesting
- [ ] Performance analytics

### **Phase 4: Live Trading** (Future)
- [ ] Broker integration (Zerodha, Upstox, etc.)
- [ ] Paper trading mode
- [ ] Real-time monitoring dashboard
- [ ] Alert system (Telegram, Email, SMS)
- [ ] Automated order execution

### **Phase 5: Advanced Features** (Future)
- [ ] Portfolio optimization
- [ ] Multi-leg order execution
- [ ] Options flow tracker
- [ ] Web-based dashboard
- [ ] Mobile app

---

## 🤝 **Contributing**

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ **Disclaimer**

**This software is for educational and research purposes only. Trading options involves substantial risk of loss. Past performance is not indicative of future results. Always consult with a qualified financial advisor before making investment decisions.**

The developers and contributors of this project:
- Do NOT provide investment advice
- Are NOT registered financial advisors
- Accept NO liability for trading losses
- Make NO guarantees about profitability

**Trade at your own risk. Only risk capital you can afford to lose.**

---

## 📞 **Contact & Support**

- **Issues**: [GitHub Issues](https://github.com/yourusername/indian-options-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/indian-options-platform/discussions)
- **Email**: support@example.com

---

## 🙏 **Acknowledgments**

Built upon the excellent [Machine Learning for Trading](https://github.com/stefan-jansen/machine-learning-for-trading) repository.

Special thanks to:
- NSE India for market data
- The Python quant finance community
- All contributors and testers

---

## 📈 **Show Your Support**

If you find this project useful, please ⭐ star the repository!

---

**Made with ❤️ for Indian retail traders**

*"Democratizing institutional-grade trading tools for everyone"*
