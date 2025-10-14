import json
import csv
from datetime import datetime
from collections import defaultdict
from services.constants import TRADE_LOG, SIGNALS_LOG, TRADE_STATE, CONFIG, ALERTS_LOG

# Đường dẫn file (có thể refactor cấu hình riêng)
TRADE_LOG = "../../trades_log.csv"
SIGNALS_LOG = "../../signals_log.csv"
TRADE_STATE = "../../trade_state.json"
CONFIG = "../../config.json"
TRADES_SIM_LOG = "../../trades_sim_log.csv"
SCORES_LOG = "../../scores_log.csv"

def safe_load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

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

def get_total_equity():
    # Lấy vốn hiện tại từ trade_state hoặc config
    state = safe_load_json(TRADE_STATE)
    if state and "equity" in state:
        return {"equity": float(state["equity"])}
    config = safe_load_json(CONFIG)
    return {"equity": float(config.get("initial_equity", 0))}

def get_total_pnl():
    # Tổng PnL tích lũy (dựa trên logs mô phỏng/thực)
    trades = safe_load_csv(TRADE_LOG)
    pnl = 0.0
    for t in trades:
        try:
            pnl += float(t.get("pnl", 0))
        except Exception:
            continue
    return {"total_pnl": pnl}

def get_daily_pnl():
    # Tổng hợp PnL theo ngày
    trades = safe_load_csv(TRADE_LOG)
    daily = defaultdict(float)
    for t in trades:
        try:
            dt = t.get("close_time", t.get("timestamp"))
            date = dt.split(" ")[0] if dt else "unknown"
            daily[date] += float(t.get("pnl", 0))
        except Exception:
            continue
    # sort by date
    return [{"date": d, "pnl": daily[d]} for d in sorted(daily.keys())]

def get_overview():
    eq = get_total_equity()
    pnl = get_total_pnl()
    daily = get_daily_pnl()
    state = get_bot_status()
    risk = get_risk_metrics()
    return {
        "equity": eq["equity"],
        "total_pnl": pnl["total_pnl"],
        "last_daily_pnl": daily[-1] if daily else {},
        "status": state,
        "risk_metrics": risk,
    }

def get_bot_status():
    # Đọc trạng thái bot từ trade_state hoặc file trạng thái riêng (có thể mở rộng)
    state = safe_load_json(TRADE_STATE)
    if not state:
        return {"status": "unknown", "detail": "No state file"}
    return {
        "status": state.get("status", "unknown"),
        "last_action": state.get("last_action", ""),
        "open_trades": state.get("open_trades", []),
        "update_time": state.get("update_time", "")
    }

def get_risk_metrics():
    # Winrate, max drawdown,... đơn giản hóa, có thể mở rộng tính toán chuyên sâu hơn
    trades = safe_load_csv(TRADE_LOG)
    total = len(trades)
    win = sum(1 for t in trades if float(t.get("pnl", 0)) > 0)
    loss = total - win
    winrate = (win / total * 100) if total else 0
    # Max drawdown ước tính
    eq = 0
    eqs = []
    for t in trades:
        try:
            eq += float(t.get("pnl", 0))
            eqs.append(eq)
        except Exception:
            continue
    drawdown = 0
    peak = 0
    for x in eqs:
        if x > peak: peak = x
        if peak - x > drawdown: drawdown = peak - x
    return {
        "winrate": winrate,
        "max_drawdown": drawdown,
        "trade_count": total
    }

def get_module_reports():
    # Tổng hợp báo cáo từ các module chính
    # (có thể mở rộng: lấy từ signals_log, scores_log, ... hoặc đọc thêm trạng thái module)
    signals = safe_load_csv(SIGNALS_LOG)
    trades = safe_load_csv(TRADE_LOG)
    # Ví dụ: số lượng tín hiệu, số lệnh thực hiện, lệnh đang mở...
    module = {
        "signals_count": len(signals),
        "total_trades": len(trades),
        "open_trades": [t for t in trades if t.get("status") == "open"],
        "closed_trades": [t for t in trades if t.get("status") == "closed"],
    }
    return module