from fastapi import FastAPI
from app.database import engine, Base
from app import models

# This creates all tables in PostgreSQL if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener", version="1.0.0")

@app.get("/health")
def health_check():
    return {"status": "ok"}