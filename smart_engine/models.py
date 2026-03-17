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

# --- MTF Fusion Models (Phase 11) ---

class MacroBias(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class ActiveBias(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class SetupType(Enum):
    BULLISH_CONTINUATION = "bullish_continuation"
    BEARISH_CONTINUATION = "bearish_continuation"
    CONSTRUCTIVE_PULLBACK = "constructive_pullback"
    BREAKOUT_CONTINUATION = "breakout_continuation"
    COUNTERTREND_BOUNCE = "countertrend_bounce"
    REVERSAL_WATCH = "reversal_watch"
    RANGE_MEAN_REVERSION = "range_mean_reversion"
    NO_TRADE = "no_trade"
    MIXED_CONTEXT = "mixed_context"

class ConfirmationState(Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    ABSENT = "absent"
    CONFLICTING = "conflicting"

class TriggerState(Enum):
    READY = "ready"
    EARLY = "early"
    VALID = "valid"
    WEAK = "weak"
    OVEREXTENDED = "overextended"
    ABSENT = "absent"
    NOISY = "noisy"

@dataclass
class MTFVerdict:
    macro_bias: MacroBias
    active_bias: ActiveBias
    setup_type: SetupType
    confirmation_state: ConfirmationState
    trigger_state: TriggerState
    confidence: int  # 0 to 100
    risk_flags: List[str] = field(default_factory=list)
