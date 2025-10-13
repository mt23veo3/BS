from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_settings():
    return {
        "max_hold_m15": 12,
        "trailing_stop": 0.002,
        "snapshot_confirmations": 1
    }

@router.post("/")
async def update_settings(settings: dict):
    # TODO: lưu settings mới vào DB/file
    return {"success": True, "msg": "Lưu cài đặt thành công!"}