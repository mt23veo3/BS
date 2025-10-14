from fastapi import APIRouter
from services.user_service import (
    get_user_info,
    get_session_info,
)

router = APIRouter()

@router.get("/info")
def user_info():
    """
    Thông tin người dùng đăng nhập.
    """
    return get_user_info()

@router.get("/session")
def session_info():
    """
    Thông tin session/dashboard hiện tại.
    """
    return get_session_info()