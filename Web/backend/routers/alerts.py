from fastapi import APIRouter, Query
from services.alerts_service import (
    get_all_alerts,
    get_unread_alerts,
    mark_alert_as_read,
)

router = APIRouter()

@router.get("/")
def all_alerts(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    """
    Lấy toàn bộ lịch sử cảnh báo (có phân trang).
    """
    return get_all_alerts(page, page_size)

@router.get("/unread")
def unread_alerts():
    """
    Lấy danh sách cảnh báo chưa đọc.
    """
    return get_unread_alerts()

@router.post("/read/{alert_id}")
def read_alert(alert_id: str):
    """
    Đánh dấu cảnh báo đã đọc.
    """
    return mark_alert_as_read(alert_id)