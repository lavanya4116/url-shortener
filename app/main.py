import asyncio
from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routes import router
from app.cache import is_redis_healthy
from app.rate_limiter import get_remaining_requests
from app.tasks import flush_click_counts, cleanup_expired_urls

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(flush_click_counts())
    asyncio.create_task(cleanup_expired_urls())
    print("[startup] Background tasks started")


@app.middleware("http")
async def add_rate_limit_headers(request, call_next):
    response = await call_next(request)
    if request.client:
        ip = request.client.host
        remaining = get_remaining_requests(ip)
        response.headers["X-RateLimit-Limit"] = "10"
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = "60s"
    return response


app.include_router(router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "redis": "healthy" if is_redis_healthy() else "unhealthy",
        "database": "connected"
    }