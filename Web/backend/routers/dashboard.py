from fastapi import APIRouter, Depends
from datetime import datetime

router = APIRouter()

@router.get("/")
async def get_dashboard():
    # Trả về mẫu dữ liệu tổng quan dashboard (giả lập/demo)
    return {
        "pnl_today": 123.45,
        "balance": 10000,
        "orders_open": 2,
        "orders_win_rate": 0.67,
        "latest_alerts": [
            {"msg": "Chạm TP BTC/USDT", "time": str(datetime.now())}
        ]
    }