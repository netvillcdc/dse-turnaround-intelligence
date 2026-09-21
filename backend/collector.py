import json
import time
from datetime import date, timedelta
from pathlib import Path

import requests

from parsers import parse_data_matrix, parse_event_page, parse_latest_earnings
from score import score_stock, signal

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data" / "stocks.json"
HISTORY = ROOT / "data" / "history.json"
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 DSE-Turnaround-Intelligence/1.0"}

URLS = {
    "matrix": "https://www.lankabd.com/Home/DataMatrix",
    "earnings": "https://www.lankabd.com/Details/GetLatestEarnings",
    "events": "https://www.lankabd.com/Details/Event",
}

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")

def get(url, params=None):
    r = requests.get(url, params=params, headers=HEADERS, timeout=40)
    r.raise_for_status()
    return r.text

def collect():
    today = date.today().isoformat()

    # 1) Current Data Matrix: LTP, sector, volume, EPS, NAV.
    matrix_html = get(URLS["matrix"])
    (RAW / "datamatrix.html").write_text(matrix_html, encoding="utf-8")
    matrix = {x["symbol"]: x for x in parse_data_matrix(matrix_html)}

    # 2) Latest earnings table.
    latest_html = get(URLS["earnings"])
    (RAW / "latest_earnings.html").write_text(latest_html, encoding="utf-8")
    latest = {x["symbol"]: x for x in parse_latest_earnings(latest_html)}

    # 3) Recent quarterly earnings events. Search recent dates because the event page
    # is date-filtered. We intentionally use its documented public URL parameters.
    events = {}
    for days_ago in range(0, 45):
        d = date.today() - timedelta(days=days_ago)
        params = {
            "catName": "Quarterly_Earnings",
            "category": "8",
            "fromDate": d.isoformat(),
            "toDate": d.isoformat(),
            "pageSize": "100",
            "page": "1",
        }
        try:
            html = get(URLS["events"], params=params)
            for x in parse_event_page(html):
                events[x["symbol"]] = x
        except Exception as exc:
            print("event skip", d, str(exc))
        time.sleep(0.15)

    old = {x.get("symbol"): x for x in load_json(DATA, [])}
    symbols = sorted(set(matrix) | set(latest) | set(events))
    rows = []

    for sym in symbols:
        m = matrix.get(sym, {})
        l = latest.get(sym, {})
        e = events.get(sym, {})
        old_row = old.get(sym, {})

        eps = m.get("eps")
        nav = m.get("nav")

        row = {
            "symbol": sym,
            "sector": m.get("sector") or l.get("sector_latest") or old_row.get("sector") or "N/A",
            "ltp": m.get("ltp"),
            "volume": m.get("volume"),
            "turnover": m.get("turnover"),
            "eps": eps if eps is not None else l.get("eps_latest"),
            "nav": nav if nav is not None else l.get("nav_latest"),

            # Event comparison:
            "eps_prev": e.get("eps_event_prev"),
            "nocfps": e.get("nocfps_event"),
            "nocfps_prev": e.get("nocfps_event_prev"),
            "nav_prev": e.get("nav_event_prev"),

            "loss_to_profit": e.get("loss_to_profit"),
            "eps_up": e.get("eps_event_up"),
            "nocfps_up": e.get("nocfps_event_up"),
            "nav_up": e.get("nav_event_up"),

            # These remain N/A until a verified LankaBangla financial-statement source
            # is wired in. Never infer them from unrelated fields.
            "sales_up": None,
            "debt_down": None,
            "price_recovery": None,
            "volume_confirm": None,
            "margin_up": None,

            "updated": today,
            "source": "LankaBangla",
        }

        # Simple volume flag only when a verified prior-volume field exists in the
        # existing normalized record. This is deliberately conservative.
        if m.get("volume") is not None and old_row.get("volume") is not None:
            row["volume_confirm"] = m["volume"] > old_row["volume"]

        row["score"] = score_stock(row)
        row["signal"] = signal(row["score"])
        rows.append(row)

    rows.sort(key=lambda x: (x["score"], x["symbol"]), reverse=True)
    save_json(DATA, rows)

    history = load_json(HISTORY, {})
    history[today] = rows
    save_json(HISTORY, history)

    return rows

if __name__ == "__main__":
    result = collect()
    print("DSE Turnaround Intelligence updated:", len(result), "symbols")
