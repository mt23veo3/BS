import csv
from collections import defaultdict
from services.constants import TRADE_LOG, SIGNALS_LOG, TRADE_STATE, CONFIG, ALERTS_LOG

TRADE_LOG = "../../trades_log.csv"

def safe_load_csv(path):
    result = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                result.append(row)
    except Exception:
        pass
    return result

def get_pnl_summary():
    trades = safe_load_csv(TRADE_LOG)
    total = sum(float(t.get("pnl", 0)) for t in trades)
    win = sum(1 for t in trades if float(t.get("pnl", 0)) > 0)
    loss = sum(1 for t in trades if float(t.get("pnl", 0)) < 0)
    count = len(trades)
    return {
        "total_pnl": total,
        "win_count": win,
        "loss_count": loss,
        "trade_count": count,
        "winrate": (win / count * 100) if count else 0,
    }

def get_pnl_by_day():
    trades = safe_load_csv(TRADE_LOG)
    by_day = defaultdict(float)
    for t in trades:
        dt = t.get("close_time") or t.get("timestamp") or ""
        date = dt.split(" ")[0] if dt else "unknown"
        by_day[date] += float(t.get("pnl", 0))
    return [{"date": d, "pnl": by_day[d]} for d in sorted(by_day.keys())]

def get_pnl_by_symbol():
    trades = safe_load_csv(TRADE_LOG)
    by_symbol = defaultdict(float)
    for t in trades:
        symbol = t.get("symbol", "unknown")
        by_symbol[symbol] += float(t.get("pnl", 0))
    return [{"symbol": s, "pnl": by_symbol[s]} for s in by_symbol.keys()]

def get_pnl_chart():
    return get_pnl_by_day()