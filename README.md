# DSE Turnaround Intelligence — LankaBangla FULL

A hosted-friendly Bangladesh DSE turnaround scanner using LankaBangla as the only
external data source.

## Verified LankaBangla sources used

- Data Matrix: https://www.lankabd.com/Home/DataMatrix
- Quarterly Earnings/Event: https://www.lankabd.com/Details/Event
- Latest Earnings: https://www.lankabd.com/Details/GetLatestEarnings
- Price Archive: https://www.lankabd.com/Home/PriceArchive
- Stock Screener: https://www.lankabd.com/Home/StockScreener

## 100-point model

Loss -> Profit 25
EPS improvement 15
NOCFPS/cash-flow improvement 15
NAV improvement 10
Sales increase 10
Debt decrease 10
Price recovery 5
Volume confirmation 5
Margin improvement 5

Missing/unverified values are N/A and receive 0 points. The program never invents data.

## Architecture

LankaBangla -> Collector -> normalized JSON -> scoring engine -> dashboard
                                      -> history

The collector uses public HTML pages and table parsing. It does not invent private
AJAX endpoints. If LankaBangla changes its HTML, the parser logs the issue rather
than fabricating values.

## Local run

Python 3.11+
pip install -r backend/requirements.txt
cd backend
python collector.py
python server.py

Then open http://127.0.0.1:5000

## GitHub Actions

The scheduled workflow runs after the Bangladesh market day on Sunday-Thursday,
commits updated JSON, and GitHub Pages publishes docs/.

## Important

This is a screening/research tool, not investment advice.
