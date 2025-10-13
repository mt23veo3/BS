# -*- coding: utf-8 -*-
"""
Main loop PRE -> PROBE -> FULL
Chống spam cảnh báo đóng lệnh: mỗi lệnh chỉ gửi đề xuất đóng lệnh khi lý do thay đổi hoặc lệnh mới.
"""

import argparse
import asyncio
import json
import signal
import time
from datetime import datetime
from typing import Dict, Any, Tuple

import pandas as pd
import csv
import os

from data import fetch_data
from indicators import calculate_indicators
from tight_gate import build_indicator_results, StablePassTracker, _heavy_hits
from votes import tally_votes
from notifier import Notifier
from order_planner import plan_probe_and_topup
from config import SIGNAL_MONITOR_CONFIG
from signal_manager import SignalMonitor
from trade_simulator import TradeSimulator
from utils import log_latency, log_score

import unicodedata

CONFIG_PATH = "config.json"

SENT_SIDE: Dict[Tuple[str, str], Dict] = {}
PRE_STATE: Dict[str, Dict[str, Any]] = {}

monitor = SignalMonitor(SIGNAL_MONITOR_CONFIG)
simulator = TradeSimulator(capital=100.0, leverage=10, fee_bps=4)
stable_tracker = StablePassTracker(path="tight_state.json", min_gap_sec=30, required_passes=2)

COOLDOWN_M15: Dict[str, float] = {}

PROBE_M5_COUNT = 3
PROBE_INDICATOR_PCT = 90

MAX_HOLD_M15 = 12
WEAK_ADX = 16
WEAK_RSI_RANGE = (45, 55)

LEVERAGE = 10

CLOSE_WARNED = {}

SPAM_PROBE_WARNED = {}
TRAILING_STEPS = [
    {"roi": 0.03, "lock": 0.002},   # trailing stop 0.2% tại ROI 3%
]
LAST_CLOSE_TIME = {}

def safe_float_fmt(val, digits=4, default=""):
    try:
        if val is None or (hasattr(pd, "isnull") and pd.isnull(val)):
            return default
        return f"{round(float(val), digits)}"
    except Exception:
        return default

def normalize_symbol(symbol: str) -> str:
    return symbol.replace("/", "").replace("_", "").upper()

def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def decide_side(score_long: float, score_short: float, eps: float = 0.1) -> str:
    if score_long - score_short > eps: return "LONG"
    if score_short - score_long > eps: return "SHORT"
    return "NEUTRAL"

