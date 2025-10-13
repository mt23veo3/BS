from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_alerts():
    return [
        {"level": "warn", "msg": "Giữ lệnh BTC/USDT quá lâu", "time": "2025-10-12 13:10:00"},
        {"level": "info", "msg": "Đã promote lên full lệnh ETH/USDT", "time": "2025-10-12 12:30:00"}
    ]