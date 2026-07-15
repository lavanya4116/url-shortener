import asyncio
from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routes import router
from app.cache import is_redis_healthy
from app.rate_limiter import get_remaining_requests
from app.tasks import flush_click_counts, cleanup_expired_urls
from app.utils import get_client_ip


app = FastAPI(title="URL Shortener", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    # DB init
    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("DB init failed:", e)

    # background tasks
    asyncio.create_task(flush_click_counts())
    asyncio.create_task(cleanup_expired_urls())

    print("[startup] App started successfully")

@app.middleware("http")
async def add_rate_limit_headers(request, call_next):
    response = await call_next(request)
    if request.client:
        ip = get_client_ip(request)
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