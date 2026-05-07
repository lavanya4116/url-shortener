from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routes import router
from app.cache import is_redis_healthy

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener", version="1.0.0")

app.include_router(router)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "redis": "healthy" if is_redis_healthy() else "unhealthy",
        "database": "connected"
    }