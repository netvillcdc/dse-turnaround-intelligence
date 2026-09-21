from __future__ import annotations
from typing import Any, Dict, Optional

WEIGHTS = {
    "loss_to_profit": 25,
    "eps": 15,
    "nocfps": 15,
    "nav": 10,
    "sales": 10,
    "debt": 10,
    "price": 5,
    "volume": 5,
    "margin": 5,
}

def _num(v):
    try:
        if v is None or v == "" or v == "-":
            return None
        return float(v)
    except Exception:
        return None

def direction(current, previous):
    c, p = _num(current), _num(previous)
    if c is None or p is None:
        return "N/A"
    if p == 0:
        return "NEW" if c > 0 else ("UNCHANGED" if c == 0 else "WORSE")
    pct = (c - p) / abs(p) * 100
    if pct > 0.5: return "UP"
    if pct < -0.5: return "DOWN"
    return "FLAT"

def pct_change(current, previous):
    c, p = _num(current), _num(previous)
    if c is None or p is None or p == 0:
        return None
    return round((c-p)/abs(p)*100, 2)

def analyze(m: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evidence-first turnaround engine.
    Every factor can be YES/NO/MIXED/N/A. N/A is never silently treated as YES.
    """
    f = {}
    reasons = []
    flags = []

    # Loss -> Profit is the strongest turnaround event.
    lp = m.get("loss_to_profit")
    if isinstance(lp, bool):
        f["loss_to_profit"] = "YES" if lp else "NO"
    else:
        eps_cur, eps_prev = _num(m.get("eps_current")), _num(m.get("eps_previous"))
        if eps_cur is not None and eps_prev is not None:
            if eps_cur > 0 and eps_prev <= 0:
                f["loss_to_profit"] = "YES"
            elif eps_cur > 0:
                f["loss_to_profit"] = "NO"
            else:
                f["loss_to_profit"] = "NO"
        else:
            f["loss_to_profit"] = "N/A"

    # Numeric trend factors.
    for key, cur, prev in [
        ("eps", m.get("eps_current"), m.get("eps_previous")),
        ("nocfps", m.get("nocfps_current"), m.get("nocfps_previous")),
        ("nav", m.get("nav_current"), m.get("nav_previous")),
        ("sales", m.get("sales_current"), m.get("sales_previous")),
        ("debt", m.get("debt_current"), m.get("debt_previous")),
        ("margin", m.get("margin_current"), m.get("margin_previous")),
    ]:
        d = direction(cur, prev)
        if d == "UP":
            f[key] = "UP"
        elif d == "DOWN":
            f[key] = "DOWN"
        elif d == "FLAT":
            f[key] = "FLAT"
        else:
            f[key] = "N/A"

    # Debt: lower is positive; higher is negative.
    debt = f["debt"]
    if debt == "UP":
        f["debt"] = "DOWN"
    elif debt == "DOWN":
        f["debt"] = "UP"

    # Price: use verified return/recovery input, not an invented number.
    pr = _num(m.get("price_recovery_pct"))
    f["price"] = "UP" if pr is not None and pr > 5 else ("DOWN" if pr is not None and pr < -5 else ("FLAT" if pr is not None else "N/A"))

    # Volume confirmation requires both positive price direction and stronger volume.
    vr = _num(m.get("volume_change_pct"))
    f["volume"] = "YES" if pr is not None and pr > 0 and vr is not None and vr > 10 else ("NO" if pr is not None and vr is not None else "N/A")

    points = {}
    positive = {
        "loss_to_profit": f["loss_to_profit"] == "YES",
        "eps": f["eps"] == "UP",
        "nocfps": f["nocfps"] == "UP",
        "nav": f["nav"] == "UP",
        "sales": f["sales"] == "UP",
        "debt": f["debt"] == "UP",
        "price": f["price"] == "UP",
        "volume": f["volume"] == "YES",
        "margin": f["margin"] == "UP",
    }
    for k, w in WEIGHTS.items():
        points[k] = w if positive[k] else 0

    verified = 0
    for k in WEIGHTS:
        if f[k] != "N/A":
            verified += 1
    coverage = round(verified / len(WEIGHTS) * 100)

    score = sum(points.values())

    # Contradictions / quality flags.
    if f["loss_to_profit"] == "YES":
        reasons.append("Earnings crossed from loss to profit.")
    elif f["loss_to_profit"] == "N/A":
        flags.append("Loss→Profit evidence unavailable.")
    if f["eps"] == "UP": reasons.append("EPS improved versus the comparison period.")
    if f["nocfps"] == "UP": reasons.append("Operating cash flow (NOCFPS) improved.")
    if f["nav"] == "UP": reasons.append("NAV improved.")
    if f["sales"] == "UP": reasons.append("Sales/income improved.")
    if f["debt"] == "UP": reasons.append("Debt burden improved.")
    if f["margin"] == "UP": reasons.append("Margin improved.")
    if f["price"] == "UP": reasons.append("Price recovery is positive.")
    if f["volume"] == "YES": reasons.append("Price recovery has volume confirmation.")
    if f["eps"] == "DOWN" and f["loss_to_profit"] == "YES":
        flags.append("Profitability improved, but EPS has a conflicting trend input.")
    if f["nocfps"] == "DOWN":
        flags.append("Cash flow is not confirming the earnings improvement.")
    if f["nav"] == "DOWN":
        flags.append("NAV is deteriorating.")
    if f["debt"] == "DOWN":
        flags.append("Debt burden is rising.")
    if coverage < 56:
        flags.append("Low evidence coverage; score is incomplete.")

    # Classification is descriptive, not a buy/sell recommendation.
    if f["loss_to_profit"] == "YES" and f["nocfps"] == "UP" and coverage >= 56:
        label = "STRONG TURNAROUND"
    elif f["loss_to_profit"] == "YES" and coverage >= 44:
        label = "TURNAROUND"
    elif f["eps"] == "UP" and f["nocfps"] == "UP":
        label = "CASH-FLOW / EARNINGS IMPROVEMENT"
    elif f["eps"] == "UP" or f["nav"] == "UP":
        label = "EARLY IMPROVEMENT"
    elif score >= 50:
        label = "WATCH — MIXED EVIDENCE"
    else:
        label = "WEAK / NOT CONFIRMED"

    return {
        "score": score,
        "coverage": coverage,
        "label": label,
        "factors": f,
        "points": points,
        "reasons": reasons,
        "flags": flags,
    }
