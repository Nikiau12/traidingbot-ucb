import pandas as pd
from core.config import SPIKE_VOLUME_MULTIPLIER, SPIKE_PRICE_ATR_MULTIPLIER, SPIKE_MIN_PCT_CHANGE

class SpikeScanner:
    def __init__(self, atr_period=14, volume_period=20):
        self.atr_period = atr_period
        self.vol_period = volume_period

    def scan(self, df: pd.DataFrame, ticker: dict = None) -> dict:
        """
        Scans a dataframe of a specific timeframe for volume and price spikes.
        Returns a dict {'is_spike': bool, 'type': 'price'/'volume'/'both', 'direction': 'up'/'down', 'info': str}
        """
        if len(df) < max(self.atr_period, self.vol_period) + 1:
            return None

        # Calculate True Range (TR)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # Calculate ATR (Simple Moving Average of TR for simplicity)
        atr = tr.rolling(window=self.atr_period).mean()

        # Calculate average volume
        avg_vol = df['volume'].rolling(window=self.vol_period).mean()

        last_row = df.iloc[-1]
        prev_atr = atr.iloc[-2]
        prev_avg_vol = avg_vol.iloc[-2]

        is_price_spike = False
        is_vol_spike = False

        # Price spike condition: candle body > ATR * multiplier
        body_size = abs(last_row['close'] - last_row['open'])
        if body_size > (prev_atr * SPIKE_PRICE_ATR_MULTIPLIER):
            is_price_spike = True

        # Volume spike condition: volume > avg_vol * multiplier
        if last_row['volume'] > (prev_avg_vol * SPIKE_VOLUME_MULTIPLIER):
            is_vol_spike = True

        if is_price_spike or is_vol_spike:
            direction = 'up' if last_row['close'] > last_row['open'] else 'down'
            spike_type = 'both' if (is_price_spike and is_vol_spike) else ('price' if is_price_spike else 'volume')
            pct_change = abs((last_row['close'] - last_row['open']) / last_row['open'] * 100)
            
            if pct_change >= SPIKE_MIN_PCT_CHANGE:
                score_data = self._score_spike(
                    df=df,
                    last_row=last_row,
                    prev_atr=prev_atr,
                    prev_avg_vol=prev_avg_vol,
                    pct_change=pct_change,
                    direction=direction,
                    ticker=ticker or {},
                )
                return {
                    'is_spike': True,
                    'type': spike_type,
                    'direction': direction,
                    'pct_change': pct_change,
                    'start_price': last_row['open'],
                    'current_price': last_row['close'],
                    'volume_ratio': last_row['volume'] / prev_avg_vol if prev_avg_vol > 0 else 0,
                    **score_data,
                }
        
        return None

    def _score_spike(self, df, last_row, prev_atr, prev_avg_vol, pct_change, direction, ticker):
        score = 0
        reasons = []
        risk_flags = []

        volume_ratio = last_row['volume'] / prev_avg_vol if prev_avg_vol > 0 else 0
        body_size = abs(last_row['close'] - last_row['open'])
        atr_ratio = body_size / prev_atr if prev_atr > 0 else 0
        quote_volume = self._to_float(ticker.get('quoteVolume') or ticker.get('quote_volume') or 0)

        score += min(30, pct_change * 3)
        if pct_change >= 5:
            reasons.append(f"движение {pct_change:.1f}% за свечу")

        score += min(25, volume_ratio * 4)
        if volume_ratio >= 4:
            reasons.append(f"объем x{volume_ratio:.1f} к среднему")

        score += min(20, atr_ratio * 6)
        if atr_ratio >= 2.5:
            reasons.append(f"свеча x{atr_ratio:.1f} ATR")

        continuation = self._continuation_score(df, direction)
        score += continuation["score"]
        if continuation["reason"]:
            reasons.append(continuation["reason"])

        wick_penalty = self._wick_penalty(last_row, direction)
        score -= wick_penalty["penalty"]
        if wick_penalty["reason"]:
            risk_flags.append(wick_penalty["reason"])

        if quote_volume and quote_volume < 500_000:
            score -= 15
            risk_flags.append("низкая ликвидность 24h")
        elif quote_volume and quote_volume >= 5_000_000:
            score += 10
            reasons.append("ликвидность 24h выше $5M")

        score = max(0, min(100, int(round(score))))
        return {
            "score": score,
            "quality": self._quality_label(score),
            "reasons": reasons[:4],
            "risk_flags": risk_flags[:4],
            "quote_volume": quote_volume,
            "atr_ratio": atr_ratio,
        }

    def _continuation_score(self, df, direction):
        recent = df.tail(4)
        if direction == "up":
            aligned = (recent["close"] > recent["open"]).sum()
            higher_closes = (recent["close"].diff().dropna() > 0).sum()
        else:
            aligned = (recent["close"] < recent["open"]).sum()
            higher_closes = (recent["close"].diff().dropna() < 0).sum()

        points = min(15, aligned * 3 + higher_closes * 2)
        reason = ""
        if aligned >= 3 and higher_closes >= 2:
            reason = "движение подтверждено несколькими свечами"
        return {"score": points, "reason": reason}

    def _wick_penalty(self, row, direction):
        candle_range = row["high"] - row["low"]
        if candle_range <= 0:
            return {"penalty": 0, "reason": ""}

        if direction == "up":
            wick = row["high"] - row["close"]
            label = "длинный верхний фитиль"
        else:
            wick = row["close"] - row["low"]
            label = "длинный нижний фитиль"

        wick_ratio = wick / candle_range
        if wick_ratio >= 0.45:
            return {"penalty": 20, "reason": f"{label}: возможный ложный вынос"}
        if wick_ratio >= 0.30:
            return {"penalty": 10, "reason": f"{label}: часть движения выкупили/продали"}
        return {"penalty": 0, "reason": ""}

    def _quality_label(self, score):
        if score >= 85:
            return "A"
        if score >= 70:
            return "B"
        if score >= 55:
            return "C"
        return "D"

    def _to_float(self, value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0
