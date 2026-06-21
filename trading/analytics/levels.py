from __future__ import annotations
from typing import List, Optional, Tuple
import math

def cluster_levels(prices: List[float], tol: float) -> List[float]:
    """
    Cluster nearby prices into levels by simple tolerance.
    """
    if not prices:
        return []
    xs = sorted(float(x) for x in prices if math.isfinite(float(x)))
    if not xs:
        return []
    clusters: List[List[float]] = [[xs[0]]]
    for x in xs[1:]:
        if abs(x - clusters[-1][-1]) <= tol:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    return [sum(c) / len(c) for c in clusters]

def nearest_levels(levels: List[float], price: float) -> Tuple[Optional[float], Optional[float]]:
    below = [x for x in levels if x <= price]
    above = [x for x in levels if x >= price]
    return (max(below) if below else None, min(above) if above else None)

def midrange_ratio(sup: Optional[float], res: Optional[float], price: float) -> Optional[float]:
    if sup is None or res is None:
        return None
    ds = abs(price - sup)
    dr = abs(res - price)
    if max(ds, dr) <= 0:
        return None
    return min(ds, dr) / max(ds, dr)
