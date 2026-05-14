import pandas as pd

from core.config import (
    BTC_LONG_ONLY_MODE,
    BTC_MAX_DAILY_ATR_PCT,
    BTC_MIN_RISK_REWARD,
    BTC_REQUIRE_DAILY_UPTREND,
)


def _with_indicators(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    enriched["ema_20"] = enriched["close"].ewm(span=20, adjust=False).mean()
    enriched["ema_50"] = enriched["close"].ewm(span=50, adjust=False).mean()
    enriched["ema_200"] = enriched["close"].ewm(span=200, adjust=False).mean()

    high_low = enriched["high"] - enriched["low"]
    high_close = (enriched["high"] - enriched["close"].shift()).abs()
    low_close = (enriched["low"] - enriched["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    enriched["atr"] = true_range.rolling(14).mean()
    enriched["atr_pct"] = enriched["atr"] / enriched["close"]
    return enriched


def _risk_reward(setup_type: str, entry: float, stop: float, target: float) -> float:
    if setup_type == "LONG":
        risk = entry - stop
        reward = target - entry
    else:
        risk = stop - entry
        reward = entry - target

    if risk <= 0:
        return 0.0
    return reward / risk


def evaluate_btc_setup(setup_type: str, entry: float, stop: float, target: float, df_1d: pd.DataFrame):
    """
    Conservative BTC-only gate for live execution.
    Returns (allowed, reasons, metrics).
    """
    reasons = []
    metrics = {}
    setup_type = setup_type.upper()

    if setup_type == "SHORT" and BTC_LONG_ONLY_MODE:
        return False, ["BTC short blocked by BTC_LONG_ONLY_MODE"], metrics

    if df_1d is None or df_1d.empty or len(df_1d) < 210:
        return False, ["Not enough 1D candles for BTC trend policy"], metrics

    df = _with_indicators(df_1d)
    last = df.iloc[-1]

    close = float(last["close"])
    ema_20 = float(last["ema_20"])
    ema_50 = float(last["ema_50"])
    ema_200 = float(last["ema_200"])
    atr_pct = float(last["atr_pct"])
    rr = _risk_reward(setup_type, float(entry), float(stop), float(target))

    metrics.update({
        "close": close,
        "ema_20": ema_20,
        "ema_50": ema_50,
        "ema_200": ema_200,
        "atr_pct": atr_pct,
        "rr": rr,
    })

    if rr < BTC_MIN_RISK_REWARD:
        reasons.append(f"RR {rr:.2f} below minimum {BTC_MIN_RISK_REWARD:.2f}")

    if atr_pct > BTC_MAX_DAILY_ATR_PCT:
        reasons.append(f"Daily ATR {atr_pct:.2%} above max {BTC_MAX_DAILY_ATR_PCT:.2%}")

    if BTC_REQUIRE_DAILY_UPTREND and setup_type == "LONG":
        if close <= ema_200:
            reasons.append("Daily close is below EMA200")
        if ema_20 <= ema_50:
            reasons.append("Daily EMA20 is not above EMA50")

    if setup_type == "SHORT":
        if close >= ema_200:
            reasons.append("BTC short rejected while daily close is above EMA200")
        if ema_20 >= ema_50:
            reasons.append("BTC short rejected while EMA20 is above EMA50")

    if reasons:
        return False, reasons, metrics

    return True, ["BTC setup passed conservative trend/volatility/RR policy"], metrics
