from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from services.constants import API_KEY

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Cho phép docs và openapi không cần API key
        if request.url.path in ["/docs", "/openapi.json", "/redoc", "/"]:
            return await call_next(request)
        api_key = request.headers.get("x-api-key")
        if api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API Key")
        return await call_next(request)