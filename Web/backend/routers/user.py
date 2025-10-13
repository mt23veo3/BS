from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login(username: str, password: str):
    # TODO: xác thực tài khoản
    if username == 'admin' and password == 'babyshark':
        return {"success": True, "token": "demo-jwt-token"}
    return {"success": False, "msg": "Sai tài khoản hoặc mật khẩu"}