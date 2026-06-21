from __future__ import annotations

import json
import os
import time
from typing import Dict

STATE_PATH = os.path.expanduser("~/.openclaw/trading/bot_state.json")


def _load() -> Dict:
    if not os.path.exists(STATE_PATH):
        return {"alerts": {}}
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"alerts": {}}


def _save(state: Dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def should_send_alert(symbol: str, side: str, conf: float) -> bool:
    prev = _load().get("alerts", {}).get(symbol)
    if prev is None:
        return True
    if prev.get("side") != side:
        return True
    if time.time() - prev.get("ts", 0) > 4 * 3600:
        return True
    if abs(conf - prev.get("conf", 0)) >= 0.10:
        return True
    return False


def mark_sent(symbol: str, side: str, conf: float) -> None:
    state = _load()
    state.setdefault("alerts", {})[symbol] = {
        "side": side,
        "conf": conf,
        "ts": time.time(),
    }
    _save(state)


def get_user_lang(user_id: int) -> str:
    return _load().get("user_langs", {}).get(str(user_id), "en")


def set_user_lang(user_id: int, lang: str) -> None:
    state = _load()
    state.setdefault("user_langs", {})[str(user_id)] = lang
    _save(state)
