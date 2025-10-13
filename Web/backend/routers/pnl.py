from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_pnl_report():
    # Trả về dữ liệu PnL mẫu
    return {
        "labels": ["2025-10-12", "2025-10-13"],
        "values": [125.2, 140.7]
    }