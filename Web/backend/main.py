from fastapi import FastAPI, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from starlette.responses import JSONResponse

from routers import dashboard, pnl, orders, signals, alerts, settings, user
from middleware.api_key_middleware import APIKeyMiddleware
from utils.logger import log_access, log_error

# Định nghĩa security scheme cho Swagger UI (ổ khóa)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

app = FastAPI(
    title="BabyShark Trading Bot Dashboard API",
    description="API phục vụ dashboard tổng hợp dữ liệu, vốn, PnL, trạng thái, lệnh, báo cáo của hệ thống bot trading.",
    version="1.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
    openapi_tags=[]
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Sửa lại nếu cần bảo mật
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# API Key middleware
app.add_middleware(APIKeyMiddleware)

# Middleware log truy cập (an toàn, không gây lỗi 500 nếu 401)
@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        # Chỉ log nếu không phải lỗi 401 (API key sai)
        if response.status_code != 401:
            user_agent = request.headers.get("user-agent", "")
            ip = request.client.host
            log_access(request.url.path, user_agent, ip)
        return response
    except Exception as ex:
        log_error(f"Exception: {ex}")
        return JSONResponse(content={"detail": "Internal Server Error"}, status_code=500)

# Đăng ký router
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(pnl.router, prefix="/pnl", tags=["PnL"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(signals.router, prefix="/signals", tags=["Signals"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(settings.router, prefix="/settings", tags=["Settings"])
app.include_router(user.router, prefix="/user", tags=["User"])

@app.get("/")
def root():
    return {"msg": "BabyShark Bot Dashboard API is running"}

# === BỔ SUNG ENDPOINT HEALTH ===
@app.get("/api/health")
async def health():
    return {"status": "ok"}