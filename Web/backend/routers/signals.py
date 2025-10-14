from fastapi import APIRouter
from services.signals_service import (
    get_all_signals,
    get_signal_by_id,
    get_signal_stats,
)

router = APIRouter()

@router.get("/")
def all_signals():
    """
    Lịch sử tín hiệu.
    """
    return get_all_signals()

@router.get("/stats")
def signal_stats():
    """
    Thống kê tín hiệu (số lượng, tỉ lệ thành công, ...).
    """
    return get_signal_stats()

@router.get("/{signal_id}")
def signal_detail(signal_id: str):
    """
    Chi tiết tín hiệu theo ID.
    """
    return get_signal_by_id(signal_id)