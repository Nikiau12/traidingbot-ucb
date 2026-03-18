from .models import CoinProfile

def get_coin_profile(symbol: str) -> CoinProfile:
    """
    Returns an adaptive configuration profile for a given coin.
    Top 50 altcoins require different thresholds for RSI and ATR multipliers 
    compared to stable majors like BTC/ETH.
    """
    base = symbol.split('/')[0].replace('USDT', '')
    
    if base == "BTC":
        return CoinProfile(symbol, "BTC", rsi_os_trend=45, rsi_ob_trend=55, rsi_os_range=30, rsi_ob_range=70, atr_mult=1.0)
    elif base == "ETH":
        return CoinProfile(symbol, "ETH", rsi_os_trend=40, rsi_ob_trend=60, rsi_os_range=25, rsi_ob_range=75, atr_mult=1.2)
    elif base in ["SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "MATIC", "SUI", "APT"]:
        return CoinProfile(symbol, "MAJOR", rsi_os_trend=35, rsi_ob_trend=65, rsi_os_range=20, rsi_ob_range=80, atr_mult=1.5)
    else:
        # High Beta / Volatile Top-50 alts / Memecoins
        return CoinProfile(symbol, "HIGH_BETA", rsi_os_trend=30, rsi_ob_trend=70, rsi_os_range=15, rsi_ob_range=85, atr_mult=2.0)
