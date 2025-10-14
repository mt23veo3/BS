from fastapi import APIRouter, Body
from services.settings_service import (
    get_settings,
    update_settings,
    get_setting_by_key,
)

router = APIRouter()

@router.get("/")
def all_settings():
    """
    Lấy toàn bộ cấu hình hệ thống.
    """
    return get_settings()

@router.get("/{key}")
def setting_by_key(key: str):
    """
    Lấy cấu hình theo key.
    """
    return get_setting_by_key(key)

@router.post("/update")
def update_config(payload: dict = Body(...)):
    """
    Cập nhật cấu hình (toàn phần hoặc một phần).
    """
    return update_settings(payload)