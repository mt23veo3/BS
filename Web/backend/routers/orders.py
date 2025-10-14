from fastapi import APIRouter, Query
from services.orders_service import (
    get_all_orders,
    get_open_orders,
    get_closed_orders,
    get_order_by_id,
)

router = APIRouter()

@router.get("/")
def all_orders(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    """
    Toàn bộ lịch sử lệnh (có phân trang).
    """
    return get_all_orders(page, page_size)

@router.get("/open")
def open_orders():
    """
    Danh sách lệnh đang mở.
    """
    return get_open_orders()

@router.get("/closed")
def closed_orders():
    """
    Danh sách lệnh đã đóng.
    """
    return get_closed_orders()

@router.get("/{order_id}")
def order_detail(order_id: str):
    """
    Chi tiết lệnh theo ID.
    """
    return get_order_by_id(order_id)