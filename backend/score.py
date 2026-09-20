WEIGHTS = {
    "loss_to_profit": 25,
    "eps_up": 15,
    "nocfps_up": 15,
    "nav_up": 10,
    "sales_up": 10,
    "debt_down": 10,
    "price_recovery": 5,
    "volume_confirm": 5,
    "margin_up": 5,
}

def score_stock(row):
    return sum(weight for key, weight in WEIGHTS.items() if row.get(key) is True)

def signal(score):
    if score >= 80:
        return "STRONG"
    if score >= 60:
        return "WATCH"
    return "AVERAGE"

def metric_status(value):
    if value is True:
        return "YES"
    if value is False:
        return "NO"
    return "N/A"
