from fastapi import APIRouter
from services.dashboard_service import (
    get_total_equity,
    get_total_pnl,
    get_daily_pnl,
    get_overview,
    get_bot_status,
    get_risk_metrics,
    get_module_reports,
)

router = APIRouter()

@router.get("/overview")
def dashboard_overview():
    """
    Tổng hợp nhanh: vốn hiện tại, tổng PnL, trạng thái bot, rủi ro, v.v.
    """
    return get_overview()

@router.get("/equity")
def equity_info():
    """
    Tổng hợp vốn hiện tại.
    """
    return get_total_equity()

@router.get("/pnl")
def pnl_info():
    """
    Tổng hợp tổng PnL (lãi/lỗ tích lũy).
    """
    return get_total_pnl()

@router.get("/daily_pnl")
def daily_pnl_info():
    """
    PnL từng ngày gần đây (chart).
    """
    return get_daily_pnl()

@router.get("/status")
def status_info():
    """
    Trạng thái bot (đang chạy/mô phỏng/lỗi/thông tin cảnh báo).
    """
    return get_bot_status()

@router.get("/risk")
def risk_metrics():
    """
    Một số chỉ số rủi ro (max drawdown, winrate, ...).
    """
    return get_risk_metrics()

@router.get("/module_reports")
def module_reports():
    """
    Báo cáo chi tiết của các module chính (ví dụ: signals, order, trade, ...).
    """
    return get_module_reports()