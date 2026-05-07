from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routes import router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener", version="1.0.0")

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "ok"}