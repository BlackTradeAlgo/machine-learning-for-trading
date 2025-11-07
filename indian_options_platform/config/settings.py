"""
Configuration Settings for Indian Options Trading Platform
"""

from typing import Dict
import os
from datetime import time

# ==================== MARKET SETTINGS ====================

# NSE Lot Sizes (as of 2024)
NSE_LOT_SIZES: Dict[str, int] = {
    'NIFTY': 50,
    'BANKNIFTY': 15,
    'FINNIFTY': 40,
    'MIDCPNIFTY': 75,
    'SENSEX': 10
}

# Strike intervals
STRIKE_INTERVALS: Dict[str, int] = {
    'NIFTY': 50,
    'BANKNIFTY': 100,
    'FINNIFTY': 50,
    'MIDCPNIFTY': 25
}

# Trading hours (IST)
MARKET_OPEN_TIME = time(9, 15)
MARKET_CLOSE_TIME = time(15, 30)

# Risk-free rate (approximate Indian T-bill rate)
RISK_FREE_RATE = 0.07  # 7%

# ==================== RISK MANAGEMENT ====================

# Position limits
MAX_POSITION_SIZE = 100000  # ₹1 lakh max per position
MAX_PORTFOLIO_VALUE = 1000000  # ₹10 lakh max portfolio
MAX_PORTFOLIO_RISK = 0.02  # 2% max risk per trade

# Greeks limits
MAX_DELTA_EXPOSURE = 100  # Max delta exposure
MAX_GAMMA_EXPOSURE = 50
MAX_VEGA_EXPOSURE = 1000

# Stop loss settings
DEFAULT_STOP_LOSS_PCT = 0.5  # 50% of premium for long options
DEFAULT_PROFIT_TARGET_PCT = 0.5  # 50% of max profit

# ==================== DATA SETTINGS ====================

# Update intervals
DATA_UPDATE_INTERVAL = 1  # seconds
OPTIONS_CHAIN_UPDATE_INTERVAL = 5  # seconds
CACHE_DURATION = 300  # 5 minutes

# Data source priorities
DATA_SOURCE_PRIORITY = ['NSE', 'BSE', 'YAHOO']

# Historical data
HISTORICAL_DATA_DAYS = 365  # 1 year
IV_HISTORICAL_PERIOD = 252  # 1 year of trading days

# ==================== STRATEGY SETTINGS ====================

# Iron Condor defaults
IRON_CONDOR_DEFAULTS = {
    'put_width': 100,
    'call_width': 100,
    'distance_from_spot': 150,
    'target_credit': 50
}

# Straddle defaults
STRADDLE_DEFAULTS = {
    'min_iv_percentile': 30,  # For long straddle
    'max_iv_percentile': 70,  # For short straddle
}

# ==================== BACKTESTING SETTINGS ====================

# Transaction costs
BROKERAGE_PER_ORDER = 20  # Flat ₹20 per order
STT_RATE = 0.0005  # 0.05% on sell side
EXCHANGE_CHARGES_RATE = 0.0005
GST_RATE = 0.18

# Slippage
DEFAULT_SLIPPAGE = 0.01  # 1 tick

# Initial capital
INITIAL_CAPITAL = 100000  # ₹1 lakh

# ==================== ML MODEL SETTINGS ====================

# Model training
TRAIN_TEST_SPLIT = 0.8
VALIDATION_SPLIT = 0.2
RANDOM_STATE = 42

# LSTM parameters
LSTM_LOOKBACK = 60
LSTM_EPOCHS = 100
LSTM_BATCH_SIZE = 32

# Random Forest parameters
RF_N_ESTIMATORS = 100
RF_MAX_DEPTH = 10

# ==================== ALERT SETTINGS ====================

# Telegram (set in environment variables)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Email (set in environment variables)
EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587'))
EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')

# Alert thresholds
PRICE_ALERT_THRESHOLD = 0.02  # 2% move
IV_ALERT_THRESHOLD = 0.1  # 10% IV change
PCR_ALERT_THRESHOLD = 0.2  # 20% PCR change

# ==================== LOGGING SETTINGS ====================

LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/platform.log'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ==================== DATABASE SETTINGS ====================

# PostgreSQL (for historical data)
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'options_trading')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')

# Redis (for caching and real-time data)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# ==================== API SETTINGS ====================

# NSE URLs
NSE_BASE_URL = 'https://www.nseindia.com'
NSE_API_BASE = 'https://www.nseindia.com/api'

# Broker API keys (set in environment variables)
ZERODHA_API_KEY = os.getenv('ZERODHA_API_KEY', '')
ZERODHA_API_SECRET = os.getenv('ZERODHA_API_SECRET', '')

UPSTOX_API_KEY = os.getenv('UPSTOX_API_KEY', '')
UPSTOX_API_SECRET = os.getenv('UPSTOX_API_SECRET', '')

# ==================== FEATURE FLAGS ====================

# Enable/disable features
ENABLE_LIVE_TRADING = False  # Set to True for live trading
ENABLE_PAPER_TRADING = True
ENABLE_ML_PREDICTIONS = False  # ML models not ready yet
ENABLE_SENTIMENT_ANALYSIS = False
ENABLE_TELEGRAM_ALERTS = False

# ==================== DEVELOPMENT SETTINGS ====================

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
TESTING = os.getenv('TESTING', 'False').lower() == 'true'

# ==================== PATHS ====================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')

# Create directories if they don't exist
for directory in [DATA_DIR, MODELS_DIR, LOGS_DIR, RESULTS_DIR]:
    os.makedirs(directory, exist_ok=True)
