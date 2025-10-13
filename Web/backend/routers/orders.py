from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_orders():
    # Trả về danh sách lệnh mẫu
    return [
        {"id": 1, "symbol": "BTC/USDT", "side": "LONG", "pnl": 20.5, "status": "CLOSE"},
        {"id": 2, "symbol": "ETH/USDT", "side": "SHORT", "pnl": -5.2, "status": "OPEN"}
    ]