def check_indicator_input(df, min_required, label):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < min_required:
        print(f"[WARN] {label}: DataFrame qua nho ({len(df) if df is not None else 0}) can >= {min_required}")
        return False
    return True

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def log_reason_vi_no_accent(log_dict):
    out = {}
    for k, v in log_dict.items():
        if isinstance(v, str):
            out[k] = remove_accents(v)
        elif isinstance(v, dict):
            out[k] = v
        else:
            out[k] = v
    fn = "entries_reasons.csv"
    fieldnames = list(out.keys())
    write_header = not os.path.exists(fn)
    with open(fn, 'a', encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(out)

def should_send_new_entry(symbol, timeframe, direction, entry, sl, tp, min_interval_min=15, min_entry_diff_pct=0.3):
    key = (normalize_symbol(symbol), timeframe)
    now = time.time()
    last = SENT_SIDE.get(key)
    warning_text = None
    if last:
        last_side = last.get("side")
        if last_side != direction:
            warning_text = f"🚨 **CẢNH BÁO: ĐẢO CHIỀU** {symbol} {timeframe} từ {last_side} sang {direction}"
        elif last_side == direction:
            last_ts = last.get("ts", 0)
            if now - last_ts < min_interval_min * 60:
                print(f"[SENT_SIDE] Bỏ qua tín hiệu do đang trong timeout {min_interval_min} phút")
                return False, None
            last_entry = last.get("entry", entry)
            last_sl = last.get("sl", sl)
            last_tp = last.get("tp", tp)
            entry_diff_pct = abs((entry or 0) - (last_entry or 0)) / max(abs(entry or 0), 1) * 100
            sl_diff_pct = abs((sl or 0) - (last_sl or 0)) / max(abs(sl or 0), 1) * 100
            tp_diff_pct = abs((tp or 0) - (last_tp or 0)) / max(abs(tp or 0), 1) * 100
            if entry_diff_pct < min_entry_diff_pct and sl_diff_pct < min_entry_diff_pct and tp_diff_pct < min_entry_diff_pct:
                print(f"[SENT_SIDE] Bỏ qua tín hiệu do entry/sl/tp lệch quá nhỏ (entry {entry_diff_pct:.4f}%, sl {sl_diff_pct:.4f}%, tp {tp_diff_pct:.4f}%) < {min_entry_diff_pct}%")
                return False, None
    SENT_SIDE[key] = {"side": direction, "ts": now, "entry": entry, "sl": sl, "tp": tp}
    print(f"[SENT_SIDE] Gửi tín hiệu mới: {symbol} {direction} entry={entry}, sl={sl}, tp={tp}")
    return True, warning_text

def mark_closed_entry(symbol, timeframe, direction):
    key = (normalize_symbol(symbol), timeframe)
    SENT_SIDE.pop(key, None)

def is_data_fresh(df, tf_min, symbol, tf_name, max_lag_n=2):
    if df is None or df.empty:
        print(f"[ERROR] DataFrame {symbol} {tf_name} rỗng!")
        return False
    last_ts = None
    if 'timestamp' in df.columns:
        last_ts = df['timestamp'].iloc[-1]
    elif hasattr(df.index, "astype"):
        try:
            last_ts = int(df.index[-1].timestamp())
        except Exception:
            pass
    if last_ts is None:
        print(f"[ERROR] Không lấy được timestamp {symbol} {tf_name}.")
        return False
    now = time.time()
    lag = now - last_ts
    max_lag = tf_min * 60 * max_lag_n
    if lag > max_lag:
        print(f"[ERROR] Dữ liệu {symbol} {tf_name} QUÁ CŨ! Lệch {lag/60:.1f} phút (> {max_lag/60:.1f} phút)")
        return False
    try:
        last_price = float(df['close'].iloc[-1])
        print(f"[DATA_CHECK] {symbol} {tf_name} | last price: {last_price} | last ts: {datetime.fromtimestamp(last_ts)} | now: {datetime.fromtimestamp(now)} | lag: {lag:.1f}s")
    except Exception:
        pass
    return True

def snapshot_m5_confirmed(side_m15, m5, ind_m5, count=PROBE_M5_COUNT):
    if m5 is None or len(m5) < count:
        return False
    votes = []
    for i in range(-count, 0):
        side = None
        try:
            sl = float(ind_m5['score_long'].iloc[i]) if hasattr(ind_m5['score_long'], 'iloc') else 0
            ss = float(ind_m5['score_short'].iloc[i]) if hasattr(ind_m5['score_short'], 'iloc') else 0
            side = decide_side(sl, ss)
        except Exception:
            pass
        votes.append(side)
    return all([v == side_m15 for v in votes])

def strong_indicator_confirmed(vote_result, side, threshold_pct=PROBE_INDICATOR_PCT):
    if vote_result is None or side == "NEUTRAL":
        return False
    total = (vote_result.get('votes_long', 0) or 0) + (vote_result.get('votes_short', 0) or 0)
    if total == 0:
        return False
    if side == "LONG":
        pct = 100 * (vote_result.get('votes_long', 0) or 0) / total
    else:
        pct = 100 * (vote_result.get('votes_short', 0) or 0) / total
    return pct >= threshold_pct

def should_suggest_close(active_trade, newest_side, ind_m15, adx_val, rsi_val, now_epoch):
    reason = None
    symbol = active_trade.get("symbol", "")
    direction = active_trade.get("direction", "")
    entry = active_trade.get("entry", 0)
    sl = active_trade.get("sl", 0)
    tp = active_trade.get("tp", 0)
    open_ts = active_trade.get("time_open", active_trade.get("open_ts",0))
    pnl = active_trade.get("result", 0)
    hold_m15 = int((now_epoch - open_ts) // (15*60)) if open_ts else 0
    if newest_side != direction and newest_side in ("LONG", "SHORT"):
        reason = f"ĐẢO CHIỀU sang {newest_side}"
    elif adx_val is not None and adx_val < WEAK_ADX:
        reason = "Momentum yếu (ADX↓)"
    elif rsi_val is not None and WEAK_RSI_RANGE[0] <= rsi_val <= WEAK_RSI_RANGE[1]:
        reason = "RSI trung tính (không trend)"
    elif hold_m15 is not None and hold_m15 > MAX_HOLD_M15:
        reason = f"Giữ lệnh quá lâu ({hold_m15} nến M15)"
    if reason:
        content = (
            f"🚨🚨🚨 **ĐỀ XUẤT ĐÓNG LỆNH NGAY [{symbol}]** 🚨🚨🚨\n"
            f"**LÝ DO:** {reason}\n"
            f"**CHIỀU:** {direction} | **ENTRY:** {safe_float_fmt(entry)} | **SL:** {safe_float_fmt(sl)} | **TP:** {safe_float_fmt(tp)}\n"
            f"**ĐANG GIỮ:** {hold_m15} nến M15 | **PnL:** {safe_float_fmt(pnl,2)}\n"
            f"👉 _HÃY XEM LẠI LỆNH & CÂN NHẮC ĐÓNG LỆNH NGAY!_"
        )
        return True, reason, content
    return False, None, None

def is_breakout_candle(df, ind, ma_col="ema200", volume_col="volume", direction="LONG"):
    if df is None or ind is None or len(df) < 20:
        return False
    atr = ind.get('atr', pd.Series([0]*len(df)))
    atr_val = float(atr.iloc[-1]) if hasattr(atr, "iloc") else float(atr[-1]) if isinstance(atr, (list, tuple)) else 0
    body = abs(df['close'].iloc[-1] - df['open'].iloc[-1])
    vol = df[volume_col].iloc[-1]
    avg_vol = df[volume_col].rolling(20).mean().iloc[-1]
    close = df['close'].iloc[-1]
    ma = ind.get(ma_col, pd.Series([0]*len(df)))
    ma_val = float(ma.iloc[-1]) if hasattr(ma, "iloc") else float(ma[-1]) if isinstance(ma, (list, tuple)) else 0
    if direction == "LONG":
        breakout_body = (df['close'].iloc[-1] - df['open'].iloc[-1]) > 1.2 * atr_val if atr_val > 0 else False
        breakout_vol = vol > 1.5 * avg_vol if avg_vol > 0 else False
        breakout_close = close > ma_val if ma_val > 0 else False
        return breakout_body and breakout_vol and breakout_close
    else:
        breakout_body = (df['open'].iloc[-1] - df['close'].iloc[-1]) > 1.2 * atr_val if atr_val > 0 else False
        breakout_vol = vol > 1.5 * avg_vol if avg_vol > 0 else False
        breakout_close = close < ma_val if ma_val > 0 else False
        return breakout_body and breakout_vol and breakout_close

def get_open_trades(symbol, direction=None, stage=None):
    trades = []
    for t in simulator.get_all_trades():
        if t.get("symbol") == symbol and t.get("time_close") is None:
            if direction is not None and t.get("direction") != direction: continue
            if stage is not None and t.get("stage") != stage: continue
            trades.append(t)
    return trades

def update_trailing_stop(trade, price_now):
    if "trailing_applied" not in trade:
        trade["trailing_applied"] = set()
    entry = trade.get("entry")
    direction = trade.get("direction")
    if entry is None or direction is None:
        return
    roi_now = ((price_now or 0) - (entry or 0)) / (entry or 1) if direction == "LONG" else ((entry or 0) - (price_now or 0)) / (entry or 1)
    for step in TRAILING_STEPS:
        roi_level = step["roi"]
        if roi_now is not None and roi_level is not None and roi_now >= roi_level and roi_level not in trade["trailing_applied"]:
            lock = step["lock"]
            if direction == "LONG":
                new_sl = max(trade.get("sl", -1e20) or -1e20, (entry or 0) + lock * (entry or 0))
            else:
                new_sl = min(trade.get("sl", 1e20) or 1e20, (entry or 0) - lock * (entry or 0))
            trade["sl"] = round(new_sl, 6)
            trade["trailing_applied"].add(roi_level)

LAST_CLOSE_TIME = {}  # {symbol: last_close_ts}

async def run_once(cfg: Dict[str, Any], notifier: Notifier):
    now_epoch = time.time()
    th_m15 = float((cfg.get("thresholds") or {}).get("M15", 15.0))
    th_h1 = float((cfg.get("thresholds") or {}).get("H1", 8.0))
    heavy_required = int(cfg.get("tight_mode", {}).get("heavy_required", 3))
    snapshot_conf_normal = int(cfg.get("tight_mode", {}).get("snapshot_confirmations", 2))
    cooldown_min = int(cfg.get("tight_mode", {}).get("cooldown_m15_min", 5))
    symbols = cfg.get("symbols", ["BTC/USDT"])
    w_m15 = (cfg.get("weights_sets") or {}).get("M15", {})
    w_h1 = (cfg.get("weights_sets") or {}).get("H1", {})

    PROBE_PCT = float((cfg.get("trading", {}) or {}).get("probe_pct", 0.1))
    FULL_PCT = float((cfg.get("trading", {}) or {}).get("full_pct", 0.5))
    min_notional = float((cfg.get("risk", {}) or {}).get("min_notional", 5.0))

    PROBE_EARLY_SIZE_RATIO = cfg.get("probe_early_size_ratio", 0.08)
    PROMOTE_PULLBACK_ATR = cfg.get("promote_pullback_atr", 0.5)
    AUTO_CLOSE_ON_WARNING_IF_PNL_POS = cfg.get("auto_close_on_warning_if_pnl_positive", True)

    h1_keys = set([k.upper() for k in w_h1.keys()])

    for symbol in symbols:
        cooldown_period = 15 * 60  # 1 nến M15
        if symbol in LAST_CLOSE_TIME and time.time() - LAST_CLOSE_TIME[symbol] < cooldown_period:
            print(f"[COOLDOWN] {symbol}: Chờ 1 nến M15 sau khi vừa đóng lệnh. Bỏ qua tín hiệu mới.")
            continue

        m5 = fetch_data(symbol, "5m", limit=400)
        m15 = fetch_data(symbol, "15m", limit=300)
        h1 = fetch_data(symbol, "1h", limit=300)
        d1 = fetch_data(symbol, "1d", limit=300)

        if not check_indicator_input(m5, 215, f"{symbol} M5"): continue
        if not check_indicator_input(m15, 200, f"{symbol} M15"): continue
        if not check_indicator_input(h1, 200, f"{symbol} H1"): continue
        if not check_indicator_input(d1, 200, f"{symbol} D1"): continue

        if not is_data_fresh(m5, tf_min=5, symbol=symbol, tf_name="M5"): continue
        if not is_data_fresh(m15, tf_min=15, symbol=symbol, tf_name="M15"): continue
        if not is_data_fresh(h1, tf_min=60, symbol=symbol, tf_name="H1"): continue
        if not is_data_fresh(d1, tf_min=1440, symbol=symbol, tf_name="D1"): continue

        ind_m5 = calculate_indicators(m5, cfg, timeframe="5m")
        ind_m15 = calculate_indicators(m15, cfg, timeframe="15m")
        ind_h1 = calculate_indicators(h1, cfg, timeframe="4h")
        ind_d1 = calculate_indicators(d1, cfg, timeframe="1d")
        if ind_m5 is None or ind_m15 is None or ind_h1 is None or ind_d1 is None: continue

        map_m5 = build_indicator_results(m5, ind_m5)
        map_m15 = build_indicator_results(m15, ind_m15)
        map_h1_full = build_indicator_results(h1, ind_h1)
        map_h1 = {k.upper(): v for k, v in map_h1_full.items() if k.upper() in h1_keys}

        vr_m5 = tally_votes(map_m5, w_m15)
        vr_m15 = tally_votes(map_m15, w_m15)
        vr_h1 = tally_votes(map_h1, w_h1)

        sl5, ss5 = float(vr_m5.get("score_long", 0) or 0), float(vr_m5.get("score_short", 0) or 0)
        sl15, ss15 = float(vr_m15.get("score_long", 0) or 0), float(vr_m15.get("score_short", 0) or 0)
        slh1, ssh1 = float(vr_h1.get("score_long", 0) or 0), float(vr_h1.get("score_short", 0) or 0)

        if sl15 - ss15 > 0.1:
            probe_direction = "LONG"
        elif ss15 - sl15 > 0.1:
            probe_direction = "SHORT"
        else:
            probe_direction = "LONG" # mặc định

        side_m5 = decide_side(sl5, ss5)
        side_m15 = decide_side(sl15, ss15)
        side_h1 = decide_side(slh1, ssh1)

        m5_score = sl5 if side_m5 == "LONG" else (ss5 if side_m5 == "SHORT" else 0.0)
        m15_score = sl15 if side_m15 == "LONG" else (ss15 if side_m15 == "SHORT" else 0.0)
        h1_score = slh1 if side_h1 == "LONG" else (ssh1 if side_h1 == "SHORT" else 0.0)

        hhits = _heavy_hits(map_h1, ind_h1['ema200'], side_m15) if side_m15 != "NEUTRAL" else 0
        try:
            adx_h1 = float(ind_h1['adx'].iloc[-1])
        except Exception:
            adx_h1 = 0.0

        price_now = float(m15['close'].iloc[-1]) if m15 is not None and not pd.isnull(m15['close'].iloc[-1]) else 0.0

        ma20_series = ind_m15.get("ma50", None)
        ma20_val = float(ma20_series.iloc[-1]) if ma20_series is not None and hasattr(ma20_series, "iloc") else price_now
        atr_series = ind_m15.get("atr", None)
        atr_val = float(atr_series.iloc[-1]) if atr_series is not None and hasattr(atr_series, "iloc") else price_now*0.01

        anti_chase = abs(price_now - ma20_val) > 1.2 * atr_val if price_now is not None and ma20_val is not None and atr_val is not None else False

        gates_ok = (
            side_m5 == side_m15 == side_h1 != "NEUTRAL"
            and m15_score >= th_m15
            and h1_score >= th_h1
            and hhits >= heavy_required
            and adx_h1 >= int(cfg.get("adx_h1_threshold", 25))
        )
        is_stable = stable_tracker.update(symbol, "15m", side_m15, gates_ok, now_ts=now_epoch)
        full_ready = gates_ok and is_stable

        m15_breakdown = vr_m15.get("breakdown_long", {}) if side_m15 == "LONG" else vr_m15.get("breakdown_short", {})
        h1_breakdown = vr_h1.get("breakdown_long", {}) if side_h1 == "LONG" else vr_h1.get("breakdown_short", {})

        trend_h4 = ind_h1.get("trend_h4", "-")
        trend_d1 = ind_d1.get("trend_d1", "-")

        log_data = {
            "timestamp": int(now_epoch),
            "symbol": symbol,
            "phase": "scan",
            "side": side_m15,
            "m15_score": safe_float_fmt(m15_score,2),
            "h1_score": safe_float_fmt(h1_score,2),
            "heavy_hits": hhits,
            "adx_h1": safe_float_fmt(adx_h1,2),
            "dist_vwap_atr": 0.0,
            "anti_chase_tier": "anti" if anti_chase else "ok",
            "fast_flags": 0,
            "decision": f"full_ready={full_ready}; stable={is_stable};",
            "trend_h4": trend_h4,
            "trend_d1": trend_d1,
        }
        for k, v in m15_breakdown.items():
            log_data[f"m15_{k}"] = v
        for k, v in h1_breakdown.items():
            log_data[f"h1_{k}"] = v

        log_reason_vi_no_accent(log_data)

        plan = plan_probe_and_topup(probe_direction, m15, ind_m15, cfg)
        ema200_series = ind_m15.get("ema200", None)
        ma_probe = float(ema200_series.iloc[-1]) if ema200_series is not None and hasattr(ema200_series, "iloc") else float(price_now)
        breakout_volume = float(m15['volume'].iloc[-1]) if m15 is not None and not pd.isnull(m15['volume'].iloc[-1]) else 0.0
        avg_volume = float(m15['volume'].rolling(20).mean().iloc[-1]) if m15 is not None and not pd.isnull(m15['volume'].rolling(20).mean().iloc[-1]) else 0.0

        # ==== TP ROI 100% (chuẩn trailing stop; leverage 10x = 10%) ====
        roi_target = 1.0  # 100%
        sim_tp_long = price_now * (1 + roi_target / LEVERAGE)
        sim_tp_short = price_now * (1 - roi_target / LEVERAGE)

        # --- Chuẩn bị kiểm tra lệnh đang mở ---
        active_probe = None
        active_full = None
        for t in simulator.get_all_trades():
            if t["symbol"] == symbol and t["direction"] == probe_direction and t["time_close"] is None:
                if t["stage"] == "probe":
                    active_probe = t
                elif t["stage"] == "full":
                    active_full = t

        # --- Logic breakout: chỉ vào probe nhỏ nếu anti-chase ---
        key = (symbol, probe_direction)
        if is_breakout_candle(m15, ind_m15, direction=probe_direction):
            if not active_probe and not active_full:
                probe_size = max(simulator.balance * PROBE_PCT, 0)
                if probe_size >= min_notional:
                    sim_tp = sim_tp_long if probe_direction == "LONG" else sim_tp_short
                    simulator.open_trade(
                        symbol, probe_direction, entry=price_now,
                        sl=None, tp=sim_tp,
                        size_quote=probe_size, is_probe=True,
                        now_ts=now_epoch, r_value=plan.get("r_value") if plan else None,
                        reason=f"probe_breakout_{probe_direction.lower()}",
                        ma=ma_probe, atr=atr_val, breakout_volume=breakout_volume, avg_volume=avg_volume
                    )
                    notifier.text(f"⚡️ Breakout mạnh trên {symbol} – vào probe nhỏ {probe_direction}! Entry: {safe_float_fmt(price_now)} (Anti-chase: {'YES' if anti_chase else 'NO'})")
                    log_data_break = {
                        "timestamp": int(now_epoch),
                        "symbol": symbol,
                        "phase": "probe_breakout",
                        "direction": probe_direction,
                        "entry": safe_float_fmt(price_now),
                        "tp": safe_float_fmt(sim_tp),
                        "size": safe_float_fmt(probe_size),
                        "anti_chase": anti_chase,
                        "reason": f"probe_breakout_{probe_direction.lower()}"
                    }
                    log_reason_vi_no_accent(log_data_break)
                    SPAM_PROBE_WARNED.pop(key, None)
                else:
                    notifier.text(f"❌ Vốn khả dụng quá nhỏ để vào probe {symbol} {probe_direction}. Vốn khả dụng: {simulator.balance}, cần tối thiểu: {min_notional}")
                    SPAM_PROBE_WARNED.pop(key, None)
            else:
                SPAM_PROBE_WARNED[key] = True

        # --- Promote lên full nếu có pullback xác nhận ---
        active_probe = None
        active_full = None
        for t in simulator.get_all_trades():
            if t["symbol"] == symbol and t["direction"] == probe_direction and t["time_close"] is None:
                if t["stage"] == "probe":
                    active_probe = t
                elif t["stage"] == "full":
                    active_full = t
        if active_probe and active_probe.get("stage") == "probe":
            last_close = float(m15["close"].iloc[-1])
            probe_entry = float(active_probe["entry"])
            atr_current = atr_val
            pullback_ok = abs(last_close - probe_entry) <= PROMOTE_PULLBACK_ATR * atr_current if last_close is not None and probe_entry is not None and atr_current is not None else False
            last_candle_dir = "LONG" if last_close > m15["open"].iloc[-1] else "SHORT"
            last_candle_vol = float(m15['volume'].iloc[-1])
            big_trap = (last_candle_dir != active_probe["direction"]) and (last_candle_vol > 1.8 * avg_volume if avg_volume is not None else False)
            if pullback_ok and not big_trap and not anti_chase:
                if not active_full:
                    plan_full = plan_probe_and_topup(active_probe["direction"], m15, ind_m15, cfg)
                    promote_size = max(simulator.balance * FULL_PCT, 0)
                    if promote_size >= min_notional:
                        simulator.promote_trade(active_probe, promote_size, price_now)
                        notifier.text(f"🔁 Promote lên FULL {symbol} sau pullback xác nhận. Giá hiện tại: {safe_float_fmt(price_now)}")
            elif big_trap:
                simulator.close_trade(active_probe, price_now, "TRAP", now_epoch, reason="trap_reversal")
                notifier.text(f"⚠️ Đóng probe {symbol} do phát hiện trap đảo chiều volume lớn!")

        for t in simulator.get_all_trades():
            if t["symbol"] == symbol and t["time_close"] is None:
                dside = t.get("direction")
                tp_sim = t.get("tp")
                sl_sim = t.get("sl")
                active_id = f"{symbol}|{t.get('entry')}"
                closed = False

                update_trailing_stop(t, price_now)

                if price_now is not None and tp_sim is not None and (
                    (dside == "LONG" and price_now >= tp_sim) or
                    (dside == "SHORT" and price_now <= tp_sim)
                ):
                    simulator.close_trade(t, price_now, "TP", now_epoch, reason="take_profit")
                    closed = True

                if not closed and price_now is not None and sl_sim is not None and (
                    (dside == "LONG" and price_now <= sl_sim) or
                    (dside == "SHORT" and price_now >= sl_sim)
                ):
                    simulator.close_trade(t, price_now, "SL", now_epoch, reason="stop_loss")
                    closed = True

                if not closed and side_m15 and dside and side_m15 != dside and side_m15 in ("LONG", "SHORT"):
                    simulator.close_trade(t, price_now, "REVERSE", now_epoch, reason="reverse_signal")
                    closed = True

                adx_latest = None
                rsi_latest = None
                try:
                    adx_latest = float(ind_m15['adx'].iloc[-1])
                except Exception:
                    pass
                try:
                    rsi_latest = float(ind_m15['rsi'].iloc[-1])
                except Exception:
                    pass
                suggest, reason, content = should_suggest_close(
                    t, side_m15, ind_m15, adx_latest, rsi_latest, now_epoch
                )
                pnl = t.get("result", 0)
                if not closed and (suggest and pnl is not None and pnl > 0 and AUTO_CLOSE_ON_WARNING_IF_PNL_POS):
                    simulator.close_trade(t, price_now, "CLOSE_WARN_PNL_POS", now_epoch, reason="close_on_warning_pnl_positive")
                    notifier.text(f"✅ Đóng vị thế {symbol} do cảnh báo & đang lãi {safe_float_fmt(pnl,2)}")
                    closed = True
                elif not closed and suggest:
                    last_warned = CLOSE_WARNED.get(active_id)
                    if last_warned != reason:
                        notifier.text(content)
                        CLOSE_WARNED[active_id] = reason
                else:
                    if CLOSE_WARNED.get(active_id):
                        CLOSE_WARNED.pop(active_id, None)

                # ======= ĐÓNG LỆNH NẾU GIỮ QUÁ LÂU MÀ ĐANG CÓ LÃI =======
                if not closed:
                    MAX_HOLD_M15_PROFIT = 12  # Số nến M15 tối đa giữ lệnh khi đang có lãi, có thể chỉnh
                    n_open = int((time.time() - t.get("time_open", 0)) // (15 * 60)) if t.get("time_open") else 0
                    direction = t.get("direction")
                    entry = float(t.get("entry") or 0)
                    size = float(t.get("size") or 0)
                    pnl_now = (price_now - entry) * size if direction == "LONG" else (entry - price_now) * size
                    if n_open >= MAX_HOLD_M15_PROFIT and pnl_now > 0:
                        simulator.close_trade(t, price_now, "MAX_HOLD_PROFIT", int(time.time()), reason="max_hold_pnl_positive")
                        notifier.text(f"⏰ Đóng {t['symbol']} {direction} do giữ quá lâu nhưng đang lãi ({n_open} nến, PnL={pnl_now:.2f})")
                        closed = True

                if closed:
                    mark_closed_entry(symbol, "15m", dside)
                    monitor.remove_signal(symbol)
                    CLOSE_WARNED.pop(active_id, None)
                    LAST_CLOSE_TIME[symbol] = time.time()

    now_dt = datetime.now()
    if now_dt.hour == 23 and now_dt.minute >= 59:
        csv_path = "trades_sim_log.csv"
        simulator.save_report(csv_path, date=now_dt.strftime("%Y-%m-%d"))
        md_report = simulator.format_markdown_report(date=now_dt.strftime("%Y-%m-%d"))
        summary = simulator.summary_by_stage(date=now_dt.strftime("%Y-%m-%d"))
        notifier.text("**Báo cáo tổng hợp cuối ngày:**\n" + md_report + "\n" + summary)
        try:
            notifier.send_file(csv_path, "Báo cáo giao dịch chi tiết (CSV)")
        except Exception:
            pass

    MAX_HOLD_M15 = 12
    for symbol in cfg.get("symbols", []):
        active_trade = simulator.get_active_trade(symbol)
        if active_trade:
            hold_m15 = int((time.time() - active_trade.get("time_open", 0)) // (15*60)) if active_trade.get("time_open") else 0
            if hold_m15 is not None and hold_m15 > MAX_HOLD_M15 and not active_trade.get("hold_warned", False):
                notifier.text(f"⚠️ Lệnh {symbol} đã treo {hold_m15} nến M15, cân nhắc đóng hoặc kiểm tra lại!")
                active_trade["hold_warned"] = True

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["strict","medium","test_soft"])
    args = parser.parse_args()

    cfg = load_config()
    prof = args.profile or cfg.get("active_profile")
    if prof:
        p = (cfg.get("profiles") or {}).get(prof) or {}
        for k in ("thresholds","tight_mode","trading","risk","scheduler"):
            if k in p: cfg.setdefault(k, {}).update(p[k])
        if "adx_h1_threshold" in p:
            cfg["adx_h1_threshold"] = p["adx_h1_threshold"]

    notifier = Notifier(cfg)
    if notifier.enabled():
        notifier.text(f"Bot started profile={prof}")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGTERM, stop_event.set)
        loop.add_signal_handler(signal.SIGINT, stop_event.set)
    except NotImplementedError:
        pass

    interval_sec = int((cfg.get("scheduler") or {}).get("interval_sec", 60))

    while not stop_event.is_set():
        start = time.time()
        print(f"[LOOP] {datetime.now().isoformat(timespec='seconds')}")
        try:
            await asyncio.wait_for(run_once(cfg, notifier), timeout=max(5, interval_sec - 5))
        except asyncio.TimeoutError:
            print("[WARN] iteration timeout")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ERROR] run_once: {e!r}")
        elapsed = time.time() - start
        remain = max(0, interval_sec - elapsed)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=remain)
        except asyncio.TimeoutError:
            pass

    print("[MAIN] Stopped")

if __name__ == "__main__":
    asyncio.run(main())