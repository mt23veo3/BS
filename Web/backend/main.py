from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import dashboard, pnl, orders, signals, alerts, settings, user

app = FastAPI(title="BabyShark Dashboard API", docs_url="/docs", redoc_url=None)

# CORS cho frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(pnl.router, prefix="/api/pnl", tags=["pnl"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

@app.get("/")
def root():
    return {"msg": "BabyShark Dashboard API đang chạy!"}