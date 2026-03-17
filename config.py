import os
from dotenv import load_dotenv

load_dotenv()

# MEXC API Credentials
MEXC_API_KEY = os.getenv("MEXC_API_KEY", "")
MEXC_API_SECRET = os.getenv("MEXC_API_SECRET", "")

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Config variables
TIMEFRAMES = ["15m", "1h", "4h", "1d", "1w"]

# Core pairs (always monitor these)
CORE_PAIRS = ["BTC/USDT", "ETH/USDT"]

# How many top coins by volume to track for SMC main strategy
TOP_COINS_LIMIT = 50

# How many coins to track for the Spike/Pump Scanner (to catch memecoins/shitcoins outside top 50)
MEMECOIN_V2_LIMIT = 250

# Spike Scanner parameters (Tuned for 15m pumps)
SPIKE_VOLUME_MULTIPLIER = 4.0 # Candle volume must be 4x the moving average (stricter for accuracy)
SPIKE_PRICE_ATR_MULTIPLIER = 2.5 # Candle body must be 2.5x the ATR
SPIKE_MIN_PCT_CHANGE = 2.0 # Minimum % move in 15m candle to trigger pump alert

# SMC Analyzer parameters
SMC_LOOKBACK_PERIOD = 200 # Candles to look back for structure

# Risk Management
RISK_PER_TRADE_PERCENT = 1.0 # 1% of total balance per trade
MAX_OPEN_POSITIONS = 3
LEVERAGE = 10
