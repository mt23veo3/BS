from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_signals():
    return [
        {"time": "2025-10-12 12:00:00", "symbol": "BTC/USDT", "signal": "LONG"},
        {"time": "2025-10-12 12:15:00", "symbol": "ETH/USDT", "signal": "SHORT"}
    ]