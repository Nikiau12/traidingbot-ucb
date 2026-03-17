from enum import Enum
from dataclasses import dataclass, field
from typing import List

class Regime(Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGE = "range"
    COMPRESSION = "compression"
    EXPANSION = "expansion"

class MarketPhase(Enum):
    IMPULSE = "impulse"
    CORRECTION = "correction"
    CONTINUATION = "continuation"
    EXHAUSTION = "exhaustion"
    UNKNOWN = "unknown"

class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"

@dataclass
class CoinProfile:
    symbol: str
    tier: str  # BTC, ETH, MAJOR, HIGH_BETA
    rsi_os_trend: float = 40.0
    rsi_ob_trend: float = 60.0
    rsi_os_range: float = 30.0
    rsi_ob_range: float = 70.0
    atr_mult: float = 1.0

@dataclass
class ContextScore:
    signal: SignalType
    confidence: int  # 0 to 100
    regime: Regime
    phase: MarketPhase
    reasons: List[str] = field(default_factory=list)
