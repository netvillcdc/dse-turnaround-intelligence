from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, re, requests
from bs4 import BeautifulSoup
from score import analyze

ROOT = Path(__file__).resolve().parents[1]
DOCS_DATA = ROOT / "docs" / "data"
RAW = ROOT / "data" / "raw"
DOCS_DATA.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Turnaround-Engine/2.0)"}
TIMEOUT = 25

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def clean(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()

def num(v):
    try:
        s = clean(v).replace(",", "")
        if s in ("", "-", "N/A", "n/a"):
            return None
        return float(re.sub(r"[^0-9.\-]", "", s))
    except Exception:
        return None

def tables(html):
    soup = BeautifulSoup(html, "html.parser")
    out=[]
    for table in soup.find_all("table"):
        rows=[]
        for tr in table.find_all("tr"):
            cells=[clean(x.get_text(" ", strip=True)) for x in tr.find_all(["th","td"])]
            if cells: rows.append(cells)
        if len(rows)>=2: out.append(rows)
    return out

def matrix():
    html = get("https://www.lankabd.com/Home/DataMatrix")
    (RAW/"datamatrix.html").write_text(html, encoding="utf-8")
    result=[]
    for t in tables(html):
        header=[x.lower() for x in t[0]]
        if not any("symbol" in x for x in header): continue
        idx={h:i for i,h in enumerate(header)}
        for row in t[1:]:
            if not row or not row[0]: continue
            def col(*names):
                for n in names:
                    for h,i in idx.items():
                        if n in h and i < len(row): return row[i]
                return None
            result.append({
                "symbol": col("symbol") or row[0],
                "sector": col("sector"),
                "ltp": num(col("ltp")),
                "volume": num(col("volume")),
                "turnover": num(col("turnover")),
                "eps_current": num(col("eps")),
                "nav_current": num(col("nav")),
            })
        if result: break
    return result

def latest_earnings():
    html = get("https://lankabd.com/Details/GetLatestEarnings")
    (RAW/"latest_earnings.html").write_text(html, encoding="utf-8")
    result={}
    for t in tables(html):
        h=[x.lower() for x in t[0]]
        idx={x:i for i,x in enumerate(h)}
        if not any("symbol" in x for x in h): continue
        for row in t[1:]:
            if len(row)<2: continue
            def c(*names):
                for n in names:
                    for hh,i in idx.items():
                        if n in hh and i<len(row): return row[i]
                return None
            sym=c("symbol")
            if sym: result[sym]={"eps":num(c("eps","epu")),"nav":num(c("nav")),"period":c("year")}
        if result: break
    return result

def event_history(days=120):
    events={}
    today=datetime.now(timezone.utc).date()
    for d in range(days):
        day=today-timedelta(days=d)
        url=f"https://lankabd.com/Details/Event?catName=Quarterly_Earnings&category=8&fromDate={day}&toDate={day}"
        try: html=get(url)
        except Exception: continue
        (RAW/f"earnings_{day}.html").write_text(html, encoding="utf-8")
        soup=BeautifulSoup(html,"html.parser")
        text=clean(soup.get_text(" ", strip=True))
        # Keep page-level evidence. Exact structured extraction depends on the portal's current HTML.
        # The dashboard will not invent values if structured comparisons are not exposed.
        for m in re.finditer(r"\b([A-Z][A-Z0-9&.\-]{2,})\b", text):
            sym=m.group(1)
            if sym not in events:
                events[sym]={"evidence_date":str(day)}
    return events

def main():
    rows=matrix()
    earnings=latest_earnings()
    event_hist=event_history()
    out=[]
    for r in rows:
        sym=r["symbol"]
        e=earnings.get(sym,{})
        m={
            "eps_current": r.get("eps_current") if r.get("eps_current") is not None else e.get("eps"),
            "eps_previous": None,
            "nocfps_current": None, "nocfps_previous": None,
            "nav_current": r.get("nav_current") if r.get("nav_current") is not None else e.get("nav"),
            "nav_previous": None,
            "sales_current": None, "sales_previous": None,
            "debt_current": None, "debt_previous": None,
            "margin_current": None, "margin_previous": None,
            "price_recovery_pct": None, "volume_change_pct": None,
            "loss_to_profit": None,
        }
        result=analyze(m)
        out.append({
            **r,
            "analysis": result,
            "evidence": {
                "latest_earnings": e,
                "quarterly_event_found": sym in event_hist,
                "note": "Only verified structured values are scored. Missing comparisons remain N/A."
            },
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    payload={
        "engine":"Turnaround Engine v2",
        "source":"LankaBangla",
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "methodology":"Evidence-first; missing metrics are N/A and do not receive points.",
        "stocks":out
    }
    (DOCS_DATA/"stocks.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Saved {len(out)} stocks")

if __name__=="__main__":
    main()
