# 🤖 Machine Learning Models - Complete Guide

> **Deep dive into ML models for options trading in Indian markets**

---

## 📋 **Table of Contents**

1. [Overview](#overview)
2. [LSTM Price Predictor](#lstm-price-predictor)
3. [Random Forest Direction Predictor](#random-forest-direction-predictor)
4. [XGBoost Intraday Signals](#xgboost-intraday-signals)
5. [Feature Engineering](#feature-engineering)
6. [Model Training Best Practices](#model-training-best-practices)
7. [Backtesting ML Strategies](#backtesting-ml-strategies)
8. [Common Pitfalls](#common-pitfalls)

---

## 🎯 **Overview**

Machine Learning models help predict:
- **Price movements** (where will the market go?)
- **Direction** (up/down/sideways?)
- **Volatility** (how much will it move?)
- **Optimal entry/exit** (when to trade?)

### **Why ML for Options Trading?**

1. **Pattern Recognition**: ML identifies complex patterns humans miss
2. **Non-linear Relationships**: Captures interactions between indicators
3. **Adaptive**: Models learn from new data
4. **Backtestable**: Quantify performance before live trading

---

## 🧠 **1. LSTM Price Predictor**

### **What is LSTM?**

**LSTM (Long Short-Term Memory)** is a type of Recurrent Neural Network (RNN) designed for **sequential data** like time series.

### **Why LSTM for Price Prediction?**

Traditional neural networks treat each input independently. But prices have **temporal dependencies**:
- Today's price depends on yesterday's price
- Last week's trend affects today's movement
- Seasonal patterns repeat

LSTM **remembers** past information through:
1. **Cell State**: Long-term memory
2. **Hidden State**: Short-term memory
3. **Gates**: Control what to remember/forget

### **Architecture**

```
Input Layer (60 days of prices)
        ↓
LSTM Layer 1 (128 units) → Captures long-term trends
        ↓
Dropout (20%) → Prevents overfitting
        ↓
LSTM Layer 2 (64 units) → Captures medium-term patterns
        ↓
Dropout (20%)
        ↓
LSTM Layer 3 (32 units) → Captures short-term movements
        ↓
Dropout (20%)
        ↓
Dense Layer (16 units, ReLU) → Non-linear transformations
        ↓
Output Layer (1 unit) → Predicted price
```

### **How It Works**

1. **Input**: Last 60 days of prices (normalized 0-1)
2. **Processing**: Each LSTM layer processes the sequence
3. **Output**: Predicted price for next day (or N days ahead)

### **Training Process**

```python
from ml_models.price_prediction import LSTMPricePredictor

# 1. Initialize
predictor = LSTMPricePredictor(
    lookback=60,           # Use last 60 days
    prediction_days=1,     # Predict 1 day ahead
    lstm_units=[128, 64, 32],  # 3 LSTM layers
    dropout_rate=0.2       # 20% dropout
)

# 2. Prepare data
predictor.prepare_data(prices, train_size=0.8)

# 3. Build model
predictor.build_model(bidirectional=False)

# 4. Train
predictor.train(epochs=100, batch_size=32)

# 5. Evaluate
metrics = predictor.evaluate()
print(f"RMSE: {metrics['rmse']:.2f}")
print(f"R²: {metrics['r2']:.4f}")

# 6. Predict next 5 days
recent_prices = prices[-60:]  # Last 60 days
predictions = predictor.predict_next(recent_prices, n_steps=5)
```

### **Key Parameters**

| Parameter | Description | Typical Range | Impact |
|-----------|-------------|---------------|--------|
| `lookback` | Days of history | 30-120 | More = better long-term patterns, slower |
| `lstm_units` | Neurons per layer | 32-256 | More = more complex patterns, overfitting risk |
| `dropout_rate` | Regularization | 0.1-0.5 | Higher = less overfitting, but may underfit |
| `learning_rate` | Optimization speed | 0.0001-0.01 | Lower = stable but slow, higher = fast but unstable |

### **Interpreting Results**

**Good Model Indicators:**
- RMSE < 1% of price (e.g., RMSE < 200 for Nifty @ 20000)
- R² > 0.7 (explains 70%+ variance)
- Predictions follow general trend (not noisy)

**Bad Model Indicators:**
- Predictions lag actual prices (model just copies previous value)
- High variance in predictions
- R² < 0.3

### **When to Use LSTM**

✅ **Good for:**
- Multi-day ahead predictions
- Capturing long-term trends
- Markets with strong momentum

❌ **Not good for:**
- Very noisy markets
- Event-driven moves (news, earnings)
- Markets without patterns

---

## 🌳 **2. Random Forest Direction Predictor**

### **What is Random Forest?**

**Random Forest** is an **ensemble** of decision trees. Each tree votes, and majority wins.

### **How It Works**

```
Training Data
    ↓
[Tree 1]  [Tree 2]  [Tree 3] ... [Tree 200]
    ↓         ↓         ↓            ↓
  Down      Up      Sideways       Up
    ↓
    Voting: 2 Up, 1 Down, 1 Sideways
    ↓
  Final Prediction: UP
```

### **Why Random Forest for Direction?**

1. **Handles Non-linearity**: Captures complex interactions
2. **Feature Importance**: Shows which indicators matter
3. **Robust**: Not sensitive to outliers
4. **No Scaling Required**: Works with raw features

### **Feature Engineering**

The model uses 30+ technical indicators:

**Trend Indicators:**
- SMA (5, 10, 20, 50 days)
- EMA (5, 10, 20, 50 days)
- Price-to-MA ratios

**Momentum Indicators:**
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Rate of Change

**Volatility Indicators:**
- Bollinger Bands (width, position)
- ATR (Average True Range)
- Standard deviation

**Volume Indicators:**
- Volume SMA
- Volume ratio (current / average)

### **Training Process**

```python
from ml_models.price_prediction import RandomForestPredictor

# 1. Initialize
predictor = RandomForestPredictor(
    n_estimators=200,      # 200 trees
    max_depth=15,          # Max tree depth
    min_samples_split=10
)

# 2. Create features
data = predictor.create_features(
    df,                    # OHLCV data
    forward_days=1,        # Predict next day
    threshold_pct=0.5      # 0.5% move = trend
)

# 3. Prepare data
predictor.prepare_data(data, test_size=0.2)

# 4. Train
predictor.train(cv_folds=5)

# 5. Evaluate
predictor.evaluate()

# 6. Get important features
importance = predictor.feature_importance(top_n=10)
print(importance)

# 7. Predict
direction, confidence = predictor.predict_direction(features)
print(f"{direction} with {confidence*100:.1f}% confidence")
```

### **Understanding Output**

**Direction Classes:**
- **0 = Down**: Price expected to fall > 0.5%
- **1 = Sideways**: Price expected to move < 0.5%
- **2 = Up**: Price expected to rise > 0.5%

**Confidence:**
- Based on % of trees voting for the prediction
- High confidence (> 70%): Strong signal
- Low confidence (< 60%): Uncertain, avoid trading

### **Feature Importance**

Shows which indicators the model finds most useful:

```
Feature              Importance
-----------------------------------
rsi                  0.15  ← Most important
price_to_sma20       0.12
macd_diff            0.10
volatility_20        0.08
bb_position          0.07
```

**Interpretation:**
- RSI (momentum) is most predictive
- Price relative to SMA20 (trend) is second
- Focus on top 5-10 features for efficiency

### **Trading Signals**

```python
signal = predictor.predict_signal(features)

if signal == 1:
    # BUY signal - Buy call options
    print("Buy Call Options")
elif signal == -1:
    # SELL signal - Buy put options
    print("Buy Put Options")
else:
    # HOLD signal - No trade
    print("Stay out")
```

### **When to Use Random Forest**

✅ **Good for:**
- Classification (up/down/sideways)
- Feature selection
- Interpretability (feature importance)
- Robust predictions

❌ **Not good for:**
- Exact price predictions
- Very fast changes (needs time to adapt)

---

## ⚡ **3. XGBoost for Intraday Signals**

### **What is XGBoost?**

**XGBoost (eXtreme Gradient Boosting)** builds trees **sequentially**, where each tree corrects errors of previous trees.

### **Gradient Boosting vs Random Forest**

| Aspect | Random Forest | XGBoost |
|--------|---------------|---------|
| Training | Parallel (all trees together) | Sequential (one after another) |
| Focus | Reduce variance | Reduce bias |
| Speed | Faster | Slower training, faster inference |
| Accuracy | Good | Often better |
| Overfitting Risk | Lower | Higher (needs tuning) |

### **Why XGBoost for Intraday?**

1. **High Accuracy**: Often beats other models
2. **Feature Interaction**: Automatically finds interactions
3. **Handles Imbalance**: Good for rare events (big moves)
4. **Fast Inference**: Quick predictions (critical for HFT)

### **Architecture**

```
Initial Prediction: Mean of target
    ↓
Tree 1: Learns from residuals
    ↓
Tree 2: Learns from remaining errors
    ↓
Tree 3: Corrects further
    ↓
...
    ↓
Tree N: Final corrections
    ↓
Final Prediction: Sum of all trees
```

### **Key Hyperparameters**

```python
params = {
    'n_estimators': 500,        # Number of trees
    'max_depth': 6,             # Tree depth
    'learning_rate': 0.01,      # Step size
    'subsample': 0.8,           # Row sampling
    'colsample_bytree': 0.8,    # Column sampling
    'min_child_weight': 5,      # Minimum samples in leaf
    'gamma': 0.1,               # Regularization
}
```

**Tuning Tips:**
- Start with `learning_rate=0.1`, then reduce to 0.01
- Increase `n_estimators` if underfitting
- Reduce `max_depth` if overfitting
- Use early stopping to prevent overtraining

### **When to Use XGBoost**

✅ **Good for:**
- High-frequency / intraday signals
- When accuracy is critical
- Tabular data with many features

❌ **Not good for:**
- Very small datasets (< 1000 samples)
- When interpretability is priority
- Real-time trading (training is slow)

---

## 🛠️ **4. Feature Engineering**

### **Why Feature Engineering Matters**

> "Garbage in, garbage out"

Even the best ML model fails with poor features.

### **Types of Features**

#### **A. Price-based Features**

```python
# Returns
df['returns'] = df['close'].pct_change()
df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

# Lagged features
df['close_lag_1'] = df['close'].shift(1)
df['close_lag_5'] = df['close'].shift(5)

# Price ratios
df['high_low_ratio'] = df['high'] / df['low']
df['close_open_ratio'] = df['close'] / df['open']
```

#### **B. Technical Indicators**

```python
# Moving Averages
df['sma_20'] = df['close'].rolling(20).mean()
df['ema_20'] = df['close'].ewm(span=20).mean()

# RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# MACD
ema_12 = df['close'].ewm(span=12).mean()
ema_26 = df['close'].ewm(span=26).mean()
df['macd'] = ema_12 - ema_26
df['macd_signal'] = df['macd'].ewm(span=9).mean()

# Bollinger Bands
df['bb_middle'] = df['close'].rolling(20).mean()
bb_std = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_middle'] + 2 * bb_std
df['bb_lower'] = df['bb_middle'] - 2 * bb_std
df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
```

#### **C. Volatility Features**

```python
# Historical Volatility
df['volatility'] = df['returns'].rolling(20).std()

# ATR (Average True Range)
high_low = df['high'] - df['low']
high_close = np.abs(df['high'] - df['close'].shift())
low_close = np.abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.rolling(14).mean()

# Realized Volatility
df['realized_vol'] = df['returns'].rolling(20).std() * np.sqrt(252)
```

#### **D. Volume Features**

```python
# Volume indicators
df['volume_sma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_sma']

# VWAP (Volume-Weighted Average Price)
df['vwap'] = (df['close'] * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()

# On-Balance Volume
df['obv'] = (np.sign(df['returns']) * df['volume']).cumsum()
```

#### **E. Time-based Features**

```python
df['day_of_week'] = df['date'].dt.dayofweek
df['day_of_month'] = df['date'].dt.day
df['month'] = df['date'].dt.month
df['quarter'] = df['date'].dt.quarter

# Cyclical encoding
df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
```

### **Feature Selection**

**Methods:**
1. **Correlation Analysis**: Remove highly correlated features
2. **Feature Importance**: Use Random Forest importance
3. **Recursive Feature Elimination**: Iteratively remove least important
4. **LASSO Regularization**: L1 penalty shrinks weak features to zero

```python
# Remove correlated features
corr_matrix = df.corr().abs()
upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
to_drop = [column for column in upper.columns if any(upper[column] > 0.95)]
df_clean = df.drop(to_drop, axis=1)
```

---

## 📚 **5. Model Training Best Practices**

### **A. Data Splitting**

**Time-Series Split** (NOT random split!):

```python
# Wrong (data leakage!)
X_train, X_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Correct
train_size = int(len(X) * 0.8)
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]
```

**Why?** Random split uses future data to predict past (lookahead bias).

### **B. Cross-Validation**

**Purged K-Fold**:

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)

for train_idx, val_idx in tscv.split(X):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    model.fit(X_train, y_train)
    score = model.score(X_val, y_val)
```

### **C. Walk-Forward Optimization**

```
Training    Validation   Test
|---------|    |-----|   |---|
           ↓
          Train
                         ↓
                       Validate
                                ↓
                              Test

Then roll forward:

    Training    Validation   Test
    |---------|    |-----|   |---|
               ↓
              Train
                           ↓
                         Validate
                                  ↓
                                Test
```

### **D. Hyperparameter Tuning**

```python
from sklearn.model_selection import RandomizedSearchCV

param_dist = {
    'n_estimators': [100, 200, 500],
    'max_depth': [5, 10, 15, 20],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4]
}

search = RandomizedSearchCV(
    RandomForestClassifier(),
    param_dist,
    n_iter=20,
    cv=TimeSeriesSplit(n_splits=5),
    scoring='accuracy'
)

search.fit(X_train, y_train)
best_model = search.best_estimator_
```

### **E. Preventing Overfitting**

1. **Regularization**: L1/L2 penalties
2. **Dropout**: For neural networks
3. **Early Stopping**: Stop when validation loss increases
4. **Ensemble**: Combine multiple models
5. **Cross-validation**: Validate on unseen data
6. **Simplify Model**: Reduce layers/trees

---

## 📊 **6. Backtesting ML Strategies**

### **Example: LSTM Strategy Backtest**

```python
from ml_models.price_prediction import LSTMPricePredictor
from backtesting.options_backtest import OptionsBacktester

# 1. Train LSTM
predictor = LSTMPricePredictor(lookback=60)
predictor.prepare_data(prices)
predictor.build_model()
predictor.train(epochs=100)

# 2. Setup backtester
backtester = OptionsBacktester(initial_capital=100000)
backtester.load_data(options_data)

# 3. Run backtest
for timestamp, data in backtester.iterate():
    # Get recent prices
    recent_prices = get_recent_prices(timestamp, lookback=60)

    # Predict
    prediction = predictor.predict_next(recent_prices, n_steps=1)[0]
    current_price = data['spot'].iloc[0]

    # Trading logic
    if prediction > current_price * 1.01:  # Expect 1%+ move up
        # Buy call
        backtester.place_order('NIFTY', atm_strike, 'CE', 'BUY', 1)
    elif prediction < current_price * 0.99:  # Expect 1%+ move down
        # Buy put
        backtester.place_order('NIFTY', atm_strike, 'PE', 'BUY', 1)

# 4. Results
results = backtester.get_results()
backtester.print_results()
```

---

## ⚠️ **7. Common Pitfalls**

### **1. Lookahead Bias**

**Problem**: Using future data to predict past

**Example:**
```python
# Wrong!
df['target'] = (df['close'].shift(-1) / df['close']) - 1
df['sma'] = df['close'].rolling(20).mean()  # Uses future!
```

**Solution**: Ensure features only use past data

### **2. Data Snooping**

**Problem**: Testing multiple strategies on same data

**Solution**: Use out-of-sample test set (never touch during development)

### **3. Overfitting**

**Signs:**
- High training accuracy, low test accuracy
- Model performs perfectly in backtest, fails in live trading

**Solutions:**
- Cross-validation
- Simpler models
- Regularization

### **4. Survivorship Bias**

**Problem**: Only using stocks that exist today (ignoring delisted/bankrupt)

**Solution**: Use survivorship-bias-free data

### **5. Ignoring Transaction Costs**

**Problem**: Backtest shows profit, but costs eat it all

**Solution**: Include realistic brokerage, slippage, STT

---

## 🎓 **Summary**

| Model | Use Case | Pros | Cons |
|-------|----------|------|------|
| **LSTM** | Multi-day price prediction | Captures long-term patterns | Slow, needs lots of data |
| **Random Forest** | Direction classification | Interpretable, robust | Not for exact prices |
| **XGBoost** | Intraday signals | High accuracy | Overfitting risk |

**Key Takeaways:**
1. Feature engineering > model choice
2. Avoid lookahead bias at all costs
3. Use time-series split, not random split
4. Backtest with realistic costs
5. Start simple, then add complexity

---

**Next Steps:**
- Read the [Backtesting Guide](BACKTESTING_GUIDE.md)
- Explore [Strategy Examples](../examples/)
- Join our [Discord Community](#)

---

*Happy Trading! 🚀*
