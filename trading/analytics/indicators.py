from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import math

Number = float

def ema(values: List[Number], length: int, *, return_series: bool = False) -> Tuple[Optional[Number], Optional[List[Number]]]:
    n = len(values)
    if length <= 0 or n == 0:
        return None, ([] if return_series else None)
    if n == 1:
        return values[0], (values[:] if return_series else None)

    alpha = 2.0 / (length + 1.0)
    e = values[0]
    series = [e] if return_series else None
    for x in values[1:]:
        e = alpha * x + (1.0 - alpha) * e
        if series is not None:
            series.append(e)
    return e, series

def rsi(values: List[Number], length: int = 14, *, return_series: bool = False) -> Tuple[Optional[Number], Optional[List[Number]]]:
    n = len(values)
    if n < length + 2:
        return None, ([float("nan")] * n if return_series else None)

    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        ch = values[i] - values[i - 1]
        gains[i] = max(0.0, ch)
        losses[i] = max(0.0, -ch)

    out = [float("nan")] * n
    avg_gain = sum(gains[1:length+1]) / length
    avg_loss = sum(losses[1:length+1]) / length

    def _calc(ag: float, al: float) -> float:
        if al == 0.0:
            return 100.0
        rs = ag / al
        return 100.0 - (100.0 / (1.0 + rs))

    out[length] = _calc(avg_gain, avg_loss)
    for i in range(length + 1, n):
        avg_gain = (avg_gain * (length - 1) + gains[i]) / length
        avg_loss = (avg_loss * (length - 1) + losses[i]) / length
        out[i] = _calc(avg_gain, avg_loss)

    last = out[-1]
    if not math.isfinite(last):
        last = None
    return last, (out if return_series else None)

@dataclass
class OHLC:
    o: float
    h: float
    l: float
    c: float

def atr(ohlc: List[OHLC], length: int = 14, *, return_series: bool = False) -> Tuple[Optional[Number], Optional[List[Number]]]:
    n = len(ohlc)
    if n < length + 2:
        return None, ([float("nan")] * n if return_series else None)

    trs = [float("nan")] * n
    for i in range(1, n):
        h = ohlc[i].h
        l = ohlc[i].l
        pc = ohlc[i - 1].c
        trs[i] = max(h - l, abs(h - pc), abs(l - pc))

    out = [float("nan")] * n
    prev = sum(trs[1:length+1]) / length
    out[length] = prev
    for i in range(length + 1, n):
        prev = (prev * (length - 1) + trs[i]) / length
        out[i] = prev

    last = out[-1]
    if not math.isfinite(last):
        last = None
    return last, (out if return_series else None)

def adx(ohlc: List[OHLC], length: int = 14, *, return_series: bool = False) -> Tuple[Optional[Number], Optional[List[Number]]]:
    """
    Wilder ADX (trend strength). Returns (last, series_or_None).
    """
    n = len(ohlc)
    if n < length * 2 + 5:
        return None, ([float("nan")] * n if return_series else None)

    tr = [0.0] * n
    pdm = [0.0] * n
    mdm = [0.0] * n

    for i in range(1, n):
        up = ohlc[i].h - ohlc[i-1].h
        dn = ohlc[i-1].l - ohlc[i].l
        pdm[i] = up if (up > dn and up > 0) else 0.0
        mdm[i] = dn if (dn > up and dn > 0) else 0.0
        tr[i] = max(
            ohlc[i].h - ohlc[i].l,
            abs(ohlc[i].h - ohlc[i-1].c),
            abs(ohlc[i].l - ohlc[i-1].c),
        )

    # Wilder smoothing
    atr_s = [float("nan")] * n
    pdm_s = [float("nan")] * n
    mdm_s = [float("nan")] * n

    atr_s[length] = sum(tr[1:length+1])
    pdm_s[length] = sum(pdm[1:length+1])
    mdm_s[length] = sum(mdm[1:length+1])

    for i in range(length + 1, n):
        atr_s[i] = atr_s[i-1] - (atr_s[i-1] / length) + tr[i]
        pdm_s[i] = pdm_s[i-1] - (pdm_s[i-1] / length) + pdm[i]
        mdm_s[i] = mdm_s[i-1] - (mdm_s[i-1] / length) + mdm[i]

    pdi = [float("nan")] * n
    mdi = [float("nan")] * n
    dx  = [float("nan")] * n
    for i in range(length, n):
        if atr_s[i] and atr_s[i] > 0:
            pdi[i] = 100.0 * (pdm_s[i] / atr_s[i])
            mdi[i] = 100.0 * (mdm_s[i] / atr_s[i])
            den = pdi[i] + mdi[i]
            dx[i] = 100.0 * abs(pdi[i] - mdi[i]) / den if den > 0 else float("nan")

    adx_s = [float("nan")] * n
    start = length * 2
    if start < n and all(math.isfinite(dx[i]) for i in range(length, start+1)):
        adx_s[start] = sum(dx[length:start+1]) / length
        for i in range(start + 1, n):
            adx_s[i] = ((adx_s[i-1] * (length - 1)) + dx[i]) / length

    last = adx_s[-1]
    if not math.isfinite(last):
        last = None
    return last, (adx_s if return_series else None)

def volatility_regime(atr_last: float, price: float) -> str:
    if price <= 0 or not math.isfinite(price) or not math.isfinite(atr_last):
        return "unknown"
    pct = atr_last / price
    if pct < 0.003:
        return "quiet"
    if pct > 0.012:
        return "wild"
    return "normal"
