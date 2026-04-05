import os
from dotenv import load_dotenv

load_dotenv()

# MEXC API Credentials (Bot 1 - Signals)
MEXC_API_KEY = os.getenv("MEXC_API_KEY", "")
MEXC_API_SECRET = os.getenv("MEXC_API_SECRET", "")

# BingX API Credentials (Bot 2 - AutoTrading)
BINGX_API_KEY = os.getenv("BINGX_API_KEY", "")
BINGX_API_SECRET = os.getenv("BINGX_API_SECRET", "")

# AutoTrading Master Switch
AUTO_TRADING_ENABLED = os.getenv("AUTO_TRADING_ENABLED", "False").lower() in ('true', '1', 't')

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Config variables
TIMEFRAMES = ["15m", "1h", "4h", "1d", "1w"]

# Core Target Pairs (Единый источник правды)
TARGET_COINS = ["BTC", "ETH", "SOL"]

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

# Global Risk Management (For Alerts / MEXC)
RISK_PER_TRADE_PERCENT = 1.0 # 1% of total balance per trade
MAX_OPEN_POSITIONS = 3
LEVERAGE = 10

# BingX AutoTrader Risk Management
BINGX_MAX_OPEN_POSITIONS = 5 # Strict limit on concurrent open trades
BINGX_BTC_ETH_MARGIN_PER_ORDER = 3.34 # 3.34 USDT на каждый из 3 ордеров в сетке (Итого ~10$ на сделку)
BINGX_MARGIN_PER_ORDER = 2.0 # 2 USDT жесткой маржи на каждый из 3 ордеров в сетке (Итого риск на сделку 6$)
BINGX_ALTCOIN_MARGIN = 2.0 # 2.0 USDT margin for altcoins
BINGX_ALTCOIN_V9_MIN_SCORE = 80 # Усиленный фильтр для альткоинов V9 >= 80
BINGX_ALTCOIN_MIN_VOLUME = 30000000 # Ликвидность: > 30M USDT суточного объема
BINGX_BTC_TREND_FILTER = True # Включить корреляцию с биткоином
BINGX_MOVE_SL_TO_BREAKEVEN = True # Автоматический перевод Стоп-Лосса в точку входа при достижении 10% ROE
BINGX_FALSE_BREAKOUT_MARGIN = 10.0 # СТРОГО: 10 USDT маржи на сделку
BINGX_LEVERAGE = 15 # Плечо x15 обеспечивает минимальный объем сделки (1$ * 15 = 15$)
BINGX_DAILY_LOSS_LIMIT = 15.0 # Если убыток за день больше 15$, бот прекращает открывать сделки до конца дня
