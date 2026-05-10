from fastapi import FastAPI, Request, Response
from app.database import engine, Base
from app import models
from app.routes import router
from app.cache import is_redis_healthy
from app.rate_limiter import get_remaining_requests

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener", version="1.0.0")


@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """Add rate limit info to every response header"""
    response = await call_next(request)
    
    if request.client:
        ip = request.client.host
        remaining = get_remaining_requests(ip)
        response.headers["X-RateLimit-Limit"] = "10"
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = "60s"
    
    return response





@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "redis": "healthy" if is_redis_healthy() else "unhealthy",
        "database": "connected"
    }

app.include_router(router)