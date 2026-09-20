import re
from bs4 import BeautifulSoup

NUM = r"\(?-?\d+(?:,\d{3})*(?:\.\d+)?\)?"

def clean_num(value):
    if value is None:
        return None
    value = value.strip().replace(",", "")
    if value in ("", "-", "—", "N/A", "NA"):
        return None
    negative = value.startswith("(") and value.endswith(")")
    value = value.strip("()")
    try:
        n = float(value)
        return -n if negative else n
    except ValueError:
        return None

def norm_header(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())

def tables(html):
    soup = BeautifulSoup(html, "html.parser")
    result = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th","td"])]
            if cells:
                rows.append(cells)
        if rows:
            result.append(rows)
    return result

def find_column(headers, *names):
    normalized = [norm_header(h) for h in headers]
    wanted = [norm_header(n) for n in names]
    for w in wanted:
        for i, h in enumerate(normalized):
            if w == h or w in h or h in w:
                return i
    return None

def parse_data_matrix(html):
    out = []
    for rows in tables(html):
        if len(rows) < 2:
            continue
        headers = rows[0]
        symbol_i = find_column(headers, "Symbol")
        sector_i = find_column(headers, "Sector")
        ltp_i = find_column(headers, "LTP")
        volume_i = find_column(headers, "Volume(Qty)", "Volume")
        turnover_i = find_column(headers, "Value(Turnover)", "Turnover")
        eps_i = find_column(headers, "EPS")
        nav_i = find_column(headers, "NAV(Quarter End)", "NAV")
        if symbol_i is None or eps_i is None or nav_i is None:
            continue
        for row in rows[1:]:
            if len(row) <= max(symbol_i, eps_i, nav_i):
                continue
            symbol = row[symbol_i].strip().upper()
            if not re.fullmatch(r"[A-Z0-9&.\-]{1,20}", symbol):
                continue
            def cell(i):
                return row[i] if i is not None and i < len(row) else None
            out.append({
                "symbol": symbol,
                "sector": cell(sector_i) or "N/A",
                "ltp": clean_num(cell(ltp_i)),
                "volume": clean_num(cell(volume_i)),
                "turnover": clean_num(cell(turnover_i)),
                "eps": clean_num(cell(eps_i)),
                "nav": clean_num(cell(nav_i)),
            })
        if out:
            break
    return out

def extract_pair(text, label_pattern):
    p = re.search(
        label_pattern + r".{0,220}?Tk\.\s*(" + NUM + r").{0,120}?"
        r"(?:as against|against)\s+(?:Adjusted\s+)?EPS?\s*(?:was\s*)?Tk\.\s*(" + NUM + r")",
        text, re.I | re.S
    )
    if not p:
        p = re.search(
            label_pattern + r".{0,220}?Tk\.\s*(" + NUM + r").{0,120}?as against\s+Tk\.\s*(" + NUM + r")",
            text, re.I | re.S
        )
    if not p:
        return None, None
    return clean_num(p.group(1)), clean_num(p.group(2))

def parse_event_text(text, symbol):
    eps, eps_prev = extract_pair(
        text, r"(?:Basic and Diluted |Consolidated |Diluted )?EPS"
    )
    nocfps, nocfps_prev = extract_pair(
        text, r"(?:Consolidated )?NOCF(?:PS|PU)"
    )
    nav, nav_prev = extract_pair(
        text, r"(?:Consolidated )?NAV per (?:share|unit)"
    )

    return {
        "symbol": symbol.upper(),
        "eps_event": eps,
        "eps_event_prev": eps_prev,
        "nocfps_event": nocfps,
        "nocfps_event_prev": nocfps_prev,
        "nav_event": nav,
        "nav_event_prev": nav_prev,
        "eps_event_up": eps is not None and eps_prev is not None and eps > eps_prev,
        "nocfps_event_up": nocfps is not None and nocfps_prev is not None and nocfps > nocfps_prev,
        "nav_event_up": nav is not None and nav_prev is not None and nav > nav_prev,
        "loss_to_profit": eps is not None and eps_prev is not None and eps > 0 and eps_prev <= 0,
    }

def parse_event_page(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    found = []
    # LankaBangla renders entries as SYMBOL: Quarterly Earnings...
    matches = list(re.finditer(
        r"\b([A-Z][A-Z0-9&.\-]{1,19}):\s+(?:Quarterly Earnings|Dividend|Annual General Meeting)",
        text
    ))
    for i, m in enumerate(matches):
        symbol = m.group(1)
        start = m.start()
        end = matches[i+1].start() if i+1 < len(matches) else min(len(text), start + 5000)
        chunk = text[start:end]
        if "Quarterly Earnings" in chunk:
            found.append(parse_event_text(chunk, symbol))
    unique = {}
    for row in found:
        unique[row["symbol"]] = row
    return list(unique.values())

def parse_latest_earnings(html):
    out = []
    for rows in tables(html):
        if len(rows) < 2:
            continue
        headers = rows[0]
        sym_i = find_column(headers, "Symbol")
        sector_i = find_column(headers, "Sector")
        year_i = find_column(headers, "Year")
        period_i = find_column(headers, "Annual/Quarter")
        eps_i = find_column(headers, "EPS/EPU")
        nav_i = find_column(headers, "NAV")
        if sym_i is None or eps_i is None or nav_i is None:
            continue
        for row in rows[1:]:
            if len(row) <= max(sym_i, eps_i, nav_i):
                continue
            sym = row[sym_i].strip().upper()
            if not re.fullmatch(r"[A-Z0-9&.\-]{1,20}", sym):
                continue
            def c(i):
                return row[i] if i is not None and i < len(row) else None
            out.append({
                "symbol": sym,
                "sector_latest": c(sector_i) or "N/A",
                "earnings_year": c(year_i),
                "earnings_period": c(period_i),
                "eps_latest": clean_num(c(eps_i)),
                "nav_latest": clean_num(c(nav_i)),
            })
        if out:
            break
    return out
