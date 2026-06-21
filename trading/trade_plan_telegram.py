#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import Dict

import trade_plan as core
from telegram_render import render_telegram_plan

def parse_kv(argv) -> Dict[str, str]:
    out = {}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            out[k.strip()] = v.strip()
    return out

def main() -> int:
    if len(sys.argv) < 2:
        print("usage: trade_plan_telegram.py SYMBOL deposit=3000 risk=1 lev=20 margin=cross", file=sys.stderr)
        return 2

    symbol = sys.argv[1]
    kv = parse_kv(sys.argv[2:])

    deposit = float(kv.get("deposit", "3000"))
    risk_pct = float(kv.get("risk", "1"))
    lev = float(kv.get("lev", "20"))
    margin = kv.get("margin", "cross")

    snapshot = core.load_snapshot(symbol)
    plan = core.make_plan(snapshot, deposit=deposit, risk_pct=risk_pct, lev=lev, margin=margin)

    msg = render_telegram_plan(plan, deposit=deposit, risk_pct=risk_pct)
    print(msg)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
