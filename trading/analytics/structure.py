from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import math

@dataclass
class Bar:
    ts: int
    o: float
    h: float
    l: float
    c: float
    v: float

@dataclass
class Swing:
    i: int
    price: float
    kind: str  # "H" or "L"

def swings(bars: List[Bar], left: int = 2, right: int = 2) -> Tuple[List[Swing], List[Swing]]:
    """
    Pivot highs/lows by local window.
    Returns (highs, lows)
    """
    highs: List[Swing] = []
    lows: List[Swing] = []
    n = len(bars)
    if n < left + right + 5:
        return highs, lows

    for i in range(left, n - right):
        h = bars[i].h
        l = bars[i].l
        win_h = max(bars[j].h for j in range(i - left, i + right + 1))
        win_l = min(bars[j].l for j in range(i - left, i + right + 1))
        if h >= win_h:
            highs.append(Swing(i=i, price=h, kind="H"))
        if l <= win_l:
            lows.append(Swing(i=i, price=l, kind="L"))

    return highs, lows

def last_structure_bias(highs: List[Swing], lows: List[Swing]) -> str:
    """
    Very simple structure bias:
      - if last swing high and last swing low are both higher than previous => up
      - if both lower => down
      - else neutral
    """
    if len(highs) < 2 or len(lows) < 2:
        return "neutral"

    h1, h2 = highs[-2].price, highs[-1].price
    l1, l2 = lows[-2].price, lows[-1].price

    if h2 > h1 and l2 > l1:
        return "up"
    if h2 < h1 and l2 < l1:
        return "down"
    return "neutral"

def bos_choch(highs: List[Swing], lows: List[Swing], last_close: float) -> str:
    """
    Minimal BOS/CHOCH signal using last close vs last swing levels:
      - if structure was down and close breaks above last swing high => CHOCH_up
      - if structure was up and close breaks below last swing low => CHOCH_down
      - if close breaks in direction of structure beyond last swing => BOS
    """
    if len(highs) < 2 or len(lows) < 2:
        return "none"

    bias = last_structure_bias(highs, lows)
    lastH = highs[-1].price
    lastL = lows[-1].price

    if bias == "down":
        if last_close > lastH:
            return "CHOCH_up"
        if last_close < lastL:
            return "BOS_down"
    if bias == "up":
        if last_close < lastL:
            return "CHOCH_down"
        if last_close > lastH:
            return "BOS_up"

    # neutral: still can note breaks
    if last_close > lastH:
        return "break_up"
    if last_close < lastL:
        return "break_down"
    return "none"
