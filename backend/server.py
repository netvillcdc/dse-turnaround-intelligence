from flask import Flask, jsonify, send_from_directory
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
app = Flask(__name__, static_folder=str(ROOT / "docs"), static_url_path="")

@app.get("/api/health")
def health():
    return jsonify({"ok": True})

@app.get("/api/stocks")
def stocks():
    path = ROOT / "docs" / "data" / "stocks.json"
    return jsonify(json.loads(path.read_text(encoding="utf-8")))

@app.get("/")
def index():
    return send_from_directory(ROOT / "docs", "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
